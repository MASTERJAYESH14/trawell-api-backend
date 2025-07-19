import requests
import json

# Test the API endpoints
api_key = "3d2d6ab594msh9d84246760ebde3p1333cajsn866c1877b839"
api_host = "irctc1.p.rapidapi.com"

def test_endpoints():
    """Test different possible endpoints and parameters"""
    
    headers = {
        "x-rapidapi-key": api_key,
        "x-rapidapi-host": api_host
    }
    
    # Test 1: Try the original endpoint that worked
    print("=== Test 1: Original getLiveStation ===")
    url = "https://irctc1.p.rapidapi.com/api/v3/getLiveStation"
    params = {"hours": "1"}
    
    try:
        response = requests.get(url, headers=headers, params=params, timeout=10)
        print(f"Status: {response.status_code}")
        print(f"Response: {response.text[:500]}...")
    except Exception as e:
        print(f"Error: {e}")
    
    # Test 2: Try different search endpoints
    print("\n=== Test 2: Search endpoints ===")
    search_endpoints = [
        "/api/v3/searchTrain",
        "/api/v3/search",
        "/api/v3/trains",
        "/api/v3/getTrains"
    ]
    
    for endpoint in search_endpoints:
        url = f"https://irctc1.p.rapidapi.com{endpoint}"
        params = {
            "fromStation": "Mumbai",
            "toStation": "Delhi",
            "dateOfJourney": "2024-01-15"
        }
        
        try:
            response = requests.get(url, headers=headers, params=params, timeout=10)
            print(f"Endpoint: {endpoint}")
            print(f"Status: {response.status_code}")
            if response.status_code == 200:
                print(f"Success! Response: {response.text[:200]}...")
            else:
                print(f"Failed: {response.text[:200]}...")
        except Exception as e:
            print(f"Error with {endpoint}: {e}")
    
    # Test 3: Try different parameter names
    print("\n=== Test 3: Different parameter names ===")
    param_variations = [
        {"from": "Mumbai", "to": "Delhi", "date": "2024-01-15"},
        {"fromStation": "Mumbai", "toStation": "Delhi", "date": "2024-01-15"},
        {"source": "Mumbai", "destination": "Delhi", "date": "2024-01-15"},
        {"fromStationCode": "CSTM", "toStationCode": "NDLS", "dateOfJourney": "2024-01-15"},
        {"fromStationCode": "CSTM", "toStationCode": "NDLS", "date": "2024-01-15"}
    ]
    
    url = "https://irctc1.p.rapidapi.com/api/v3/searchTrain"
    
    for i, params in enumerate(param_variations):
        try:
            response = requests.get(url, headers=headers, params=params, timeout=10)
            print(f"Params {i+1}: {params}")
            print(f"Status: {response.status_code}")
            if response.status_code == 200:
                print(f"Success! Response: {response.text[:200]}...")
            else:
                print(f"Failed: {response.text[:200]}...")
        except Exception as e:
            print(f"Error: {e}")
        print()

if __name__ == "__main__":
    test_endpoints() 