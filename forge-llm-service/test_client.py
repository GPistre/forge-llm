#!/usr/bin/env python3
"""
Test client for the LLM service
This script sends test requests to the LLM service and prints the responses
"""

import requests
import json
import sys
import time

def test_server(url, test_file=None):
    """Test the server with various requests"""
    print(f"Testing LLM server at {url}")
    
    # Test the root endpoint
    try:
        response = requests.get(url)
        print(f"Root endpoint response: {response.text}")
    except Exception as e:
        print(f"Error connecting to server: {e}")
        return
    
    # Test contexts
    contexts = {
        "debug": {"context": "debug"},
        "testing": {"context": "testing"}
    }
    
    for name, payload in contexts.items():
        try:
            print(f"\nTesting {name} context...")
            response = requests.post(f"{url}/act", json=payload)
            print(f"Status: {response.status_code}")
            print(f"Response: {json.dumps(response.json(), indent=2)}")
        except Exception as e:
            print(f"Error testing {name} context: {e}")
    
    # Test with sample state if provided
    if test_file:
        try:
            print(f"\nTesting with sample state from {test_file}...")
            with open(test_file, 'r') as f:
                sample_state = json.load(f)
            
            start_time = time.time()
            response = requests.post(f"{url}/act", json=sample_state)
            elapsed = time.time() - start_time
            
            print(f"Status: {response.status_code}")
            print(f"Response time: {elapsed:.2f} seconds")
            print(f"Response: {json.dumps(response.json(), indent=2)}")
        except Exception as e:
            print(f"Error testing with sample state: {e}")
    
    print("\nTest completed")

if __name__ == "__main__":
    # Default URL
    url = "http://localhost:7861"
    
    # Use sample state file if provided
    test_file = "sample-state.json"
    
    # Override URL if provided as argument
    if len(sys.argv) > 1:
        url = sys.argv[1]
    
    # Override test file if provided as second argument
    if len(sys.argv) > 2:
        test_file = sys.argv[2]
    
    test_server(url, test_file)