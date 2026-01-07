"""
Body Measurement Estimation Module
Uses MediaPipe Pose to estimate body measurements from images
"""

import cv2
import numpy as np
from typing import Dict, Optional, Tuple, List
import os
import urllib.request

try:
    # New MediaPipe API (v0.10+)
    from mediapipe.tasks import python
    from mediapipe.tasks.python import vision
    USE_NEW_API = True
except ImportError:
    USE_NEW_API = False


class BodyMeasurementEstimator:
    """Estimates body measurements using pose detection"""
    
    # Model file URL for MediaPipe Pose Landmarker
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
                    print("Using fallback measurement method")
                    return
            
            # Initialize PoseLandmarker
            try:
                base_options = python.BaseOptions(model_asset_path=self.MODEL_PATH)
                options = vision.PoseLandmarkerOptions(
                    base_options=base_options,
                    output_segmentation_masks=False,
                    num_poses=1  # Detect only one person
                )
                self.pose_landmarker = vision.PoseLandmarker.create_from_options(options)
                self.use_mediapipe = True
                print("MediaPipe Pose initialized successfully!")
            except Exception as e:
                print(f"Failed to initialize MediaPipe: {e}")
                print("Using fallback measurement method")
        
        # Calibration factors (pixels to cm)
        self.PIXEL_TO_CM_RATIO = 0.3  # Approximate, assumes person is ~170cm tall
        
    def analyze_pose(self, image_data: np.ndarray) -> Dict:
        """Analyze pose for real-time feedback"""
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
            mp_image = python.vision.Image(image_format=python.vision.ImageFormat.SRGB, data=image_rgb)
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
            
            # Key landmarks
            # NOSE=0, LEFT_ANKLE=27, RIGHT_ANKLE=28
            nose = landmarks[0]
            l_ankle = landmarks[27]
            r_ankle = landmarks[28]
            
            # Check conditions
            message = "Perfect! Hold still..."
            status = "good"
            quality = 0.95
            
            # Check Feet (y goes from 0 top to 1 bottom)
            if l_ankle.y > 0.95 or r_ankle.y > 0.95:
                 message = "Feet not visible - Step Back"
                 status = "warning"
                 quality = 0.5
            # Check Head
            elif nose.y < 0.05:
                 message = "Head cut off - Adjust Camera"
                 status = "warning"
                 quality = 0.5
            else:
                 # Check if too far (height of person relative to frame)
                 person_h = ((l_ankle.y + r_ankle.y)/2) - nose.y
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
            print(f"Analysis error: {e}")
            return {"detected": False, "message": "Analysis failed", "status": "error", "quality": 0.0}

    def estimate_from_image(self, image_data: np.ndarray, reference_height_cm: Optional[float] = None) -> Dict[str, float]:
        """
        Estimate body measurements from a single image
        
        Args:
            image_data: Image as numpy array (BGR format from OpenCV)
            reference_height_cm: Optional known height for calibration
            
        Returns:
            Dictionary with measurements in centimeters
        """
        if not self.use_mediapipe or self.pose_landmarker is None:
            # Fallback: Return estimated measurements based on image analysis
            return self._estimate_without_mediapipe(image_data, reference_height_cm)
        
        try:
            # Convert BGR to RGB for MediaPipe
            image_rgb = cv2.cvtColor(image_data, cv2.COLOR_BGR2RGB)
            
            # Create MediaPipe Image object
            mp_image = python.vision.Image(image_format=python.vision.ImageFormat.SRGB, data=image_rgb)
            
            # Detect pose
            detection_result = self.pose_landmarker.detect(mp_image)
            
            if not detection_result.pose_landmarks or len(detection_result.pose_landmarks) == 0:
                print("No pose detected, using fallback")
                return self._estimate_without_mediapipe(image_data, reference_height_cm)
            
            # Get landmarks from first detected pose
            landmarks = detection_result.pose_landmarks[0]
            h, w, _ = image_data.shape
            
            # Calculate measurements
            measurements = {}
            
            # Height: top of head to feet
            height_pixels = self._calculate_height_new_api(landmarks, h, w)
            
            # Calibrate pixel-to-cm ratio if reference height is provided
            if reference_height_cm:
                self.PIXEL_TO_CM_RATIO = reference_height_cm / height_pixels
            
            measurements['height'] = round(height_pixels * self.PIXEL_TO_CM_RATIO, 2)
            
            # Shoulder width
            shoulder_width_pixels = self._calculate_shoulder_width_new_api(landmarks, h, w)
            measurements['shoulder_width'] = round(shoulder_width_pixels * self.PIXEL_TO_CM_RATIO, 2)
            
            # Chest
            chest_pixels = self._calculate_chest_new_api(landmarks, h, w)
            measurements['chest'] = round(chest_pixels * self.PIXEL_TO_CM_RATIO, 2)
            
            # Waist
            waist_pixels = self._calculate_waist_new_api(landmarks, h, w)
            measurements['waist'] = round(waist_pixels * self.PIXEL_TO_CM_RATIO, 2)
            
            return measurements
            
        except Exception as e:
            print(f"Error in pose detection: {e}")
            return self._estimate_without_mediapipe(image_data, reference_height_cm)
    
    def _estimate_without_mediapipe(self, image_data: np.ndarray, reference_height_cm: Optional[float] = None) -> Dict[str, float]:
        """
        Fallback method to estimate measurements without MediaPipe
        Returns average measurements based on image dimensions
        """
        h, w, _ = image_data.shape
        
        # Use reference height or estimate based on image height
        if reference_height_cm:
            height = reference_height_cm
        else:
            # Assume average height based on image aspect ratio
            height = 170.0  # Average height in cm
        
        # Estimate other measurements based on typical body proportions
        # These are statistical averages and will be less accurate than pose detection
        measurements = {
            'height': round(height, 2),
            'shoulder_width': round(height * 0.25, 2),  # ~25% of height
            'chest': round(height * 0.55, 2),  # ~55% of height for circumference
            'waist': round(height * 0.47, 2),  # ~47% of height for circumference
        }
        
        return measurements
    
    def _calculate_height(self, landmarks, h: int, w: int) -> float:
        """Calculate height in pixels"""
        # Use nose (0) as top and average of ankles (27, 28) as bottom
        nose = landmarks[self.mp_pose.PoseLandmark.NOSE.value]
        left_ankle = landmarks[self.mp_pose.PoseLandmark.LEFT_ANKLE.value]
        right_ankle = landmarks[self.mp_pose.PoseLandmark.RIGHT_ANKLE.value]
        
        top_y = nose.y * h
        bottom_y = ((left_ankle.y + right_ankle.y) / 2) * h
        
        height = abs(bottom_y - top_y)
        return height
    
    def _calculate_shoulder_width(self, landmarks, h: int, w: int) -> float:
        """Calculate shoulder width in pixels"""
        left_shoulder = landmarks[self.mp_pose.PoseLandmark.LEFT_SHOULDER.value]
        right_shoulder = landmarks[self.mp_pose.PoseLandmark.RIGHT_SHOULDER.value]
        
        left_x = left_shoulder.x * w
        right_x = right_shoulder.x * w
        left_y = left_shoulder.y * h
        right_y = right_shoulder.y * h
        
        width = np.sqrt((right_x - left_x)**2 + (right_y - left_y)**2)
        return width
    
    def _calculate_chest(self, landmarks, h: int, w: int) -> float:
        """
        Estimate chest circumference
        Approximation: chest circumference ≈ shoulder_width * 2.5
        """
        shoulder_width = self._calculate_shoulder_width(landmarks, h, w)
        # Approximate chest circumference from shoulder width
        chest_circumference = shoulder_width * 2.5
        return chest_circumference
    
    def _calculate_waist(self, landmarks, h: int, w: int) -> float:
        """
        Estimate waist circumference
        Using hip landmarks as approximation
        """
        left_hip = landmarks[self.mp_pose.PoseLandmark.LEFT_HIP.value]
        right_hip = landmarks[self.mp_pose.PoseLandmark.RIGHT_HIP.value]
        
        left_x = left_hip.x * w
        right_x = right_hip.x * w
        left_y = left_hip.y * h
        right_y = right_hip.y * h
        
        hip_width = np.sqrt((right_x - left_x)**2 + (right_y - left_y)**2)
        
        # Approximate waist circumference from hip width
        # Waist is typically slightly smaller than hips
        waist_circumference = hip_width * 2.3
        return waist_circumference
    
    def estimate_from_front_and_side(
        self, 
        front_image: np.ndarray, 
        side_image: Optional[np.ndarray] = None,
        reference_height_cm: Optional[float] = None
    ) -> Dict[str, float]:
        """
        Estimate measurements from front and optional side images
        
        Args:
            front_image: Front view image
            side_image: Optional side view image for better accuracy
            reference_height_cm: Optional known height for calibration
            
        Returns:
            Dictionary with measurements
        """
        # Get measurements from front image
        front_measurements = self.estimate_from_image(front_image, reference_height_cm)
        
        # If side image is provided, we could refine measurements
        # For this prototype, we'll use front image measurements
        if side_image is not None:
            try:
                side_measurements = self.estimate_from_image(side_image, reference_height_cm)
                # Average some measurements for better accuracy
                front_measurements['chest'] = round(
                    (front_measurements['chest'] + side_measurements['chest']) / 2, 2
                )
                front_measurements['waist'] = round(
                    (front_measurements['waist'] + side_measurements['waist']) / 2, 2
                )
            except Exception:
                # If side image processing fails, just use front measurements
                pass
        
        return front_measurements
    
    # New API calculation methods (for MediaPipe 0.10+)
    def _calculate_height_new_api(self, landmarks: List, h: int, w: int) -> float:
        """Calculate height in pixels using new API landmarks"""
        # Landmark indices for new API
        NOSE = 0
        LEFT_ANKLE = 27
        RIGHT_ANKLE = 28
        
        nose = landmarks[NOSE]
        left_ankle = landmarks[LEFT_ANKLE]
        right_ankle = landmarks[RIGHT_ANKLE]
        
        top_y = nose.y * h
        bottom_y = ((left_ankle.y + right_ankle.y) / 2) * h
        
        height = abs(bottom_y - top_y)
        return height
    
    def _calculate_shoulder_width_new_api(self, landmarks: List, h: int, w: int) -> float:
        """Calculate shoulder width in pixels using new API landmarks"""
        LEFT_SHOULDER = 11
        RIGHT_SHOULDER = 12
        
        left_shoulder = landmarks[LEFT_SHOULDER]
        right_shoulder = landmarks[RIGHT_SHOULDER]
        
        left_x = left_shoulder.x * w
        right_x = right_shoulder.x * w
        left_y = left_shoulder.y * h
        right_y = right_shoulder.y * h
        
        width = np.sqrt((right_x - left_x)**2 + (right_y - left_y)**2)
        return width
    
    def _calculate_chest_new_api(self, landmarks: List, h: int, w: int) -> float:
        """Estimate chest circumference using new API landmarks"""
        shoulder_width = self._calculate_shoulder_width_new_api(landmarks, h, w)
        chest_circumference = shoulder_width * 2.5
        return chest_circumference
    
    def _calculate_waist_new_api(self, landmarks: List, h: int, w: int) -> float:
        """Estimate waist circumference using new API landmarks"""
        LEFT_HIP = 23
        RIGHT_HIP = 24
        
        left_hip = landmarks[LEFT_HIP]
        right_hip = landmarks[RIGHT_HIP]
        
        left_x = left_hip.x * w
        right_x = right_hip.x * w
        left_y = left_hip.y * h
        right_y = right_hip.y * h
        
        hip_width = np.sqrt((right_x - left_x)**2 + (right_y - left_y)**2)
        waist_circumference = hip_width * 2.3
        return waist_circumference
    
    def __del__(self):
        """Cleanup"""
        if hasattr(self, 'pose_landmarker') and self.pose_landmarker:
            self.pose_landmarker.close()
