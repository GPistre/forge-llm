#!/usr/bin/env python3
import json
import requests
import sys

def test_llm_service(json_file="sample-state.json"):
    """Test the LLM service with a sample JSON file"""
    try:
        # Load the sample JSON file
        with open(json_file, 'r') as f:
            sample_data = json.load(f)
        
        # Send the request to the service
        print(f"Sending request with context: {sample_data.get('context', 'unknown')}")
        response = requests.post('http://localhost:7860/act', json=sample_data)
        
        # Check if the request was successful
        if response.status_code == 200:
            print("Request successful!")
            print("Response:")
            print(json.dumps(response.json(), indent=2))
            return True
        else:
            print(f"Request failed with status code: {response.status_code}")
            print(f"Response: {response.text}")
            return False
    
    except FileNotFoundError:
        print(f"Error: File '{json_file}' not found")
        return False
    
    except json.JSONDecodeError:
        print(f"Error: '{json_file}' is not a valid JSON file")
        return False
    
    except requests.RequestException as e:
        print(f"Error making request: {e}")
        print("Is the LLM service running?")
        return False

if __name__ == "__main__":
    # Use command line argument for the JSON file if provided, otherwise use default
    json_file = sys.argv[1] if len(sys.argv) > 1 else "sample-state.json"
    test_llm_service(json_file)