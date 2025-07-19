import os
import requests
import json
from typing import List, Dict, Optional
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class TrainSearchAPI:
    def __init__(self):
        # Use the provided API key
        self.api_key = "3d2d6ab594msh9d84246760ebde3p1333cajsn866c1877b839"
        self.api_host = "irctc1.p.rapidapi.com"
        self.base_url = "https://irctc1.p.rapidapi.com/api/v3"
        
        self.station_codes = {
            "Mumbai": "CSTM",  # Chhatrapati Shivaji Terminus
            "Delhi": "NDLS",   # New Delhi
            "Bangalore": "SBC", # Bangalore City
            "Chennai": "MAS",  # Chennai Central
            "Hyderabad": "HYB", # Hyderabad Deccan
            "Kolkata": "HWH",  # Howrah
            "Pune": "PUNE",    # Pune Junction
            "Ahmedabad": "ADI", # Ahmedabad Junction
            "Jaipur": "JP",    # Jaipur Junction
            "Lucknow": "LKO",  # Lucknow Junction
            "Patna": "PNBE",   # Patna Junction
            "Bhopal": "BPL",   # Bhopal Junction
            "Indore": "INDB",  # Indore Junction
            "Nagpur": "NGP",   # Nagpur Junction
            "Varanasi": "BSB", # Varanasi Junction
            "Amritsar": "ASR", # Amritsar Junction
            "Chandigarh": "CDG", # Chandigarh Junction
            "Dehradun": "DDN", # Dehradun
            "Shimla": "SML",   # Shimla
            "Manali": "MLI",   # Manali
            "Goa": "MAO",      # Madgaon
            "Kochi": "ERS",    # Ernakulam Junction
            "Trivandrum": "TVC", # Trivandrum Central
            "Bhubaneswar": "BBS", # Bhubaneswar
            "Guwahati": "GHY", # Guwahati
            "Shillong": "SHL", # Shillong
            "Gangtok": "GKT",  # Gangtok
            "Darjeeling": "DJG" # Darjeeling
        }
    
    def get_station_code(self, city_name: str) -> Optional[str]:
        """Get station code for a city name"""
        # Try exact match first
        if city_name in self.station_codes:
            return self.station_codes[city_name]
        
        # Try partial match
        for city, code in self.station_codes.items():
            if city_name.lower() in city.lower() or city.lower() in city_name.lower():
                return code
        
        return None
    
    def search_trains(self, source: str, destination: str, date: str, 
                     budget: Optional[int] = None) -> str:
        """
        Search for trains between two cities/stations
        
        Args:
            source: Source city or station name
            destination: Destination city or station name
            date: Travel date (YYYY-MM-DD)
            budget: Optional budget constraint
            
        Returns:
            JSON string with train options
        """
        try:
            # Try using station names directly first
            url = f"{self.base_url}/searchTrain"
            params = {
                "fromStation": source,  # Try station name first
                "toStation": destination,  # Try station name first
                "dateOfJourney": date
            }
            headers = {
                "x-rapidapi-key": self.api_key,
                "x-rapidapi-host": self.api_host
            }
            
            response = requests.get(url, headers=headers, params=params, timeout=15)
            
            # If station names don't work, try with station codes
            if response.status_code != 200:
                source_code = self.get_station_code(source) if len(source) != 4 else source
                dest_code = self.get_station_code(destination) if len(destination) != 4 else destination
                
                if not source_code:
                    return json.dumps({
                        "status": "error",
                        "message": f"Station not found for source: {source}"
                    }, indent=2)
                
                if not dest_code:
                    return json.dumps({
                        "status": "error", 
                        "message": f"Station not found for destination: {destination}"
                    }, indent=2)
                
                # Retry with station codes
                params = {
                    "fromStationCode": source_code,
                    "toStationCode": dest_code,
                    "dateOfJourney": date
                }
                response = requests.get(url, headers=headers, params=params, timeout=15)
            
            response.raise_for_status()
            data = response.json()
            
            if data.get("status") and data.get("data"):
                trains = data["data"]
                
                # Filter by budget if provided
                if budget:
                    trains = [
                        train for train in trains
                        if self._get_train_fare(train) <= budget
                    ]
                
                # Format the response
                formatted_trains = []
                for train in trains:
                    formatted_train = {
                        "train_number": train.get("trainNumber", ""),
                        "train_name": train.get("trainName", ""),
                        "departure": train.get("departureTime", ""),
                        "arrival": train.get("arrivalTime", ""),
                        "duration": train.get("duration", ""),
                        "source": source,
                        "destination": destination,
                        "date": date,
                        "classes": train.get("classes", []),
                        "fare": self._get_train_fare(train),
                        "status": train.get("status", "Unknown")
                    }
                    formatted_trains.append(formatted_train)
                
                return json.dumps({
                    "status": "success",
                    "trains": formatted_trains,
                    "total_options": len(formatted_trains),
                    "source": source,
                    "destination": destination
                }, indent=2)
            else:
                return json.dumps({
                    "status": "no_trains",
                    "message": f"No trains found between {source} and {destination} on {date}"
                }, indent=2)
                
        except requests.exceptions.RequestException as e:
            return json.dumps({
                "status": "error",
                "message": f"API request failed: {str(e)}"
            }, indent=2)
        except Exception as e:
            return json.dumps({
                "status": "error",
                "message": f"Error searching trains: {str(e)}"
            }, indent=2)
    
    def get_live_station(self, station: str, hours: int = 1) -> str:
        """
        Get live trains at a station in the next N hours
        
        Args:
            station: Station name or code
            hours: Number of hours to look ahead
            
        Returns:
            JSON string with live train data
        """
        try:
            url = f"{self.base_url}/getLiveStation"
            
            # Try station name first
            params = {
                "station": station,  # Try station name first
                "hours": str(hours)
            }
            headers = {
                "x-rapidapi-key": self.api_key,
                "x-rapidapi-host": self.api_host
            }
            
            response = requests.get(url, headers=headers, params=params, timeout=15)
            
            # If station name doesn't work, try with station code
            if response.status_code != 200:
                station_code = self.get_station_code(station) if len(station) != 4 else station
                
                if not station_code:
                    return json.dumps({
                        "status": "error",
                        "message": f"Station not found for: {station}"
                    }, indent=2)
                
                # Retry with station code
                params = {
                    "stationCode": station_code,
                    "hours": str(hours)
                }
                response = requests.get(url, headers=headers, params=params, timeout=15)
            
            response.raise_for_status()
            data = response.json()
            
            return json.dumps({
                "status": "success",
                "station": station,
                "hours": hours,
                "data": data
            }, indent=2)
            
        except Exception as e:
            return json.dumps({
                "status": "error",
                "message": f"Error getting live station data: {str(e)}"
            }, indent=2)
    
    def get_train_details(self, train_number: str) -> str:
        """
        Get detailed information about a specific train
        
        Args:
            train_number: Train number (e.g., "12951")
            
        Returns:
            JSON string with train details
        """
        try:
            url = f"{self.base_url}/getTrainDetails"
            params = {
                "trainNumber": train_number
            }
            headers = {
                "x-rapidapi-key": self.api_key,
                "x-rapidapi-host": self.api_host
            }
            
            response = requests.get(url, headers=headers, params=params, timeout=15)
            response.raise_for_status()
            
            data = response.json()
            
            return json.dumps({
                "status": "success",
                "train_number": train_number,
                "data": data
            }, indent=2)
            
        except Exception as e:
            return json.dumps({
                "status": "error",
                "message": f"Error getting train details: {str(e)}"
            }, indent=2)
    
    def _get_train_fare(self, train_data: Dict) -> int:
        """Extract fare from train data"""
        try:
            # Try to get fare from various possible fields
            fare_fields = ["fare", "price", "cost", "amount"]
            for field in fare_fields:
                if field in train_data and train_data[field]:
                    return int(train_data[field])
            
            # If no fare found, return a default estimate
            return 1000  # Default fare estimate
        except:
            return 1000  # Default fare estimate
    
    def get_available_stations(self) -> str:
        """Get list of available station codes"""
        return json.dumps({
            "status": "success",
            "stations": self.station_codes,
            "total_stations": len(self.station_codes)
        }, indent=2)

# Example usage
if __name__ == "__main__":
    train_api = TrainSearchAPI()
    
    # Test train search
    print("=== Testing Train Search ===")
    result = train_api.search_trains("Mumbai", "Delhi", "2024-01-15", 3000)
    print(result)
    
    # Test live station
    print("\n=== Testing Live Station ===")
    live_result = train_api.get_live_station("Delhi", 2)
    print(live_result)
    
    # Test available stations
    print("\n=== Available Stations ===")
    stations = train_api.get_available_stations()
    print(stations) 