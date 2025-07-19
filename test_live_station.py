import requests
import json

# Test the getLiveStation endpoint with different parameters
api_key = "3d2d6ab594msh9d84246760ebde3p1333cajsn866c1877b839"
api_host = "irctc1.p.rapidapi.com"

def test_live_station():
    """Test getLiveStation with different parameters"""
    
    headers = {
        "x-rapidapi-key": api_key,
        "x-rapidapi-host": api_host
    }
    
    url = "https://irctc1.p.rapidapi.com/api/v3/getLiveStation"
    
    # Test different parameter combinations
    param_tests = [
        {"hours": "1"},
        {"fromStationCode": "NDLS", "hours": "1"},
        {"stationCode": "NDLS", "hours": "1"},
        {"station": "NDLS", "hours": "1"},
        {"code": "NDLS", "hours": "1"},
        {"fromStationCode": "NDLS"},
        {"stationCode": "NDLS"},
        {"station": "NDLS"},
        {"code": "NDLS"}
    ]
    
    for i, params in enumerate(param_tests):
        print(f"\n=== Test {i+1}: {params} ===")
        try:
            response = requests.get(url, headers=headers, params=params, timeout=10)
            print(f"Status: {response.status_code}")
            print(f"Response: {response.text[:300]}...")
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    test_live_station() 