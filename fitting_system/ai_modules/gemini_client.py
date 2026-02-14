"""
Gemini AI Client Module
Central AI engine for body measurements and recommendations.
Uses Google Gemini Vision API to analyze body images and generate
intelligent fashion recommendations.

Architecture:
    - MediaPipe: Camera/pose visualization only (kept in body_measurement.py)
    - Gemini API: All measurement extraction + recommendations (this module)
"""

import json
import base64
import logging
import re
from typing import Dict, List, Optional, Tuple
from django.conf import settings

logger = logging.getLogger(__name__)

try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    logger.warning("google-generativeai package not installed. Run: pip install google-generativeai")


class GeminiClient:
    """
    Wrapper around Google Gemini API for fashion AI tasks.
    
    Responsibilities:
        1. Extract body measurements from images (replacing MediaPipe math)
        2. Recommend clothing sizes based on measurements
        3. Classify body shape
        4. Analyze skin tone for color recommendations
        5. Generate intelligent fit/style recommendations
    """
    
    # Gemini model to use - gemini-2.0-flash for fast vision tasks
    MODEL_NAME = "gemini-2.0-flash"
    
    def __init__(self, api_key: str = None):
        """
        Initialize Gemini client.
        
        Args:
            api_key: Gemini API key. Falls back to settings.GEMINI_API_KEY
        """
        self.api_key = api_key or getattr(settings, 'GEMINI_API_KEY', None)
        self.model = None
        self.available = False
        
        if not GEMINI_AVAILABLE:
            logger.error("Gemini SDK not available")
            return
            
        if not self.api_key:
            logger.error("No Gemini API key configured. Set GEMINI_API_KEY in settings.py")
            return
        
        try:
            genai.configure(api_key=self.api_key)
            self.model = genai.GenerativeModel(self.MODEL_NAME)
            self.available = True
            logger.info("Gemini AI client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Gemini: {e}")
    
    def _encode_image_for_gemini(self, image_bytes: bytes, mime_type: str = "image/jpeg") -> dict:
        """Convert raw image bytes to Gemini-compatible format."""
        return {
            "mime_type": mime_type,
            "data": base64.b64encode(image_bytes).decode("utf-8")
        }
    
    def _parse_json_response(self, text: str) -> dict:
        """
        Robustly parse JSON from Gemini's response text.
        Handles markdown code blocks, extra text, etc.
        """
        # Try to extract JSON from markdown code block
        json_match = re.search(r'```(?:json)?\s*\n?(.*?)\n?\s*```', text, re.DOTALL)
        if json_match:
            text = json_match.group(1)
        
        # Try to find JSON object or array
        json_obj_match = re.search(r'(\{.*\})', text, re.DOTALL)
        if json_obj_match:
            text = json_obj_match.group(1)
        
        try:
            return json.loads(text)
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Gemini JSON response: {e}\nRaw text: {text[:500]}")
            return {}
    
    def extract_measurements(
        self, 
        front_image_bytes: bytes, 
        side_image_bytes: bytes = None,
        reference_height_cm: float = None
    ) -> Dict[str, float]:
        """
        Extract body measurements from images using Gemini Vision.
        
        This replaces the old MediaPipe landmark-based math calculations.
        Gemini can visually analyze body proportions and estimate measurements
        much more accurately than pixel-distance formulas.
        
        Args:
            front_image_bytes: Front-view body image (JPEG bytes)
            side_image_bytes: Optional side-view image for better accuracy
            reference_height_cm: Optional known height for calibration
            
        Returns:
            Dict with measurements in cm:
                height, shoulder_width, chest, waist, hip,
                torso_length, arm_length, inseam
        """
        if not self.available:
            logger.warning("Gemini not available, returning fallback measurements")
            return self._fallback_measurements(reference_height_cm)
        
        height_instruction = ""
        if reference_height_cm:
            height_instruction = f"""
IMPORTANT: The person's actual height is {reference_height_cm} cm. 
Use this as a calibration reference to estimate all other measurements proportionally.
"""
        
        prompt = f"""You are an expert body measurement AI for a fashion/clothing system.

Analyze the provided body image(s) and estimate the following measurements in centimeters.
{height_instruction}

Look at the person's body proportions carefully and provide realistic estimates.
Consider the person's build, proportions, and visible body contours.

Return ONLY a JSON object with these exact keys (all values in centimeters as numbers):
{{
    "height": <estimated height in cm>,
    "shoulder_width": <shoulder width from edge to edge in cm>,
    "chest": <chest circumference in cm>,
    "waist": <waist circumference in cm>,
    "hip": <hip circumference in cm>,
    "torso_length": <shoulder to hip length in cm>,
    "arm_length": <shoulder to wrist length in cm>,
    "inseam": <hip to ankle inner leg length in cm>
}}

Guidelines for realistic adult measurements:
- Height: typically 150-200 cm
- Shoulder width: typically 35-55 cm
- Chest circumference: typically 75-130 cm
- Waist circumference: typically 60-120 cm
- Hip circumference: typically 80-130 cm
- Torso length: typically 40-55 cm
- Arm length: typically 50-70 cm
- Inseam: typically 65-90 cm

Respond with ONLY the JSON object, no explanations."""

        try:
            # Build the content parts
            content_parts = [prompt]
            
            front_image_part = self._encode_image_for_gemini(front_image_bytes)
            content_parts.append(front_image_part)
            
            if side_image_bytes:
                content_parts.append("Side view image:")
                side_image_part = self._encode_image_for_gemini(side_image_bytes)
                content_parts.append(side_image_part)
            
            response = self.model.generate_content(content_parts)
            result = self._parse_json_response(response.text)
            
            if not result:
                logger.warning("Empty Gemini measurement response, using fallback")
                return self._fallback_measurements(reference_height_cm)
            
            # Validate and normalize measurements
            measurements = self._validate_measurements(result, reference_height_cm)
            logger.info(f"Gemini measurements extracted: {measurements}")
            return measurements
            
        except Exception as e:
            logger.error(f"Gemini measurement extraction failed: {e}")
            return self._fallback_measurements(reference_height_cm)
    
    def analyze_body(
        self,
        front_image_bytes: bytes,
        side_image_bytes: bytes = None,
        reference_height_cm: float = None
    ) -> Dict:
        """
        Full body analysis: measurements + body shape + skin tone + recommendations.
        Single Gemini call for efficiency.
        
        Args:
            front_image_bytes: Front-view body image (JPEG bytes)
            side_image_bytes: Optional side-view image
            reference_height_cm: Optional known height
            
        Returns:
            Dict with measurements, body_shape, skin_tone, undertone
        """
        if not self.available:
            logger.warning("Gemini not available, returning fallback analysis")
            fallback_measurements = self._fallback_measurements(reference_height_cm)
            return {
                "measurements": fallback_measurements,
                "body_shape": "rectangle",
                "skin_tone": "medium",
                "undertone": "warm",
                "confidence": 0.3
            }
        
        height_instruction = ""
        if reference_height_cm:
            height_instruction = f"The person's actual height is {reference_height_cm} cm. Use this to calibrate all measurements."
        
        prompt = f"""You are an expert AI for a virtual dressing / clothing recommendation system.
Analyze the person in the image(s) and provide a complete body analysis.

{height_instruction}

Return ONLY a JSON object with this exact structure:
{{
    "measurements": {{
        "height": <cm>,
        "shoulder_width": <cm>,
        "chest": <chest circumference in cm>,
        "waist": <waist circumference in cm>,
        "hip": <hip circumference in cm>,
        "torso_length": <cm>,
        "arm_length": <cm>,
        "inseam": <cm>
    }},
    "body_shape": "<one of: hourglass, rectangle, triangle, inverted_triangle, oval>",
    "skin_tone": "<one of: light, medium, dark>",
    "undertone": "<one of: warm, cool>",
    "confidence": <0.0-1.0 confidence in the analysis>
}}

Measurement guidelines (realistic adult ranges):
- Height: 150-200 cm
- Shoulder width: 35-55 cm
- Chest circumference: 75-130 cm
- Waist circumference: 60-120 cm
- Hip circumference: 80-130 cm
- Torso length: 40-55 cm
- Arm length: 50-70 cm
- Inseam: 65-90 cm

Body shapes:
- hourglass: bust and hip similar, waist much smaller
- rectangle: bust/waist/hip similar
- triangle: hips wider than shoulders (pear)
- inverted_triangle: shoulders wider than hips (athletic)
- oval: fuller midsection (apple)

Respond with ONLY the JSON object."""

        try:
            content_parts = [prompt]
            content_parts.append(self._encode_image_for_gemini(front_image_bytes))
            
            if side_image_bytes:
                content_parts.append("Side view:")
                content_parts.append(self._encode_image_for_gemini(side_image_bytes))
            
            response = self.model.generate_content(content_parts)
            result = self._parse_json_response(response.text)
            
            if not result or "measurements" not in result:
                logger.warning("Invalid Gemini analysis response, using fallback")
                fallback_measurements = self._fallback_measurements(reference_height_cm)
                return {
                    "measurements": fallback_measurements,
                    "body_shape": "rectangle",
                    "skin_tone": "medium",
                    "undertone": "warm",
                    "confidence": 0.3
                }
            
            # Validate measurements
            result["measurements"] = self._validate_measurements(
                result["measurements"], reference_height_cm
            )
            
            # Validate body shape
            valid_shapes = ["hourglass", "rectangle", "triangle", "inverted_triangle", "oval"]
            if result.get("body_shape") not in valid_shapes:
                result["body_shape"] = "rectangle"
            
            # Validate skin tone
            valid_tones = ["light", "medium", "dark"]
            if result.get("skin_tone") not in valid_tones:
                result["skin_tone"] = "medium"
            
            # Validate undertone
            if result.get("undertone") not in ["warm", "cool"]:
                result["undertone"] = "warm"
            
            logger.info(f"Gemini full analysis complete: shape={result['body_shape']}, tone={result['skin_tone']}")
            return result
            
        except Exception as e:
            logger.error(f"Gemini full analysis failed: {e}")
            fallback_measurements = self._fallback_measurements(reference_height_cm)
            return {
                "measurements": fallback_measurements,
                "body_shape": "rectangle",
                "skin_tone": "medium",
                "undertone": "warm",
                "confidence": 0.3
            }
    
    def get_size_recommendation(
        self,
        measurements: Dict[str, float],
        garment_type: str,
        body_shape: str = "rectangle",
        available_sizes: List[str] = None
    ) -> Dict:
        """
        Get intelligent size recommendation using Gemini.
        
        Args:
            measurements: Body measurements dict
            garment_type: Type of garment (shirt, pants, dress, jacket, skirt)
            body_shape: Body shape classification
            available_sizes: List of available sizes to choose from
            
        Returns:
            Dict with recommended_size, fit_type, reasoning
        """
        if not self.available:
            return {"recommended_size": "M", "fit_type": "regular", "reasoning": "Fallback default"}
        
        if available_sizes is None:
            available_sizes = ["XS", "S", "M", "L", "XL", "XXL"]
        
        prompt = f"""You are a fashion sizing expert. Based on these body measurements, recommend the best clothing size.

Body Measurements:
{json.dumps(measurements, indent=2)}

Garment Type: {garment_type}
Body Shape: {body_shape}
Available Sizes: {', '.join(available_sizes)}

Return ONLY a JSON object:
{{
    "recommended_size": "<one of the available sizes>",
    "fit_type": "<slim, regular, or oversize>",
    "reasoning": "<brief explanation of why this size fits best>"
}}

Size guidelines (chest circumference):
- XS: 76-84 cm
- S: 84-92 cm
- M: 92-100 cm
- L: 100-108 cm
- XL: 108-116 cm
- XXL: 116-124 cm

Consider the body shape when recommending:
- inverted_triangle: may need size up for shirts/jackets, size down for pants
- triangle: may need size up for pants/skirts
- oval: may need size up across the board
- hourglass: fitted styles work well

Respond with ONLY the JSON."""

        try:
            response = self.model.generate_content(prompt)
            result = self._parse_json_response(response.text)
            
            if not result or "recommended_size" not in result:
                return {"recommended_size": "M", "fit_type": "regular", "reasoning": "Could not determine"}
            
            # Validate size is in available list
            if result["recommended_size"] not in available_sizes:
                result["recommended_size"] = "M"
            
            if result.get("fit_type") not in ["slim", "regular", "oversize"]:
                result["fit_type"] = "regular"
            
            return result
            
        except Exception as e:
            logger.error(f"Gemini size recommendation failed: {e}")
            return {"recommended_size": "M", "fit_type": "regular", "reasoning": f"Error: {e}"}
    
    def get_color_recommendations(
        self,
        skin_tone: str,
        undertone: str = "warm",
        body_shape: str = "rectangle",
        garment_type: str = None
    ) -> List[str]:
        """
        Get personalized color recommendations using Gemini.
        
        Args:
            skin_tone: light, medium, or dark
            undertone: warm or cool
            body_shape: Body shape classification
            garment_type: Optional specific garment type
            
        Returns:
            List of recommended color names
        """
        if not self.available:
            return self._fallback_colors(skin_tone)
        
        garment_context = f" for {garment_type}" if garment_type else ""
        
        prompt = f"""You are a fashion color consultant. Recommend clothing colors{garment_context}.

Person's profile:
- Skin tone: {skin_tone}
- Undertone: {undertone}
- Body shape: {body_shape}

Return ONLY a JSON object:
{{
    "recommended_colors": ["Color1", "Color2", "Color3", ...]
}}

Provide 8-12 specific color names that would complement this person.
Use actual fashion color names (e.g., "Navy Blue", "Burgundy", "Emerald Green", not generic "blue", "red").

Respond with ONLY the JSON."""

        try:
            response = self.model.generate_content(prompt)
            result = self._parse_json_response(response.text)
            
            colors = result.get("recommended_colors", [])
            if colors:
                return colors
            
            return self._fallback_colors(skin_tone)
            
        except Exception as e:
            logger.error(f"Gemini color recommendation failed: {e}")
            return self._fallback_colors(skin_tone)
    
    def get_styling_advice(
        self,
        measurements: Dict[str, float],
        body_shape: str,
        skin_tone: str,
        undertone: str = "warm"
    ) -> str:
        """
        Get personalized styling advice using Gemini.
        
        Returns:
            String with styling advice
        """
        if not self.available:
            return "Wear clothes that fit well and make you feel confident!"
        
        prompt = f"""You are a personal fashion stylist. Give brief, practical styling advice.

Person's profile:
- Body shape: {body_shape}
- Skin tone: {skin_tone} with {undertone} undertone
- Measurements: {json.dumps(measurements)}

Give 3-4 concise styling tips specific to their body type and coloring.
Keep each tip to 1-2 sentences. Be encouraging and positive.
Return plain text, not JSON."""

        try:
            response = self.model.generate_content(prompt)
            return response.text.strip()
        except Exception as e:
            logger.error(f"Gemini styling advice failed: {e}")
            return "Wear clothes that fit well and make you feel confident!"
    
    # --- Validation and Fallback Methods ---
    
    def _validate_measurements(self, raw: Dict, reference_height: float = None) -> Dict[str, float]:
        """Validate and clamp measurements to realistic ranges."""
        ranges = {
            "height": (140, 220),
            "shoulder_width": (30, 60),
            "chest": (65, 150),
            "waist": (50, 140),
            "hip": (70, 150),
            "torso_length": (35, 65),
            "arm_length": (45, 80),
            "inseam": (55, 100),
        }
        
        validated = {}
        for key, (min_val, max_val) in ranges.items():
            value = raw.get(key, 0)
            try:
                value = float(value)
            except (TypeError, ValueError):
                value = 0
            
            if value <= 0:
                # Use proportional fallback
                height = float(raw.get("height", reference_height or 170))
                proportions = {
                    "height": 1.0,
                    "shoulder_width": 0.25,
                    "chest": 0.55,
                    "waist": 0.47,
                    "hip": 0.55,
                    "torso_length": 0.30,
                    "arm_length": 0.33,
                    "inseam": 0.45,
                }
                value = height * proportions.get(key, 0.5)
            
            # Clamp to range
            value = max(min_val, min(max_val, value))
            # Round to nearest 0.5
            validated[key] = round(value * 2) / 2
        
        # Override height if reference provided
        if reference_height:
            validated["height"] = reference_height
        
        return validated
    
    def _fallback_measurements(self, reference_height: float = None) -> Dict[str, float]:
        """Return average-proportioned measurements when Gemini is unavailable."""
        height = reference_height or 170.0
        return {
            "height": height,
            "shoulder_width": round(height * 0.25, 1),
            "chest": round(height * 0.55, 1),
            "waist": round(height * 0.47, 1),
            "hip": round(height * 0.55, 1),
            "torso_length": round(height * 0.30, 1),
            "arm_length": round(height * 0.33, 1),
            "inseam": round(height * 0.45, 1),
        }
    
    def _fallback_colors(self, skin_tone: str) -> List[str]:
        """Return rule-based color recommendations when Gemini is unavailable."""
        color_map = {
            'light': [
                'Pastel Pink', 'Light Blue', 'Lavender', 'Mint Green',
                'Peach', 'Navy Blue', 'Emerald Green', 'Ruby Red',
                'Soft Yellow', 'Coral'
            ],
            'medium': [
                'Earth Brown', 'Olive Green', 'Burgundy', 'Mustard Yellow',
                'Terracotta', 'Teal', 'Warm Orange', 'Camel',
                'Deep Purple', 'Forest Green'
            ],
            'dark': [
                'Bright White', 'Vibrant Red', 'Electric Blue', 'Hot Pink',
                'Sunny Yellow', 'Lime Green', 'Orange', 'Magenta',
                'Turquoise', 'Gold'
            ],
        }
        return color_map.get(skin_tone, color_map['medium'])


# --- Singleton accessor ---

_gemini_client_instance = None

def get_gemini_client() -> GeminiClient:
    """Get or create the global GeminiClient singleton."""
    global _gemini_client_instance
    if _gemini_client_instance is None:
        _gemini_client_instance = GeminiClient()
    return _gemini_client_instance
