
import os
import django
from django.conf import settings
from unittest.mock import MagicMock, patch

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from fitting_system.models import BodyScan
from fitting_system.ai_modules.gemini_client import GeminiClient
from fitting_system.ai_modules.body_measurement import BodyMeasurementEstimator

def test_fallback_flagging():
    print("Testing Fallback Flagging Logic...")
    
    # 1. Test GeminiClient direct response
    client = GeminiClient()
    # Force unavailable to simulate failure
    client.available = False
    
    print("\n1. Testing GeminiClient.analyze_body (Available=False)...")
    result = client.analyze_body(b'dummy_image_data')
    
    if result.get('is_fallback') and result.get('error_message'):
        print(f"SUCCESS: GeminiClient returned fallback flag. Error: {result['error_message']}")
    else:
        print(f"FAILURE: GeminiClient did not return fallback flag. Result: {result}")

    # 2. Test Integration via BodyMeasurementEstimator
    print("\n2. Testing BodyMeasurementEstimator.analyze_body_complete...")
    estimator = BodyMeasurementEstimator()
    
    # Mock get_gemini_client to return our disabled client
    with patch('fitting_system.ai_modules.gemini_client.get_gemini_client', return_value=client):
        # Create dummy image (100x100 black image)
        import numpy as np
        dummy_image = np.zeros((100, 100, 3), dtype=np.uint8)
        
        analysis = estimator.analyze_body_complete(dummy_image)
        
        if analysis.get('is_fallback'):
            print("SUCCESS: Estimator propagated fallback flag.")
        else:
            print("FAILURE: Estimator dropped fallback flag.")

if __name__ == "__main__":
    test_fallback_flagging()

