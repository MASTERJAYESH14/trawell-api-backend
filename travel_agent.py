import os
import json
from datetime import datetime
from typing import List
from pymongo import MongoClient
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain.agents import initialize_agent, Tool
from pydantic import SecretStr
import demjson3

# Load environment variables
load_dotenv()
mongo_uri = os.getenv("MONGODB_URI")
openai_api_key = os.getenv("OPENAI_API_KEY")

# Connect to MongoDB
client = MongoClient(mongo_uri)
db = client['trawell_ai']
cities_collection = db['cities']
users_collection = db['users']

# Set up the LLM (OpenAI GPT-4o)
llm = ChatOpenAI(
    model="gpt-4o-mini"
)

class TravelAgent:
    def __init__(self):
        self.llm = llm
        self.tools = self._create_tools()
        self.agent = initialize_agent(
            self.tools,
            self.llm,
            verbose=True,
            max_iterations=15
        )
    
    def _create_tools(self):
        """Create tools for the agent to use"""
        return [
            Tool(
                name="get_user_profile",
                func=self.get_user_profile,
                description="Get user's complete personality profile and preferences from database"
            ),
            Tool(
                name="get_places_data",
                func=self.get_places_data,
                description="Get all places and activities data for a specific state"
            ),
            Tool(
                name="get_weather_info",
                func=self.get_weather_info,
                description="Get current weather and seasonal information for planning"
            ),
            Tool(
                name="save_itinerary",
                func=self.save_itinerary,
                description="Save the generated itinerary to database"
            )
        ]
    
    def get_user_profile(self, user_id: str) -> str:
        """Get user's complete profile"""
        try:
            user = users_collection.find_one({"user_id": user_id})
            if user:
                return json.dumps({
                    "user_id": user.get("user_id"),
                    "name": user.get("name"),
                    "age": user.get("age"),
                    "budget": user.get("budget"),
                    "personality_answers": user.get("personality_answers", {}),
                    "travel_dates": user.get("travel_dates"),
                    "start_place": user.get("start_place"),
                    "destination": user.get("destination")
                }, indent=2)
            return "User not found"
        except Exception as e:
            return f"Error getting user profile: {str(e)}"
    
    def get_places_data(self, state: str) -> str:
        """Get all places and activities data for a state"""
        try:
            places_data = cities_collection.find({"state": state})
            result = []
            for city_data in places_data:
                city_info = {
                    "city": city_data["city"],
                    "places": []
                }
                for place in city_data.get("places", []):
                    place_info = {
                        "name": place["name"],
                        "type": place.get("type", []),
                        "description": place.get("description", ""),
                        "uniqueness": place.get("uniqueness", ""),
                        "rating": place.get("rating", 0),
                        "stars": place.get("stars", 0),
                        "best_time_to_visit": place.get("best_time_to_visit", ""),
                        "tags": place.get("tags", []),
                        "time_required": place.get("time_required", ""),
                        "cost": place.get("cost", 0),
                        "min_age": place.get("min_age", 0),
                        "activities": place.get("activities", [])
                    }
                    city_info["places"].append(place_info)
                result.append(city_info)
            
            limited_result = []
            for city in result:
                limited_city = {
                    "city": city["city"],
                    "places": city["places"]
                }
                limited_result.append(limited_city)
            
            return json.dumps(limited_result, indent=2)
        except Exception as e:
            return f"Error getting places data: {str(e)}"
    
    def get_weather_info(self, state: str, travel_dates: str) -> str:
        """Get weather and seasonal information"""
        try:
            start_date = travel_dates.split(" to ")[0]
            month = datetime.strptime(start_date, "%Y-%m-%d").strftime("%B")
            
            weather_data = {
                "state": state,
                "travel_month": month,
                "season": self._get_season(month),
                "weather_notes": self._get_weather_notes(month),
                "packing_tips": self._get_packing_tips(month),
                "activity_timing": self._get_activity_timing(month)
            }
            
            return json.dumps(weather_data, indent=2)
        except Exception as e:
            return f"Error getting weather info: {str(e)}"
    
    def save_itinerary(self, itinerary_data: str) -> str:
        """Save itinerary to database"""
        try:
            itinerary = json.loads(itinerary_data)
            itinerary["created_at"] = datetime.now().isoformat()
            
            itineraries_collection = db['itineraries']
            result = itineraries_collection.insert_one(itinerary)
            
            return json.dumps({
                "status": "success",
                "itinerary_id": str(result.inserted_id),
                "message": "Itinerary saved successfully"
            }, indent=2)
        except Exception as e:
            return f"Error saving itinerary: {str(e)}"
    
    def _get_season(self, month: str) -> str:
        if month in ["March", "April", "May"]:
            return "summer"
        elif month in ["June", "July", "August", "September"]:
            return "monsoon"
        else:
            return "winter"
    
    def _get_weather_notes(self, month: str) -> str:
        season = self._get_season(month)
        notes = {
            "summer": "Hot weather (35-45°C). Plan outdoor activities early morning or evening.",
            "monsoon": "Moderate temperature with rain. Carry rain protection.",
            "winter": "Pleasant weather (10-25°C). Perfect for outdoor activities."
        }
        return notes.get(season, "Check local weather forecast.")
    
    def _get_packing_tips(self, month: str) -> List[str]:
        season = self._get_season(month)
        tips = {
            "summer": ["Light cotton clothes", "Sunscreen", "Water bottle"],
            "monsoon": ["Rain jacket", "Quick-dry clothes", "Waterproof bag"],
            "winter": ["Warm clothes", "Jacket", "Comfortable shoes"]
        }
        return tips.get(season, ["Comfortable clothes", "Walking shoes"])
    
    def _get_activity_timing(self, month: str) -> str:
        season = self._get_season(month)
        timing = {
            "summer": "Early morning and evening for outdoor activities.",
            "monsoon": "Flexible timing, avoid heavy rain.",
            "winter": "Daytime is perfect for outdoor activities."
        }
        return timing.get(season, "Plan based on local weather.")
    
    def create_smart_itinerary(self, user_id: str) -> str:
        """Create a completely AI-powered personalized itinerary"""
        try:
            user_profile = self.get_user_profile(user_id)
            if "User not found" in user_profile:
                return "User not found in database"
            
            user_data = json.loads(user_profile)
            state = user_data.get("destination", "").split(",")[-1].strip() if user_data.get("destination") else ""
            
            if not state:
                return "Destination state not found in user profile"
            
            places_data = self.get_places_data(state)
            
            # Let the LLM do all the thinking!
            prompt = f"""
You are an expert travel planner focused on creating a personalized itinerary for a user. Given the following information, create a detailed, personalized travel itinerary.

If you're unsure about user's personality or preferences, instead of guessing, ask the user for clarification.

USER PROFILE:
{user_profile}

AVAILABLE PLACES:
{places_data}

Create a detailed, personalized travel itinerary that:
1. Matches the user's personality to the best of your ability
2. Optimizes routes between cities based on transportation options.
3. Plans daily activities based on their travel style and energy level (number and type of activities per day should be based on the user's personality and preferences; do not limit the number of activities unless the user's profile suggests it), include the time in a.m and p.m.
4. Infers the likely weather, season, and provides region- and activity-specific packing tips based on the user's travel dates, destination, and planned activities (e.g., trekking gear for treks, rain gear for monsoon, etc.)
5. Everything should be in the user's budget, budget should not be exceeded. But overall it should be close to given budget.
6. Suggests optimal timing for activities based on weather and activity type
7. Includes food recommendations and schedules meal breaks (breakfast, lunch, dinner, snacks) each day, food should be in the user's budget.
8. Plans all transportation in detail:
    - Suggest the most suitable mode of transport from the user's starting location to the destination (flight, train, bus, car, etc.), considering distance, budget, and convenience. Justify your choice.
    - After arrival, suggest local transport (cab, auto, metro, etc.) from arrival point to hotel, with estimated travel time.
    - For each day, include travel time and mode between hotel and each activity/place, and between activities.
    - Estimate and include all travel times in the daily plan.
    - Make sure to mention time for each thing.
    - Ensure the plan is realistic and accounts for time spent traveling, at activities, and for meals/rest.

Respond ONLY with a valid JSON object. All keys and string values must be in double quotes. All numbers must be numbers (no units or text). Do not include trailing commas, comments, or any explanation outside the JSON.

Format as JSON with: itinerary_summary, daily_plans, budget_breakdown, personalized_tips, weather_contingency_plans, food_recommendations.

Make it truly personalized based on their personality answers. Make it as suitable as possible for the user.
"""
            
            response = self.llm.invoke(prompt)
            content = response.content if hasattr(response, 'content') else str(response)
            
            # Ensure content is a string before parsing
            if isinstance(content, str):
                try:
                    itinerary = json.loads(content)
                    save_result = self.save_itinerary(json.dumps(itinerary))
                    itinerary["save_status"] = json.loads(save_result)
                    return json.dumps(itinerary, indent=2)
                except json.JSONDecodeError:
                    # Try demjson3 as a fallback
                    try:
                        itinerary = demjson3.decode(content)
                        itinerary = json.loads(json.dumps(itinerary))  # Convert to dict
                        save_result = self.save_itinerary(json.dumps(itinerary))
                        itinerary["save_status"] = json.loads(save_result)
                        return json.dumps(itinerary, indent=2)
                    except Exception:
                        # Try regex as last resort
                        import re
                        match = re.search(r'(\{.*\})', content, re.DOTALL)
                        if match:
                            try:
                                itinerary = demjson3.decode(match.group(1))
                                itinerary = json.loads(json.dumps(itinerary))  # Convert to dict
                                save_result = self.save_itinerary(json.dumps(itinerary))
                                itinerary["save_status"] = json.loads(save_result)
                                return json.dumps(itinerary, indent=2)
                            except Exception:
                                return f"LLM Response:\n{content}\n\nNote: Response not in JSON format."
                        return f"LLM Response:\n{content}\n\nNote: Response not in JSON format."
            else:
                return f"LLM Response:\n{str(content)}\n\nNote: Unexpected response format."
            
        except Exception as e:
            return f"Error creating smart itinerary: {str(e)}"
    
    def get_recommendations(self, user_id: str, query: str) -> str:
        """Get AI-powered recommendations"""
        try:
            user_profile = self.get_user_profile(user_id)
            if "User not found" in user_profile:
                return "User not found"
            
            prompt = f"""
User Profile: {user_profile}
Query: {query}

Provide personalized recommendations based on their personality and preferences.
"""
            
            response = self.llm.invoke(prompt)
            content = response.content if hasattr(response, 'content') else str(response)
            return str(content)
            
        except Exception as e:
            return f"Error: {str(e)}"

# Example usage
if __name__ == "__main__":
    agent = TravelAgent()
    
    # Get actual user_id from database
    try:
        user = users_collection.find_one()
        if user:
            user_id = user.get("user_id")
            print(f"Found user: {user.get('name', 'Unknown')} (ID: {user_id})")
            print(f"Destination: {user.get('destination', 'Unknown')}")
            print(f"Budget: {user.get('budget', 0)} INR")
            print(f"Travel Dates: {user.get('travel_dates', 'Unknown')}")
            print("\n" + "="*50)
            
            print("Creating AI-powered itinerary...")
            itinerary = agent.create_smart_itinerary(user_id)
            print("\n" + "="*50)
            print("GENERATED ITINERARY:")
            print("="*50)
            print(itinerary)
        else:
            print("No users found in database. Please add a user first using user_profile_db.py")
    except Exception as e:
        print(f"Error accessing database: {str(e)}")
        print("Make sure MongoDB is running and connected properly.") 