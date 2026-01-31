"""
Skin Tone Analysis Module
Uses MediaPipe Face Mesh to analyze skin tone with ITA (Individual Typology Angle)
and undertone detection for accurate clothing color recommendations.
"""

import cv2
import numpy as np
from typing import Tuple, Optional, Dict, List
from dataclasses import dataclass

try:
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
    """
    Analyzes skin tone from facial images using ITA (Individual Typology Angle).
    
    This system:
    1. Detects face using MediaPipe Face Mesh
    2. Extracts skin pixels from cheeks and forehead (avoiding eyes, lips, hair)
    3. Filters skin pixels using YCrCb color space
    4. Converts to LAB color space for accurate color measurement
    5. Calculates ITA for skin tone classification
    6. Detects undertone (warm/cool) from b* value
    7. Recommends clothing colors based on skin tone + undertone
    """
    
    # ITA-based skin tone classification thresholds
    # ITA = arctan((L* - 50) / b*) × (180/π)
    SKIN_TONE_THRESHOLDS = {
        'very_light': (55, float('inf')),   # ITA > 55°
        'light': (41, 55),                   # 41° < ITA ≤ 55°
        'intermediate': (28, 41),            # 28° < ITA ≤ 41°
        'tan': (10, 28),                     # 10° < ITA ≤ 28°
        'dark': (float('-inf'), 10)          # ITA ≤ 10°
    }
    
    # Face Mesh landmark indices for skin sampling regions
    # Cheeks: left cheek (234, 93, 132), right cheek (454, 323, 361)
    # Forehead: center (10, 151, 9)
    CHEEK_LEFT_LANDMARKS = [234, 93, 132, 147, 187, 205]
    CHEEK_RIGHT_LANDMARKS = [454, 323, 361, 376, 411, 425]
    FOREHEAD_LANDMARKS = [10, 151, 9, 107, 336, 296, 67]
    
    # Color recommendations based on skin tone + undertone (10 combinations)
    COLOR_RECOMMENDATIONS = {
        ('very_light', 'warm'): [
            'Peach', 'Coral', 'Warm Beige', 'Camel', 'Soft Orange',
            'Golden Yellow', 'Warm Taupe', 'Cream', 'Honey', 'Champagne'
        ],
        ('very_light', 'cool'): [
            'Soft Pink', 'Lavender', 'Icy Blue', 'Silver', 'Cool Gray',
            'Dusty Rose', 'Periwinkle', 'Mint', 'Powder Blue', 'Mauve'
        ],
        ('light', 'warm'): [
            'Warm Red', 'Mustard', 'Burnt Orange', 'Terracotta', 'Olive',
            'Rust', 'Warm Brown', 'Copper', 'Amber', 'Warm Coral'
        ],
        ('light', 'cool'): [
            'Navy Blue', 'Emerald Green', 'Cool Purple', 'Rose', 'Burgundy',
            'Teal', 'Cool Red', 'Sapphire', 'Mulberry', 'Deep Plum'
        ],
        ('intermediate', 'warm'): [
            'Terracotta', 'Olive Green', 'Gold', 'Rust', 'Bronze',
            'Warm Caramel', 'Cinnamon', 'Rich Orange', 'Warm Burgundy', 'Khaki'
        ],
        ('intermediate', 'cool'): [
            'Teal', 'Burgundy', 'Cool Gray', 'Plum', 'Forest Green',
            'Deep Blue', 'Aubergine', 'Cool Mauve', 'Charcoal', 'Berry'
        ],
        ('tan', 'warm'): [
            'Warm Brown', 'Orange', 'Bronze', 'Gold', 'Terracotta',
            'Burnt Sienna', 'Warm Red', 'Amber', 'Cognac', 'Rich Coral'
        ],
        ('tan', 'cool'): [
            'Deep Blue', 'Forest Green', 'Berry', 'Plum', 'Burgundy',
            'Midnight Blue', 'Peacock', 'Cool Raspberry', 'Deep Teal', 'Wine'
        ],
        ('dark', 'warm'): [
            'Bright Yellow', 'Orange', 'Gold', 'Coral', 'Warm Red',
            'Tangerine', 'Sunflower', 'Bronze', 'Rich Caramel', 'Amber'
        ],
        ('dark', 'cool'): [
            'Electric Blue', 'Magenta', 'White', 'Silver', 'Hot Pink',
            'Cobalt', 'Bright Purple', 'Turquoise', 'Fuchsia', 'Icy White'
        ]
    }
    
    def __init__(self):
        """Initialize the skin tone analyzer with MediaPipe Face Mesh"""
        self.use_mediapipe = False
        self.face_mesh = None
        
        if MEDIAPIPE_AVAILABLE:
            try:
                self.mp_face_mesh = mp.solutions.face_mesh
                self.face_mesh = self.mp_face_mesh.FaceMesh(
                    static_image_mode=True,
                    max_num_faces=1,
                    refine_landmarks=True,
                    min_detection_confidence=0.5,
                    min_tracking_confidence=0.5
                )
                self.use_mediapipe = True
            except Exception as e:
                print(f"Warning: Failed to initialize Face Mesh: {e}")
                self.use_mediapipe = False
    
    def analyze_skin_tone(self, image_data: np.ndarray) -> str:
        """
        Analyze skin tone from an image (backward compatible method).
        
        Args:
            image_data: Image as numpy array (BGR format from OpenCV)
            
        Returns:
            Skin tone category: 'very_light', 'light', 'intermediate', 'tan', or 'dark'
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
        
        if self.use_mediapipe and self.face_mesh is not None:
            # Use Face Mesh for precise skin region extraction
            skin_pixels = self._extract_skin_with_face_mesh(image_rgb)
            confidence = 0.9 if skin_pixels is not None and len(skin_pixels) > 100 else 0.5
        else:
            # Fallback: analyze center region
            skin_pixels = self._extract_skin_fallback(image_rgb)
            confidence = 0.5
        
        if skin_pixels is None or len(skin_pixels) < 10:
            # Return default values if no skin detected
            return SkinToneResult(
                skin_tone='intermediate',
                undertone='warm',
                ita_value=30.0,
                L_star=60.0,
                b_star=15.0,
                confidence=0.0
            )
        
        # Convert skin pixels to LAB color space
        L_star, b_star = self._calculate_lab_values(skin_pixels)
        
        # Calculate ITA (Individual Typology Angle)
        ita_value = self._calculate_ita(L_star, b_star)
        
        # Classify skin tone based on ITA
        skin_tone = self._classify_skin_tone_by_ita(ita_value)
        
        # Detect undertone from b* value
        undertone = self._detect_undertone(b_star)
        
        return SkinToneResult(
            skin_tone=skin_tone,
            undertone=undertone,
            ita_value=ita_value,
            L_star=L_star,
            b_star=b_star,
            confidence=confidence
        )
    
    def _extract_skin_with_face_mesh(self, image_rgb: np.ndarray) -> Optional[np.ndarray]:
        """
        Extract skin pixels from cheeks and forehead using Face Mesh landmarks.
        
        Args:
            image_rgb: Image in RGB format
            
        Returns:
            Array of skin pixels in RGB format, or None if face not detected
        """
        h, w, _ = image_rgb.shape
        results = self.face_mesh.process(image_rgb)
        
        if not results.multi_face_landmarks:
            return None
        
        face_landmarks = results.multi_face_landmarks[0]
        
        # Collect skin sampling points from cheeks and forehead
        skin_regions = []
        all_landmarks = (
            self.CHEEK_LEFT_LANDMARKS + 
            self.CHEEK_RIGHT_LANDMARKS + 
            self.FOREHEAD_LANDMARKS
        )
        
        for idx in all_landmarks:
            landmark = face_landmarks.landmark[idx]
            x = int(landmark.x * w)
            y = int(landmark.y * h)
            
            # Sample a small region around each landmark (5x5 pixels)
            x_start = max(0, x - 2)
            x_end = min(w, x + 3)
            y_start = max(0, y - 2)
            y_end = min(h, y + 3)
            
            if x_end > x_start and y_end > y_start:
                region = image_rgb[y_start:y_end, x_start:x_end]
                skin_regions.append(region.reshape(-1, 3))
        
        if not skin_regions:
            return None
        
        # Combine all sampled pixels
        all_pixels = np.vstack(skin_regions)
        
        # Filter skin pixels using YCrCb color space
        filtered_pixels = self._filter_skin_pixels_ycrcb(all_pixels)
        
        return filtered_pixels
    
    def _extract_skin_fallback(self, image_rgb: np.ndarray) -> Optional[np.ndarray]:
        """
        Fallback method: extract skin from center region when Face Mesh unavailable.
        
        Args:
            image_rgb: Image in RGB format
            
        Returns:
            Array of skin pixels in RGB format
        """
        h, w, _ = image_rgb.shape
        
        # Extract center region (assuming face is centered)
        center_y = h // 3
        center_x = w // 3
        region_h = h // 3
        region_w = w // 3
        
        center_region = image_rgb[center_y:center_y + region_h, center_x:center_x + region_w]
        pixels = center_region.reshape(-1, 3)
        
        # Filter skin pixels
        filtered_pixels = self._filter_skin_pixels_ycrcb(pixels)
        
        return filtered_pixels
    
    def _filter_skin_pixels_ycrcb(self, pixels: np.ndarray) -> np.ndarray:
        """
        Filter pixels to keep only skin-colored pixels using YCrCb color space.
        
        Args:
            pixels: Array of RGB pixels (N, 3)
            
        Returns:
            Filtered array of skin pixels
        """
        if len(pixels) == 0:
            return pixels
        
        # Reshape for color conversion
        pixels_image = pixels.reshape(1, -1, 3).astype(np.uint8)
        ycrcb = cv2.cvtColor(pixels_image, cv2.COLOR_RGB2YCrCb)
        ycrcb = ycrcb.reshape(-1, 3)
        
        # Skin detection thresholds in YCrCb
        # Cr: 133-173, Cb: 77-127
        mask = (
            (ycrcb[:, 1] >= 133) & (ycrcb[:, 1] <= 173) &
            (ycrcb[:, 2] >= 77) & (ycrcb[:, 2] <= 127)
        )
        
        filtered_pixels = pixels[mask]
        
        # If too few pixels pass the filter, return original
        if len(filtered_pixels) < 10:
            return pixels
        
        return filtered_pixels
    
    def _calculate_lab_values(self, skin_pixels: np.ndarray) -> Tuple[float, float]:
        """
        Convert skin pixels to LAB and calculate median L* and b* values.
        
        Args:
            skin_pixels: Array of RGB pixels (N, 3)
            
        Returns:
            Tuple of (L_star, b_star) median values
        """
        # Reshape for color conversion
        pixels_image = skin_pixels.reshape(1, -1, 3).astype(np.uint8)
        lab = cv2.cvtColor(pixels_image, cv2.COLOR_RGB2LAB)
        lab = lab.reshape(-1, 3).astype(np.float32)
        
        # OpenCV LAB ranges: L: 0-255, a: 0-255, b: 0-255
        # Convert to standard LAB: L: 0-100, a: -128 to 127, b: -128 to 127
        L_values = lab[:, 0] * 100 / 255
        b_values = lab[:, 2] - 128  # Convert from 0-255 to -128 to 127
        
        # Use median to reduce impact of outliers (shadows, highlights)
        L_star = np.median(L_values)
        b_star = np.median(b_values)
        
        return L_star, b_star
    
    def _calculate_ita(self, L_star: float, b_star: float) -> float:
        """
        Calculate ITA (Individual Typology Angle) from L* and b* values.
        
        ITA = arctan((L* - 50) / b*) × (180/π)
        
        Higher ITA = lighter skin, Lower ITA = darker skin
        
        Args:
            L_star: Lightness value (0-100)
            b_star: Yellow-blue axis value (-128 to 127)
            
        Returns:
            ITA value in degrees
        """
        # Handle edge case where b_star is zero or very small
        if abs(b_star) < 0.1:
            b_star = 0.1 if b_star >= 0 else -0.1
        
        ita = np.arctan2(L_star - 50, b_star) * (180 / np.pi)
        return float(ita)
    
    def _classify_skin_tone_by_ita(self, ita_value: float) -> str:
        """
        Classify skin tone based on ITA value.
        
        Args:
            ita_value: ITA angle in degrees
            
        Returns:
            Skin tone category: 'very_light', 'light', 'intermediate', 'tan', 'dark'
        """
        for tone, (min_ita, max_ita) in self.SKIN_TONE_THRESHOLDS.items():
            if min_ita < ita_value <= max_ita:
                return tone
        
        # Default fallback
        return 'intermediate'
    
    def _detect_undertone(self, b_star: float) -> str:
        """
        Detect skin undertone (warm or cool) from b* value.
        
        Positive b* indicates yellow tones (warm)
        Negative b* indicates blue tones (cool)
        
        Args:
            b_star: Yellow-blue axis value from LAB color space
            
        Returns:
            'warm' or 'cool'
        """
        return 'warm' if b_star > 0 else 'cool'
    
    def get_recommended_colors(self, skin_tone: str, undertone: str = 'warm') -> List[str]:
        """
        Get recommended clothing colors based on skin tone and undertone.
        
        Args:
            skin_tone: Skin tone category ('very_light', 'light', 'intermediate', 'tan', 'dark')
            undertone: Skin undertone ('warm' or 'cool')
            
        Returns:
            List of recommended color names
        """
        # Normalize inputs
        skin_tone = skin_tone.lower().replace(' ', '_')
        undertone = undertone.lower()
        
        # Map old categories to new ones for backward compatibility
        tone_mapping = {
            'light': 'light',
            'medium': 'intermediate',
            'dark': 'dark'
        }
        skin_tone = tone_mapping.get(skin_tone, skin_tone)
        
        # Get recommendations
        key = (skin_tone, undertone)
        if key in self.COLOR_RECOMMENDATIONS:
            return self.COLOR_RECOMMENDATIONS[key]
        
        # Fallback to intermediate warm
        return self.COLOR_RECOMMENDATIONS.get(
            ('intermediate', 'warm'),
            ['Navy Blue', 'White', 'Gray', 'Black', 'Beige']
        )
    
    def get_all_analysis_data(self, image_data: np.ndarray) -> Dict:
        """
        Get complete skin tone analysis with all details for API response.
        
        Args:
            image_data: Image as numpy array (BGR format)
            
        Returns:
            Dictionary with all analysis results and recommendations
        """
        result = self.analyze_skin_tone_detailed(image_data)
        recommended_colors = self.get_recommended_colors(result.skin_tone, result.undertone)
        
        return {
            'skin_tone': result.skin_tone,
            'skin_tone_display': result.skin_tone.replace('_', ' ').title(),
            'undertone': result.undertone,
            'undertone_display': result.undertone.title(),
            'ita_value': round(result.ita_value, 2),
            'L_star': round(result.L_star, 2),
            'b_star': round(result.b_star, 2),
            'confidence': round(result.confidence, 2),
            'recommended_colors': recommended_colors
        }
    
    def __del__(self):
        """Cleanup MediaPipe resources"""
        if hasattr(self, 'face_mesh') and self.face_mesh is not None:
            try:
                self.face_mesh.close()
            except:
                pass
