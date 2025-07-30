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
from google.cloud import firestore

# Load environment variables
load_dotenv()
mongo_uri = os.getenv("MONGODB_URI")
openai_api_key = os.getenv("OPENAI_API_KEY")

# Connect to MongoDB
client = MongoClient(mongo_uri)
db = client['trawell']
cities_collection = db['cities']
trip_requests_collection = db['trip_requests']
itineraries_collection = db['itineraries']

# Set up the LLM (OpenAI GPT-4o)
llm = ChatOpenAI(
    model="gpt-4o-mini"
)

def update_firestore_trip_status(user_id, trip_id, status, mongo_itinerary_id):
    db = firestore.Client()
    trip_ref = db.collection('users').document(user_id).collection('trip_requests').document(trip_id)
    update_data = {
        'status': status,
        'mongo_itinerary_id': mongo_itinerary_id
    }
    trip_ref.set(update_data, merge=True)

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
    
    def get_user_profile(self, user_id: str, trip_id: str) -> str:
        """Get user's complete trip profile from the trip_requests collection"""
        try:
            trip_data = trip_requests_collection.find_one({"userId": user_id, "tripId": trip_id})
            if trip_data:
                return json.dumps({
                    "user_id": trip_data.get("userId"),
                    "trip_id": trip_data.get("tripId"),
                    "name": trip_data.get("name"),
                    "budget": trip_data.get("budget"),
                    "personality_answers": trip_data.get("travelPreferences", {}),
                    "travel_dates": {
                        "start_date": trip_data.get("start_date"),
                        "end_date": trip_data.get("end_date")
                    },
                    "start_place": trip_data.get("start_place"),
                    "destination": trip_data.get("destination"),
                    "num_of_travellers": trip_data.get("num_travelers")
                }, indent=2)
            return "Trip data not found"
        except Exception as e:
            return f"Error getting trip profile: {str(e)}"

    
    def get_places_data(self, state: str) -> str:
        """Get all places and activities data for a state with enhanced city information"""
        try:
            places_data = cities_collection.find({"state": state})
            result = []
            for city_data in places_data:
                city_info = {
                    "city": city_data["city"],
                    "city_rating": city_data.get("city_rating"),
                    "city_description": city_data.get("city_description", ""),
                    "city_tags": city_data.get("city_tags", []),
                    "city_image_url": city_data.get("city_image_url", ""),
                    "city_highlights": city_data.get("city_highlights", []),
                    "city_type": city_data.get("city_type", "heritage_city"),
                    "accessibility": city_data.get("accessibility", "well_connected"),
                    "best_time_to_visit": city_data.get("best_time_to_visit", ""),
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
            
            return json.dumps(result, indent=2)
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
    
    def save_itinerary(self, itinerary_data: str, user_id: str, trip_id: str) -> str:
        """Save itinerary to database and update Firestore status"""
        try:
            itinerary = json.loads(itinerary_data)
            itinerary["created_at"] = datetime.now().isoformat()
            result = itineraries_collection.insert_one(itinerary)
            mongo_itinerary_id = str(result.inserted_id)
            # Update Firestore status and MongoDB itinerary reference
            update_firestore_trip_status(user_id, trip_id, "initial_generated", mongo_itinerary_id)
            return json.dumps({
                "status": "success",
                "itinerary_id": mongo_itinerary_id,
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
    
    def create_smart_itinerary(self, user_id: str, trip_id: str) -> str:
        """Create a completely AI-powered personalized itinerary"""
        try:
            user_profile = self.get_user_profile(user_id, trip_id)
            if "Trip data not found" in user_profile:
                return "User not found in database"
            
            user_data = json.loads(user_profile)
            state = user_data.get("destination", "").split(",")[-1].strip() if user_data.get("destination") else ""
            
            if not state:
                return "Destination state not found in user profile"
            
            places_data = self.get_places_data(state)
            
            # Let the LLM do all the thinking with enhanced understanding!
            prompt = f"""
You are an expert travel planner focused on creating a personalized itinerary for a user. Given the following information, create a detailed, personalized travel itinerary.

If you're unsure about user's personality or preferences, instead of guessing, ask the user for clarification.

USER PROFILE:
{user_profile}

AVAILABLE PLACES WITH ENHANCED CITY INFORMATION:
{places_data}

Create a detailed, personalized travel itinerary that:
1. **Matches the user's personality** to the best of your ability using the enhanced city information (ratings, tags, types, accessibility)
2. **Optimizes routes between cities** based on transportation options and city accessibility levels
3. **Plans daily activities** based on their travel style and energy level (number and type of activities per day should be based on the user's personality and preferences; do not limit the number of activities unless the user's profile suggests it), include the time in a.m and p.m.
4. **Infers the likely weather, season**, and provides region- and activity-specific packing tips based on the user's travel dates, destination, and planned activities (e.g., trekking gear for treks, rain gear for monsoon, etc.)
5. **Everything should be in the user's budget**, budget should not be exceeded. But overall it should be close to given budget.
6. **Suggests optimal timing for activities** based on weather, activity type, and city's best_time_to_visit information
7. **Includes food recommendations** and schedules meal breaks (breakfast, lunch, dinner, snacks) each day, food should be in the user's budget.
8. **Plans all transportation in detail**:
    - Suggest the most suitable mode of transport from the user's starting location to the destination (flight, train, bus, car, etc.), considering distance, budget, and convenience. Justify your choice.
    - After arrival, suggest local transport (cab, auto, metro, etc.) from arrival point to hotel, with estimated travel time.
    - For each day, include travel time and mode between hotel and each activity/place, and between activities.
    - Estimate and include all travel times in the daily plan.
    - Make sure to mention time for each thing.
    - Ensure the plan is realistic and accounts for time spent traveling, at activities, and for meals/rest.

**ENHANCED RECOMMENDATION GUIDELINES:**
- Use city ratings to prioritize higher-rated cities for users who prefer popular destinations
- Match user's travel excitement with city highlights and tags
- Consider city accessibility for users with mobility concerns or group size
- Use city types (heritage_city, modern_city, etc.) to match user preferences
- Leverage city descriptions and highlights for better personalization
- Consider best_time_to_visit for optimal planning

Respond ONLY with a valid JSON object. All keys and string values must be in double quotes. All numbers must be numbers (no units or text). Do not include trailing commas, comments, or any explanation outside the JSON.

Format as JSON with: itinerary_summary, daily_plans, budget_breakdown, personalized_tips, weather_contingency_plans, food_recommendations.

Make it truly personalized based on their personality answers and the enhanced city information. Make it as suitable as possible for the user.
"""
            
            response = self.llm.invoke(prompt)
            content = response.content if hasattr(response, 'content') else str(response)
            
            # Ensure content is a string before parsing
            if isinstance(content, str):
                try:
                    itinerary = json.loads(content)
                    save_result = self.save_itinerary(json.dumps(itinerary), user_id, trip_id)
                    itinerary["save_status"] = json.loads(save_result)
                    return json.dumps(itinerary, indent=2)
                except json.JSONDecodeError:
                    # Try demjson3 as a fallback
                    try:
                        itinerary = demjson3.decode(content)
                        itinerary = json.loads(json.dumps(itinerary))  # Convert to dict
                        save_result = self.save_itinerary(json.dumps(itinerary), user_id, trip_id)
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
                                save_result = self.save_itinerary(json.dumps(itinerary), user_id, trip_id)
                                itinerary["save_status"] = json.loads(save_result)
                                return json.dumps(itinerary, indent=2)
                            except Exception:
                                return f"LLM Response:\n{content}\n\nNote: Response not in JSON format."
                        return f"LLM Response:\n{content}\n\nNote: Response not in JSON format."
            else:
                return f"LLM Response:\n{str(content)}\n\nNote: Unexpected response format."
            
        except Exception as e:
            return f"Error creating smart itinerary: {str(e)}"
    
    def get_recommendations(self, user_id: str, trip_id: str, query: str) -> str:
        """Get AI-powered recommendations using enhanced city information"""
        try:
            user_profile = self.get_user_profile(user_id, trip_id)
            if "Trip data not found" in user_profile:
                return "User not found"
            
            user_data = json.loads(user_profile)
            state = user_data.get("destination", "").split(",")[-1].strip() if user_data.get("destination") else ""
            
            if not state:
                return "Destination state not found in user profile"
            
            places_data = self.get_places_data(state)
            
            prompt = f"""
You are an expert travel advisor. Provide personalized recommendations based on the user's profile and the enhanced city information available.

USER PROFILE:
{user_profile}

AVAILABLE CITIES WITH ENHANCED INFORMATION:
{places_data}

USER QUERY:
{query}

INSTRUCTIONS:
- Use the enhanced city information (ratings, tags, types, accessibility, highlights) to provide better recommendations
- Match user's personality traits with city characteristics
- Consider city ratings for popularity preferences
- Use city tags to match specific interests
- Consider accessibility for group size and mobility
- Leverage city highlights and descriptions for detailed recommendations
- Provide specific reasons why each recommendation matches the user's profile

Provide detailed, personalized recommendations that leverage all the available city information.
"""
            
            response = self.llm.invoke(prompt)
            content = response.content if hasattr(response, 'content') else str(response)
            return str(content)
            
        except Exception as e:
            return f"Error: {str(e)}"
    
    def generate_initial_recommendations(self, user_id: str, trip_id: str) -> dict:
        """Generate and save initial recommendations in hierarchical structure: cities -> places+activities -> hotels."""
        try:
            trip_doc = trip_requests_collection.find_one({"userId": user_id, "tripId": trip_id})
            if not trip_doc:
                return {"status": "error", "error": "Trip not found"}

            # Extract trip details
            trip_data = trip_doc.get("tripData", {})
            travel_preferences = trip_doc.get("travelPreferences", {})
            destination = trip_data.get("destination", "")
            budget = trip_data.get("budget", 0)
            start_date = trip_data.get("start_date", "")
            end_date = trip_data.get("end_date", "")
            group_size = trip_data.get("num_travelers", "")

            # --- STEP 1: CITY RECOMMENDATIONS ---
            ai_cities = self._ai_recommend_cities(destination, travel_preferences, budget, group_size, start_date, end_date)
            popular_cities = self._popular_cities(destination)
            hidden_gem_cities = self._hidden_gem_cities(destination)

            # Debug: Print what we're getting
            print(f"AI Cities: {len(ai_cities)}")
            print(f"Popular Cities: {len(popular_cities)}")
            print(f"Hidden Gem Cities: {len(hidden_gem_cities)}")

            # Ensure no duplicates between categories
            ai_city_names = {c.get("name") for c in ai_cities if c.get("name")}
            popular_city_names = {c.get("name") for c in popular_cities if c.get("name")}

            popular_cities = [c for c in popular_cities if c.get("name") not in ai_city_names]
            hidden_gem_cities = [c for c in hidden_gem_cities if c.get("name") not in ai_city_names and c.get("name") not in popular_city_names]

            print(f"After deduplication - Popular: {len(popular_cities)}, Hidden Gems: {len(hidden_gem_cities)}")

            # Ensure we have at least some cities in each category
            if len(popular_cities) == 0:
                print("No popular cities after deduplication, adding some back...")
                all_cities_data = cities_collection.find({"state": destination})
                all_cities = []
                for city_doc in all_cities_data:
                    city_info = {
                        "name": city_doc.get("city", ""),
                        "rating": city_doc.get("city_rating", 4.0),
                        "description": city_doc.get("city_description", ""),
                        "tags": city_doc.get("city_tags", []),
                        "type": city_doc.get("city_type", "heritage_city"),
                        "accessibility": city_doc.get("accessibility", "well_connected"),
                        "highlights": city_doc.get("city_highlights", []),
                        "image_url": city_doc.get("city_image_url", "")
                    }
                    all_cities.append(city_info)
                
                # Add top rated cities as popular
                sorted_cities = sorted(all_cities, key=lambda x: float(x.get("rating", 0)), reverse=True)
                popular_cities = [c for c in sorted_cities[:3] if c.get("name") not in ai_city_names]

            if len(hidden_gem_cities) == 0:
                print("No hidden gem cities after deduplication, adding some back...")
                all_cities_data = cities_collection.find({"state": destination})
                all_cities = []
                for city_doc in all_cities_data:
                    city_info = {
                        "name": city_doc.get("city", ""),
                        "rating": city_doc.get("city_rating", 4.0),
                        "description": city_doc.get("city_description", ""),
                        "tags": city_doc.get("city_tags", []),
                        "type": city_doc.get("city_type", "heritage_city"),
                        "accessibility": city_doc.get("accessibility", "well_connected"),
                        "highlights": city_doc.get("city_highlights", []),
                        "image_url": city_doc.get("city_image_url", "")
                    }
                    all_cities.append(city_info)
                
                # Add lower rated or unique cities as hidden gems
                hidden_candidates = []
                for city in all_cities:
                    rating = float(city.get("rating", 0))
                    tags = city.get("tags", [])
                    city_type = city.get("type", "").lower()
                    
                    if (rating < 4.0 or 
                        any(tag.lower() in ['offbeat', 'hidden', 'local', 'authentic', 'lesser-known', 'traditional'] for tag in tags) or
                        city_type in ['spiritual_city', 'adventure_destination']):
                        hidden_candidates.append(city)
                
                hidden_gem_cities = [c for c in hidden_candidates[:3] if c.get("name") not in ai_city_names and c.get("name") not in {c.get("name") for c in popular_cities}]

            print(f"Final counts - AI: {len(ai_cities)}, Popular: {len(popular_cities)}, Hidden Gems: {len(hidden_gem_cities)}")

            # --- STEP 2: PLACES AND ACTIVITIES FOR EACH CITY ---
            city_details = {}
            all_cities = ai_cities + popular_cities + hidden_gem_cities
            
            for city in all_cities:
                city_name = city.get("name", "")
                if city_name:
                    places_and_activities = self._get_places_and_activities_for_city(destination, city_name)
                    city_details[city_name] = places_and_activities

            # --- STEP 3: HOTELS RECOMMENDATION ---
            ai_hotels = self._ai_recommend_hotels(destination, budget, group_size, start_date, end_date)
            popular_hotels = self._popular_hotels(destination)
            budget_hotels = self._budget_hotels(destination)

            initial_itinerary = {
                "cities": {
                    "ai_recommended": ai_cities,
                    "popular": popular_cities,
                    "hidden_gems": hidden_gem_cities
                },
                "city_details": city_details,
                "hotels": {
                    "ai_recommended": ai_hotels,
                    "popular": popular_hotels,
                    "budget_friendly": budget_hotels
                }
            }

            # Save to MongoDB
            trip_requests_collection.update_one(
                {"userId": user_id, "tripId": trip_id},
                {
                    "$set": {
                        "initialItinerary": initial_itinerary,
                        "tripData.status": "initial_generated"
                    }
                }
            )
            # Also update Firestore with status and MongoDB trip request _id
            mongo_trip_doc = trip_requests_collection.find_one({"userId": user_id, "tripId": trip_id})
            mongo_trip_id = str(mongo_trip_doc["_id"]) if mongo_trip_doc and "_id" in mongo_trip_doc else None
            update_firestore_trip_status(user_id, trip_id, "initial_generated", mongo_trip_id)

            return {"status": "success"}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    # --- Helper methods for recommendations ---#
    
    def _ai_recommend_cities(self, destination, travel_preferences, budget, group_size, start_date=None, end_date=None):
        # Calculate trip duration in days
        duration_days = 3
        if start_date and end_date:
            try:
                from datetime import datetime
                d1 = datetime.fromisoformat(str(start_date)[:10])
                d2 = datetime.fromisoformat(str(end_date)[:10])
                duration_days = max(1, (d2 - d1).days + 1)
            except Exception:
                pass
        
        # Get enhanced city data for better recommendations
        cities_data = cities_collection.find({"state": destination})
        available_cities = []
        for city_doc in cities_data:
            city_info = {
                "name": city_doc.get("city", ""),
                "rating": city_doc.get("city_rating", 4.0),
                "description": city_doc.get("city_description", ""),
                "tags": city_doc.get("city_tags", []),
                "type": city_doc.get("city_type", "heritage_city"),
                "accessibility": city_doc.get("accessibility", "well_connected"),
                "highlights": city_doc.get("city_highlights", []),
                "image_url": city_doc.get("city_image_url", "")
            }
            available_cities.append(city_info)
        
        # Build a detailed, production-level prompt with enhanced city understanding
        prompt = f"""
You are an expert personalized travel planner. Recommend cities to visit in {destination} for a traveler with these preferences:

USER PREFERENCES:
- Group size: {group_size}
- Openness to new experiences: {travel_preferences.get('openness_to_new_experiences', 'N/A')}
- Free time preference: {travel_preferences.get('free_time_preference', 'N/A')}
- Travel excitement: {travel_preferences.get('travel_excitement', 'N/A')}
- Travel planning style: {travel_preferences.get('travel_planning_style', 'N/A')}
- Travel life role: {travel_preferences.get('travel_life_role', 'N/A')}

TRIP DETAILS:
- Budget: {budget} INR
- Trip duration: {duration_days} days

AVAILABLE CITIES WITH DETAILS:
{json.dumps(available_cities, indent=2)}

INSTRUCTIONS:
- Analyze user preferences and match them with city characteristics
- Consider city ratings, tags, type, and accessibility
- Match user's travel excitement with city highlights
- Consider group size and accessibility
- Recommend cities that align with user's personality and preferences
- For each recommended city, provide: name, description, image_url, why_recommended
- Return ONLY a valid JSON array like this:
[
  {{
    "name": "City Name",
    "description": "Brief description",
    "image_url": "https://example.com/image.jpg",
  }}
]
"""
        response = self.llm.invoke(prompt)
        ai_recommendations = self._parse_llm_response(response)
        
        # Convert AI recommendations to match the structure of popular/hidden gem cities
        enhanced_ai_cities = []
        for ai_city in ai_recommendations:
            # Find the full city data from available_cities
            matching_city = next((city for city in available_cities if city.get("name") == ai_city.get("name")), None)
            if matching_city:
                enhanced_city = {
                    "name": ai_city.get("name"),
                    "rating": matching_city.get("rating", 4.0),
                    "description": ai_city.get("description", matching_city.get("description", "")),
                    "tags": matching_city.get("tags", []),
                    "type": matching_city.get("type", "heritage_city"),
                    "accessibility": matching_city.get("accessibility", "well_connected"),
                    "highlights": matching_city.get("highlights", []),
                    "image_url": ai_city.get("image_url", matching_city.get("image_url", "")),
                    "why_recommended": ai_city.get("why_recommended", "")
                }
                enhanced_ai_cities.append(enhanced_city)
        
        return enhanced_ai_cities

    def safe_int(self, val, default=0):
        try:
            return int(val)
        except (ValueError, TypeError):
            return default

    def _popular_cities(self, destination):
        # Get all cities in the destination state with enhanced information
        cities_data = cities_collection.find({"state": destination})
        cities = []
        for city_doc in cities_data:
            city_info = {
                "name": city_doc.get("city", ""),
                "rating": city_doc.get("city_rating"),
                "description": city_doc.get("city_description", ""),
                "tags": city_doc.get("city_tags", []),
                "type": city_doc.get("city_type", "heritage_city"),
                "accessibility": city_doc.get("accessibility", "well_connected"),
                "highlights": city_doc.get("city_highlights", []),
                "image_url": city_doc.get("city_image_url", "")
            }
            cities.append(city_info)
        
        # Sort by city rating (higher rating = more popular)
        popular_cities = sorted(cities, key=lambda x: float(x.get("rating", 0)), reverse=True)[:5]
        return popular_cities

    def _hidden_gem_cities(self, destination):
        # Get all cities in the destination state with enhanced information
        cities_data = cities_collection.find({"state": destination})
        cities = []
        for city_doc in cities_data:
            city_info = {
                "name": city_doc.get("city", ""),
                "rating": city_doc.get("city_rating", 4.0),
                "description": city_doc.get("city_description", ""),
                "tags": city_doc.get("city_tags", []),
                "type": city_doc.get("city_type", "heritage_city"),
                "accessibility": city_doc.get("accessibility", "well_connected"),
                "highlights": city_doc.get("city_highlights", []),
                "image_url": city_doc.get("city_image_url", "")
            }
            cities.append(city_info)
        
        # For hidden gems, look for cities with lower ratings or unique tags
        hidden_gem_cities = []
        for city in cities:
            rating = float(city.get("rating", 0))
            tags = city.get("tags", [])
            city_type = city.get("type", "").lower()
            if (rating < 4.0 or 
                any(tag.lower() in ['offbeat', 'hidden', 'local', 'authentic', 'lesser-known', 'traditional'] for tag in tags) or
                city_type in ['spiritual_city', 'adventure_destination']):
                hidden_gem_cities.append(city)
        
        return hidden_gem_cities[:5]

    def _get_places_and_activities_for_city(self, destination, city_name):
        """Get places and their activities for a specific city with enhanced city information"""
        city_doc = cities_collection.find_one({"state": destination, "city": city_name})
        if not city_doc:
            return {"places": [], "activities": [], "city_info": {}}
        
        # Enhanced city information
        city_info = {
            "name": city_doc.get("city", ""),
            "rating": city_doc.get("city_rating", 4.0),
            "description": city_doc.get("city_description", ""),
            "tags": city_doc.get("city_tags", []),
            "type": city_doc.get("city_type", "heritage_city"),
            "accessibility": city_doc.get("accessibility", "well_connected"),
            "highlights": city_doc.get("city_highlights", []),
            "image_url": city_doc.get("city_image_url", ""),
            "best_time_to_visit": city_doc.get("best_time_to_visit", "")
        }
        
        places = city_doc.get("places", [])
        all_activities = []
        
        # Extract activities from each place
        for place in places:
            place_activities = place.get("activities", [])
            for activity in place_activities:
                activity["place_name"] = place.get("name", "")
                activity["city_name"] = city_name
                all_activities.append(activity)
        
        return {
            "city_info": city_info,
            "places": places,
            "activities": all_activities
        }

    def _ai_recommend_activities(self, destination, travel_preferences, budget, start_date=None, end_date=None):
        # Get all cities in the destination state to extract activities from all places
        cities_data = cities_collection.find({"state": destination})
        if not cities_data:
            return []
        
        # Collect all activities from all places in all cities
        all_activities = []
        for city_doc in cities_data:
            city_name = city_doc.get("city", "")
            places = city_doc.get("places", [])
            for place in places:
                place_activities = place.get("activities", [])
                for activity in place_activities:
                    activity["place_name"] = place.get("name", "")
                    activity["city_name"] = city_name
                    all_activities.append(activity)
        
        # Calculate trip duration in days
        duration_days = 3
        if start_date and end_date:
            try:
                from datetime import datetime
                d1 = datetime.fromisoformat(str(start_date)[:10])
                d2 = datetime.fromisoformat(str(end_date)[:10])
                duration_days = max(1, (d2 - d1).days + 1)
            except Exception:
                pass
        
        # Filter activities based on user preferences
        filtered_activities = []
        for activity in all_activities:
            # Filter based on user preferences
            if self._activity_matches_preferences(activity, travel_preferences):
                filtered_activities.append(activity)
        
        # Return top activities (limit to reasonable number)
        return filtered_activities[:10]
    
    def _activity_matches_preferences(self, activity, travel_preferences):
        """Check if activity matches user preferences"""
        activity_name = activity.get("name", "").lower()
        activity_type = activity.get("type", "").lower()
        
        # Check based on travel excitement
        travel_excitement = travel_preferences.get('travel_excitement', '').lower()
        if travel_excitement == 'exploring' and any(word in activity_name for word in ['trek', 'hike', 'adventure', 'explore']):
            return True
        elif travel_excitement == 'relaxing' and any(word in activity_name for word in ['spa', 'yoga', 'meditation', 'relax']):
            return True
        elif travel_excitement == 'cultural' and any(word in activity_name for word in ['museum', 'temple', 'heritage', 'culture']):
            return True
        
        # Check based on free time preference
        free_time = travel_preferences.get('free_time_preference', '').lower()
        if free_time == 'outdoor' and any(word in activity_name for word in ['outdoor', 'nature', 'park', 'garden']):
            return True
        elif free_time == 'indoor' and any(word in activity_name for word in ['indoor', 'museum', 'shopping', 'cinema']):
            return True
        
        # Default: include if no specific preference or activity doesn't match any preference
        return True

    def _popular_activities(self, destination, exclude_names=None):
        city_doc = cities_collection.find_one({"state": destination})
        if not city_doc:
            return []
        activities = []
        for place in city_doc.get("places", []):
            place_activities = place.get("activities", [])
            for activity in place_activities:
                activity["place_name"] = place.get("name", "")
                activities.append(activity)
        # Exclude already recommended
        if exclude_names:
            activities = [a for a in activities if a.get("name") not in exclude_names]
        # Sort by rating if available, otherwise return first 5
        return sorted(activities, key=lambda x: self.safe_int(x.get("rating", 0)), reverse=True)[:5]

    def _hidden_activities(self, destination, exclude_names=None):
        city_doc = cities_collection.find_one({"state": destination})
        if not city_doc:
            return []
        activities = []
        for place in city_doc.get("places", []):
            place_activities = place.get("activities", [])
            for activity in place_activities:
                activity["place_name"] = place.get("name", "")
                activities.append(activity)
        # Exclude already recommended
        if exclude_names:
            activities = [a for a in activities if a.get("name") not in exclude_names]
        # For hidden activities, look for unique or less common activities
        hidden_activities = []
        for activity in activities:
            activity_name = activity.get("name", "").lower()
            # Consider it hidden if it has unique keywords
            if any(word in activity_name for word in ['offbeat', 'local', 'authentic', 'traditional', 'unique']):
                hidden_activities.append(activity)
        return hidden_activities[:5]

    def _ai_recommend_hotels(self, destination, budget, group_size, start_date=None, end_date=None):
        # Calculate trip duration in days
        duration_days = 3
        if start_date and end_date:
            try:
                from datetime import datetime
                d1 = datetime.fromisoformat(str(start_date)[:10])
                d2 = datetime.fromisoformat(str(end_date)[:10])
                duration_days = max(1, (d2 - d1).days + 1)
            except Exception:
                pass
        prompt = f"""
You are an expert travel planner. Recommend hotels in {destination} for a traveler with these details:

User Preferences:
- Group size: {group_size}

Trip Details:
- Budget: {budget} INR
- Trip duration: {duration_days} days

Instructions:
- Recommend 3-5 hotels based on budget and group size
- For each hotel provide: name, description
- Consider budget constraints and group size
- Return ONLY a valid JSON array like this:
[
  {{"name": "Hotel Name", "description": "Brief description"}},
  {{"name": "Another Hotel", "description": "Another description"}}
]
"""
        response = self.llm.invoke(prompt)
        return self._parse_llm_response(response)

    def _popular_hotels(self, destination, exclude_names=None):
        # For now, return empty as we don't have hotel data
        # In production, you would query a hotels collection or API
        return []

    def _budget_hotels(self, destination):
        # For budget-friendly hotels
        # For now, return empty as we don't have hotel data
        return []

    def _parse_llm_response(self, response):
        content = response.content if hasattr(response, 'content') else str(response)
        try:
            # Try to extract JSON from the response
            import re
            # Look for JSON array or object in the response
            json_match = re.search(r'(\[.*\]|\{.*\})', content, re.DOTALL)
            if json_match:
                json_str = json_match.group(1)
                return json.loads(json_str)
            else:
                # If no JSON found, try parsing the entire content
                return json.loads(content)
        except Exception:
            try:
                import demjson3
                return demjson3.decode(content)
            except Exception:
                # If all parsing fails, return empty array
                print(f"Failed to parse LLM response: {content[:200]}...")
                return []


# Example usage
if __name__ == "__main__":
    agent = TravelAgent()
    # Get actual user_id and trip_id from database
    try:
        user = trip_requests_collection.find_one() # Changed from users_collection to trip_requests_collection
        if user:
            user_id = user.get("userId")
            # Find a trip for this user
            trip = trip_requests_collection.find_one({"userId": user_id}) # Changed from users_collection to trip_requests_collection
            if trip:
                trip_id = trip.get("tripId")
                print(f"Found user: {user.get('name', 'Unknown')} (ID: {user_id})")
                print(f"Destination: {trip.get('tripData', {}).get('destination', 'Unknown')}")
                print(f"Budget: {trip.get('tripData', {}).get('budget', 0)} INR")
                print(f"Travel Dates: {trip.get('tripData', {}).get('start_date', 'Unknown')} to {trip.get('tripData', {}).get('end_date', 'Unknown')}")
                print("\n" + "="*50)
                print("Creating AI-powered itinerary...")
                itinerary = agent.create_smart_itinerary(user_id, trip_id)
                print("\n" + "="*50)
                print("GENERATED ITINERARY:")
                print("="*50)
                print(itinerary)
            else:
                print("No trips found for user. Please add a trip first.")
        else:
            print("No users found in database. Please add a user first using user_profile_db.py")
    except Exception as e:
        print(f"Error accessing database: {str(e)}")
        print("Make sure MongoDB is running and connected properly.") 