import os
import requests
import json
from dotenv import load_dotenv

load_dotenv()

class FlightSearch:
    def __init__(self):
        self.api_key = os.getenv("AVIATIONSTACK_API_KEY") or "ca549a437bd8cc1c9bdfc562cb1d4ffd"
        self.base_url = "http://api.aviationstack.com/v1"

    def get_departures(self, airport_iata, limit=5):
        """Get departures from a given airport (IATA code)"""
        try:
            url = f"{self.base_url}/flights"
            params = {
                "access_key": self.api_key,
                "dep_iata": airport_iata,
                "limit": limit
            }
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            flights = self._format_flights(data)
            return json.dumps({"status": "success", "flights": flights}, indent=2)
        except Exception as e:
            return json.dumps({"status": "error", "message": str(e)}, indent=2)

    def get_arrivals(self, airport_iata, limit=5):
        """Get arrivals to a given airport (IATA code)"""
        try:
            url = f"{self.base_url}/flights"
            params = {
                "access_key": self.api_key,
                "arr_iata": airport_iata,
                "limit": limit
            }
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            flights = self._format_flights(data)
            return json.dumps({"status": "success", "flights": flights}, indent=2)
        except Exception as e:
            return json.dumps({"status": "error", "message": str(e)}, indent=2)

    def get_flight_status(self, flight_iata=None, flight_number=None, date=None):
        """Get status of a specific flight by IATA code or flight number and date (YYYY-MM-DD)"""
        try:
            url = f"{self.base_url}/flights"
            params = {"access_key": self.api_key}
            if flight_iata:
                params["flight_iata"] = flight_iata
            if flight_number:
                params["flight_number"] = flight_number
            if date:
                params["flight_date"] = date
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            flights = self._format_flights(data)
            return json.dumps({"status": "success", "flights": flights}, indent=2)
        except Exception as e:
            return json.dumps({"status": "error", "message": str(e)}, indent=2)

    def search_by_airline(self, airline_iata, date=None, limit=5):
        """Search flights by airline (IATA code) and optional date (YYYY-MM-DD)"""
        try:
            url = f"{self.base_url}/flights"
            params = {
                "access_key": self.api_key,
                "airline_iata": airline_iata,
                "limit": limit
            }
            if date:
                params["flight_date"] = date
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            flights = self._format_flights(data)
            return json.dumps({"status": "success", "flights": flights}, indent=2)
        except Exception as e:
            return json.dumps({"status": "error", "message": str(e)}, indent=2)

    def _format_flights(self, data):
        """Format flight data for agentic AI consumption"""
        flights = []
        for item in data.get("data", []):
            flights.append({
                "flight_date": item.get("flight_date"),
                "flight_status": item.get("flight_status"),
                "airline": item.get("airline", {}).get("name"),
                "airline_iata": item.get("airline", {}).get("iata"),
                "flight_number": item.get("flight", {}).get("number"),
                "flight_iata": item.get("flight", {}).get("iata"),
                "departure_airport": item.get("departure", {}).get("airport"),
                "departure_iata": item.get("departure", {}).get("iata"),
                "departure_scheduled": item.get("departure", {}).get("scheduled"),
                "departure_actual": item.get("departure", {}).get("actual"),
                "arrival_airport": item.get("arrival", {}).get("airport"),
                "arrival_iata": item.get("arrival", {}).get("iata"),
                "arrival_scheduled": item.get("arrival", {}).get("scheduled"),
                "arrival_actual": item.get("arrival", {}).get("actual"),
                "duration": item.get("flight_time", None),
                "terminal": item.get("departure", {}).get("terminal"),
                "gate": item.get("departure", {}).get("gate"),
                "baggage": item.get("arrival", {}).get("baggage"),
            })
        return flights

# Example usage
if __name__ == "__main__":
    fs = FlightSearch()
    print("=== Departures from DEL ===")
    print(fs.get_departures("DEL", 3))
    print("\n=== Arrivals to BOM ===")
    print(fs.get_arrivals("BOM", 3))
    print("\n=== Status of AI101 ===")
    print(fs.get_flight_status(flight_iata="AI101"))
    print("\n=== Flights by airline (IndiGo) ===")
    print(fs.search_by_airline("6E", limit=3)) 