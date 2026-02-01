"""
Skin Tone Analysis Module
Uses MediaPipe Face Detection to analyze skin tone
"""

import cv2
import numpy as np
from typing import Tuple, Optional

try:
    # Try new MediaPipe API (v0.10+)
    from mediapipe.tasks import python
    from mediapipe.tasks.python import vision
    USE_NEW_API = True
except ImportError:
    # Fall back to old API
    import mediapipe as mp
    MEDIAPIPE_AVAILABLE = True
except ImportError:
    MEDIAPIPE_AVAILABLE = False


@dataclass
class SkinToneResult:
    """Result of skin tone analysis"""
    skin_tone: str        # 'very_light', 'light', 'intermediate', 'tan', 'dark'
    undertone: str        # 'warm' or 'cool'
    ita_value: float      # ITA angle in degrees
    L_star: float         # Lightness value (0-100)
    b_star: float         # Yellow-blue axis value
    confidence: float     # Confidence score (0-1)


class SkinToneAnalyzer:
    """Analyzes skin tone from facial images"""
    
    SKIN_TONE_CATEGORIES = {
        'light': 'Light',
        'medium': 'Medium',
        'dark': 'Dark'
    }
    
    def __init__(self):
        if USE_NEW_API:
            # New API - use fallback method
            self.use_mediapipe = False
        else:
            # Old API
            self.mp_face_detection = mp.solutions.face_detection
            self.face_detection = self.mp_face_detection.FaceDetection(
                model_selection=1,  # Full range model
                min_detection_confidence=0.5
            )
            self.use_mediapipe = True
    
    def analyze_skin_tone(self, image_data: np.ndarray) -> str:
        """
        Analyze skin tone from an image
        
        Args:
            image_data: Image as numpy array (BGR format from OpenCV)
            
        Returns:
            Skin tone category: 'light', 'medium', or 'dark'
        """
        result = self.analyze_skin_tone_detailed(image_data)
        return result.skin_tone
    
    def analyze_skin_tone_detailed(self, image_data: np.ndarray) -> SkinToneResult:
        """
        Perform detailed skin tone analysis with ITA and undertone detection.
        
        Args:
            image_data: Image as numpy array (BGR format from OpenCV)
            
        Returns:
            SkinToneResult with skin_tone, undertone, ITA value, L*, b*, and confidence
        """
        # Convert BGR to RGB for MediaPipe
        image_rgb = cv2.cvtColor(image_data, cv2.COLOR_BGR2RGB)
        
        # Detect face
        results = self.face_detection.process(image_rgb)
        
        if not results.detections:
            # Fallback to center region analysis
            return self._analyze_without_mediapipe(image_data)
        
        # Get the first detected face
        detection = results.detections[0]
        
        # Extract face region
        h, w, _ = image_data.shape
        bounding_box = detection.location_data.relative_bounding_box
        
        # Convert relative coordinates to absolute
        x = int(bounding_box.xmin * w)
        y = int(bounding_box.ymin * h)
        width = int(bounding_box.width * w)
        height = int(bounding_box.height * h)
        
        # Ensure coordinates are within image bounds
        x = max(0, x)
        y = max(0, y)
        x_end = min(w, x + width)
        y_end = min(h, y + height)
        
        # Extract face region (use center portion to avoid hair/background)
        face_center_x = x + width // 4
        face_center_y = y + height // 4
        face_center_width = width // 2
        face_center_height = height // 2
        
        face_region = image_rgb[
            face_center_y:face_center_y + face_center_height,
            face_center_x:face_center_x + face_center_width
        ]
        
        if face_region.size == 0:
            return self._analyze_without_mediapipe(image_data)
        
        # Calculate average skin color
        avg_color = self._get_average_skin_color(face_region)
        
        # Classify skin tone
        skin_tone = self._classify_skin_tone(avg_color)
        
        return skin_tone
    
    def _extract_skin_fallback(self, image_rgb: np.ndarray) -> Optional[np.ndarray]:
        """
        Fallback method to analyze skin tone without face detection
        Analyzes the center region of the image
        """
        h, w, _ = image_rgb.shape
        
        # Extract center region (assuming face is centered)
        center_y = h // 3
        center_x = w // 3
        region_h = h // 3
        region_w = w // 3
        
        center_region = image_data[center_y:center_y + region_h, center_x:center_x + region_w]
        
        # Convert BGR to RGB
        center_region_rgb = cv2.cvtColor(center_region, cv2.COLOR_BGR2RGB)
        
        # Calculate average color
        avg_color = self._get_average_skin_color(center_region_rgb)
        
        # Classify skin tone
        return self._classify_skin_tone(avg_color)
    
    def _get_average_skin_color(self, face_region: np.ndarray) -> Tuple[float, float, float]:
        """
        Calculate average skin color from face region
        
        Args:
            skin_pixels: Array of RGB pixels (N, 3)
            
        Returns:
            Tuple of (L_star, b_star) median values
        """
        # Convert to YCrCb color space for better skin detection
        ycrcb = cv2.cvtColor(face_region, cv2.COLOR_RGB2YCrCb)
        
        # Define skin color range in YCrCb
        # These values are empirically determined for skin detection
        lower_skin = np.array([0, 133, 77], dtype=np.uint8)
        upper_skin = np.array([255, 173, 127], dtype=np.uint8)
        
        # Create mask for skin pixels
        skin_mask = cv2.inRange(ycrcb, lower_skin, upper_skin)
        
        # Apply mask to get skin pixels only
        skin_pixels = cv2.bitwise_and(face_region, face_region, mask=skin_mask)
        
        # Calculate average color of skin pixels
        # If no skin pixels detected, use entire face region
        if np.count_nonzero(skin_mask) > 0:
            avg_color = cv2.mean(face_region, mask=skin_mask)[:3]
        else:
            avg_color = cv2.mean(face_region)[:3]
        
        return avg_color
    
    def _classify_skin_tone(self, rgb_color: Tuple[float, float, float]) -> str:
        """
        Classify skin tone based on RGB color
        
        Args:
            ita_value: ITA angle in degrees
            
        Returns:
            Skin tone category: 'light', 'medium', or 'dark'
        """
        r, g, b = rgb_color
        
        # Calculate luminance (perceived brightness)
        # Using standard luminance formula
        luminance = 0.299 * r + 0.587 * g + 0.114 * b
        
        # Classify based on luminance thresholds
        # These thresholds are approximate and can be adjusted
        if luminance > 170:
            return 'light'
        elif luminance > 120:
            return 'medium'
        else:
            return 'dark'
    
    def get_recommended_colors(self, skin_tone: str) -> list:
        """
        Get recommended clothing colors based on skin tone
        
        Args:
            skin_tone: Skin tone category ('light', 'medium', or 'dark')
            
        Returns:
            Dictionary with undertone details
        """
        color_recommendations = {
            'light': [
                'Pastel Pink', 'Light Blue', 'Lavender', 'Mint Green',
                'Peach', 'Soft Yellow', 'Baby Blue', 'Coral',
                'Navy Blue', 'Emerald Green', 'Ruby Red'
            ],
            'medium': [
                'Earth Brown', 'Olive Green', 'Burgundy', 'Mustard Yellow',
                'Terracotta', 'Teal', 'Warm Orange', 'Camel',
                'Deep Purple', 'Forest Green', 'Rust'
            ],
            'dark': [
                'Bright White', 'Vibrant Red', 'Electric Blue', 'Hot Pink',
                'Sunny Yellow', 'Lime Green', 'Orange', 'Magenta',
                'Turquoise', 'Gold', 'Silver'
            ]
        }
        
        return color_recommendations.get(skin_tone, color_recommendations['medium'])
    
    def __del__(self):
        """Cleanup"""
        if hasattr(self, 'face_detection'):
            self.face_detection.close()


# Example usage
if __name__ == "__main__":
    # Test the analyzer
    analyzer = SkinToneAnalyzer()
    
    # Load test image
    image = cv2.imread('test_image.jpg')
    
    if image is not None:
        # Simple analysis
        undertone = analyzer.analyze_skin_tone(image)
        print(f"Detected undertone: {undertone}")
        
        # Detailed analysis with confidence
        result = analyzer.analyze_with_confidence(image)
        print(f"\nDetailed Analysis:")
        print(f"Undertone: {result['undertone']}")
        print(f"Confidence: {result['confidence']}")
        print(f"Face Detected: {result['face_detected']}")
        print(f"Description: {result['description']['description']}")
        
        # Test color compatibility
        color_score = analyzer.get_color_compatibility_score('warm', undertone)
        print(f"\nWarm color compatibility score: {color_score}")