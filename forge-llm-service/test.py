#!/usr/bin/env python3
import requests
import json

def test_llm_service():
    """Simple test for the LLM service"""
    
    # Create a very basic test request
    test_data = {
        "context": "test",
        "message": "This is a test message"
    }
    
    # Send the request
    try:
        response = requests.post('http://localhost:7860/act', 
                                json=test_data, 
                                timeout=5)
        
        # Print results
        print(f"Status code: {response.status_code}")
        print(f"Response: {response.text}")
        
        return response.status_code == 200
    except Exception as e:
        print(f"Error: {e}")
        return False

if __name__ == "__main__":
    print("Testing LLM service...")
    result = test_llm_service()
    print(f"Test {'passed' if result else 'failed'}!")