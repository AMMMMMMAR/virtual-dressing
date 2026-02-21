"""
Body Measurement Estimation Module

Architecture:
    - MediaPipe Pose: Used ONLY for real-time pose detection, landmark visualization,
      and capturing well-framed body images (camera feedback).
    - Gemini API: Used for actual measurement extraction from the captured images.

MediaPipe provides the visual feedback loop (pose overlay, framing guidance),
while Gemini provides the intelligence (measurement estimation).
"""

import cv2
import numpy as np
from typing import Dict, Optional, List
import os
import urllib.request
import logging

logger = logging.getLogger(__name__)

try:
    # New MediaPipe API (v0.10+)
    import mediapipe as mp
    from mediapipe.tasks import python
    from mediapipe.tasks.python import vision
    USE_NEW_API = True
except ImportError:
    USE_NEW_API = False


class BodyMeasurementEstimator:
    """
    Body measurement estimator.
    
    Uses MediaPipe for:
        - Real-time pose detection (analyze_pose)
        - Visual landmark feedback during camera capture
        
    Uses Gemini API for:
        - Actual body measurement extraction from images
        - Body shape classification
        - Skin tone analysis
    """
    
    # Model file URL for MediaPipe Pose Landmarker (used for pose visualization only)
    MODEL_URL = "https://storage.googleapis.com/mediapipe-models/pose_landmarker/pose_landmarker_heavy/float16/latest/pose_landmarker_heavy.task"
    MODEL_PATH = "pose_landmarker.task"
    
    def __init__(self):
        self.use_mediapipe = False
        self.pose_landmarker = None
        
        if USE_NEW_API:
            # Download model if not exists
            if not os.path.exists(self.MODEL_PATH):
                print(f"Downloading MediaPipe Pose model...")
                try:
                    urllib.request.urlretrieve(self.MODEL_URL, self.MODEL_PATH)
                    print("Model downloaded successfully!")
                except Exception as e:
                    print(f"Failed to download model: {e}")
                    print("Pose visualization will be unavailable")
                    return
            
            # Initialize PoseLandmarker (for visualization/feedback only)
            try:
                base_options = python.BaseOptions(model_asset_path=self.MODEL_PATH)
                options = vision.PoseLandmarkerOptions(
                    base_options=base_options,
                    output_segmentation_masks=False,  # Not needed - Gemini handles analysis
                    num_poses=1
                )
                self.pose_landmarker = vision.PoseLandmarker.create_from_options(options)
                self.use_mediapipe = True
                print("MediaPipe Pose initialized (for camera feedback only)")
            except Exception as e:
                print(f"Failed to initialize MediaPipe: {e}")
                print("Pose visualization will be unavailable")
    
    def analyze_pose(self, image_data: np.ndarray) -> Dict:
        """
        Analyze pose for real-time camera feedback.
        
        This is the ONLY function that uses MediaPipe directly.
        It provides visual guidance to the user during image capture:
        - Is the full body visible?
        - Is the person centered?
        - Are they too close/far?
        
        The actual measurement extraction happens via Gemini in estimate_from_image().
        """
        if not self.use_mediapipe or self.pose_landmarker is None:
            return {
                "detected": True, 
                "message": "System ready", 
                "status": "ready", 
                "quality": 1.0, 
                "landmarks": []
            }
            
        try:
            image_rgb = cv2.cvtColor(image_data, cv2.COLOR_BGR2RGB)
            mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=image_rgb)
            detection_result = self.pose_landmarker.detect(mp_image)
            
            if not detection_result.pose_landmarks or len(detection_result.pose_landmarks) == 0:
                return {
                    "detected": False, 
                    "message": "No person detected", 
                    "status": "bad", 
                    "quality": 0.0,
                    "landmarks": []
                }
                
            landmarks = detection_result.pose_landmarks[0]
            
            # Key landmarks for framing feedback
            nose = landmarks[0]
            l_ankle = landmarks[27]
            r_ankle = landmarks[28]
            
            # Check framing conditions
            message = "Perfect! Hold still..."
            status = "good"
            quality = 0.95
            
            # Check Feet visibility
            if l_ankle.y > 0.95 or r_ankle.y > 0.95:
                message = "Feet not visible - Step Back"
                status = "warning"
                quality = 0.5
            # Check Head visibility
            elif nose.y < 0.05:
                message = "Head cut off - Adjust Camera"
                status = "warning"
                quality = 0.5
            else:
                # Check if too far
                person_h = ((l_ankle.y + r_ankle.y) / 2) - nose.y
                if person_h < 0.4:
                    message = "Too far - Come Closer"
                    status = "warning"
                    quality = 0.6
            
            landmarks_data = [{'x': lm.x, 'y': lm.y} for lm in landmarks]
            
            return {
                "detected": True,
                "message": message,
                "status": status,
                "quality": quality,
                "landmarks": landmarks_data
            }
            
        except Exception as e:
            logger.error(f"Pose analysis error: {e}")
            return {"detected": False, "message": "Analysis failed", "status": "error", "quality": 0.0}

    def estimate_from_image(
        self, 
        image_data: np.ndarray, 
        reference_height_cm: Optional[float] = None
    ) -> Dict[str, float]:
        """
        Estimate body measurements from a single image using Gemini API.
        
        This method converts the image to JPEG bytes and sends it to Gemini
        for intelligent measurement extraction.
        
        Args:
            image_data: Image as numpy array (BGR format from OpenCV)
            reference_height_cm: Optional known height for calibration
            
        Returns:
            Dictionary with measurements in centimeters
        """
        from .gemini_client import get_gemini_client
        
        if True:
            # Convert OpenCV image to JPEG bytes for Gemini
            image_bytes = self._image_to_bytes(image_data)
            
            # Use Gemini for measurement extraction
            gemini = get_gemini_client()
            measurements = gemini.extract_measurements(
                front_image_bytes=image_bytes,
                reference_height_cm=reference_height_cm
            )
            
            logger.info(f"Gemini measurements: {measurements}")
            return measurements
    
    def estimate_from_front_and_side(
        self, 
        front_image: np.ndarray, 
        side_image: Optional[np.ndarray] = None,
        reference_height_cm: Optional[float] = None
    ) -> Dict[str, float]:
        """
        Estimate measurements from front and optional side images using Gemini.
        
        Both images are sent to Gemini for more accurate analysis.
        """
        from .gemini_client import get_gemini_client
        
        if True:
            front_bytes = self._image_to_bytes(front_image)
            side_bytes = self._image_to_bytes(side_image) if side_image is not None else None
            
            gemini = get_gemini_client()
            measurements = gemini.extract_measurements(
                front_image_bytes=front_bytes,
                side_image_bytes=side_bytes,
                reference_height_cm=reference_height_cm
            )
            
            return measurements
    
    def analyze_body_complete(
        self,
        front_image: np.ndarray,
        side_image: Optional[np.ndarray] = None,
        reference_height_cm: Optional[float] = None
    ) -> Dict:
        """
        Complete body analysis using Gemini: measurements + body shape + skin tone.
        
        This is the preferred method - it makes a single Gemini call to get
        everything at once, which is faster and more consistent.
        
        Args:
            front_image: Front view body image (BGR numpy array)
            side_image: Optional side view image
            reference_height_cm: Optional known height for calibration
            
        Returns:
            Dict with:
                measurements: Dict[str, float]
                body_shape: str
                skin_tone: str
                undertone: str
                confidence: float
        """
        from .gemini_client import get_gemini_client
        
        if True:
            front_bytes = self._image_to_bytes(front_image)
            side_bytes = self._image_to_bytes(side_image) if side_image is not None else None
            
            gemini = get_gemini_client()
            result = gemini.analyze_body(
                front_image_bytes=front_bytes,
                side_image_bytes=side_bytes,
                reference_height_cm=reference_height_cm
            )
            
            return result
    
    def estimate_with_stability(
        self, 
        frames: List[np.ndarray], 
        reference_height_cm: Optional[float] = None
    ) -> Dict[str, float]:
        """
        Estimate measurements from multiple frames for stability.
        
        For Gemini-based analysis, we select the best frame rather than 
        averaging multiple results (which would waste API calls).
        
        Args:
            frames: List of image frames (BGR format)
            reference_height_cm: Optional known height for calibration
            
        Returns:
            Dictionary with measurements
        """
        if not frames:
            raise ValueError("No frames provided for measurement estimation")
        
        # Select the middle frame (usually best quality/pose)
        best_frame_idx = len(frames) // 2
        best_frame = frames[best_frame_idx]
        
        return self.estimate_from_image(best_frame, reference_height_cm)
    
    # --- Helper Methods ---
    
    @staticmethod
    def _image_to_bytes(image_data: np.ndarray) -> bytes:
        """Convert OpenCV BGR image to JPEG bytes for Gemini API."""
        success, buffer = cv2.imencode('.jpg', image_data, [cv2.IMWRITE_JPEG_QUALITY, 85])
        if not success:
            raise ValueError("Failed to encode image to JPEG")
        return buffer.tobytes()
    
    
    # _fallback_measurements REMOVED to force error propagation

    
    @staticmethod
    def normalize_measurement(value: float, round_to: float = 0.5, min_val: float = 0, max_val: float = 300) -> float:
        """Fashion-grade normalization: round to nearest increment and clamp."""
        clamped = max(min_val, min(max_val, value))
        return round(clamped / round_to) * round_to
    
    def __del__(self):
        """Cleanup MediaPipe resources."""
        if hasattr(self, 'pose_landmarker') and self.pose_landmarker:
            self.pose_landmarker.close()
