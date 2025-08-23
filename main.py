# main.py
from fastapi import FastAPI, HTTPException, Body
from google.cloud import firestore
from pymongo import MongoClient
from pydantic import BaseModel
from datetime import datetime
import os
import dotenv
from travel_agent import TravelAgent

dotenv.load_dotenv()

# Initialize FastAPI
app = FastAPI()

# Initialize Firestore
firestore_client = firestore.Client()

# Initialize MongoDB
mongo_client = MongoClient(os.getenv("MONGODB_URI"))
mongo_db = mongo_client["trawell"]
mongo_collection = mongo_db["trip_requests"]
cities_collection = mongo_db["cities"]

# Request models
class SyncRequest(BaseModel):
    userId: str
    tripId: str

class ImageRequest(BaseModel):
    place_name: str
    city_name: str
    state_name: str

class EnhancedRecommendationRequest(BaseModel):
    userId: str
    tripId: str
    destination_input: str

@app.post("/sync_trip")
def sync_trip(request: SyncRequest):
    user_id = request.userId
    trip_id = request.tripId

    try:
        # Fetch user travelPreferences
        user_ref = firestore_client.collection("users").document(user_id)
        user_doc = user_ref.get()
        if not user_doc.exists:
            raise HTTPException(status_code=404, detail="User not found")
        travel_preferences = (user_doc.to_dict() or {}).get("travelPreferences", {})

        # Fetch trip data
        trip_ref = user_ref.collection("trip_requests").document(trip_id)
        trip_doc = trip_ref.get()
        if not trip_doc.exists:
            raise HTTPException(status_code=404, detail="Trip not found")
        trip_data = trip_doc.to_dict()

        # Create combined MongoDB document
        combined_data = {
            "userId": user_id,
            "tripId": trip_id,
            "travelPreferences": travel_preferences,
            "tripData": trip_data,
            "syncedAt": datetime.utcnow().isoformat()
        }

        # Insert into MongoDB (upsert)
        mongo_collection.update_one(
            {"userId": user_id, "tripId": trip_id},
            {"$set": combined_data},
            upsert=True
        )

        # Trigger AI agent to generate enhanced recommendations
        agent = TravelAgent()
        
        # Get the destination from trip data
        destination = trip_data.get("destination", "")
        if not destination:
            return {"message": "Trip synced, but destination not found for recommendations."}
        
        # Parse the destination to determine if it's state, city, or landmark
        parsed_destination = agent.parse_destination_input(destination)
        print(f"Destination '{destination}' parsed as: {parsed_destination['input_type']} (confidence: {parsed_destination['confidence']})")
        
        # Generate enhanced recommendations using the destination (handles state/city/landmark automatically)
        ai_result = agent.get_enhanced_recommendations(user_id, trip_id, destination)
        if isinstance(ai_result, dict) and ai_result.get("status") == "error":
            return {"message": "Trip synced, but enhanced recommendations failed.", "ai_error": ai_result.get("message")}

        # Save the enhanced recommendations to the trip document
        mongo_collection.update_one(
            {"userId": user_id, "tripId": trip_id},
            {"$set": {"enhancedItinerary": ai_result}}
        )

        # Get the input type for the success message
        input_type = parsed_destination['input_type']
        parsed_value = parsed_destination['parsed_value']
        
        return {
            "message": f"Trip synced to MongoDB and enhanced recommendations generated successfully.",
            "destination_info": {
                "original_input": destination,
                "parsed_type": input_type,
                "parsed_value": parsed_value,
                "confidence": parsed_destination['confidence']
            }
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class ItineraryRequest(BaseModel):
    userId: str
    tripId: str

@app.post("/get_itinerary")
def get_itinerary(request: ItineraryRequest):
    user_id = request.userId
    trip_id = request.tripId

    # Fetch the trip document
    trip_doc = mongo_collection.find_one({"userId": user_id, "tripId": trip_id})

    if not trip_doc:
        raise HTTPException(status_code=404, detail="Trip not found")

    # Try to get enhanced itinerary first, fallback to initial itinerary
    itinerary = trip_doc.get("enhancedItinerary") or trip_doc.get("initialItinerary")

    if not itinerary:
        raise HTTPException(status_code=404, detail="Itinerary not found for this trip")

    return {
        "status": "success",
        "message": "Itinerary fetched successfully",
        "data": itinerary
    }

@app.post("/get_enhanced_recommendations")
def get_enhanced_recommendations(request: EnhancedRecommendationRequest):
    """
    Enhanced recommendation API that handles multiple input types:
    - State input (e.g., "Rajasthan") → returns cities in that state
    - City input (e.g., "Jaipur") → returns places in that city + nearby cities
    - Landmark input (e.g., "Hawa Mahal") → returns the landmark + nearby places + related cities
    
    NOTE: This is a standalone endpoint for testing enhanced recommendations.
    For the main flow:
    - /sync_trip: Syncs Firestore data to MongoDB and generates enhanced recommendations for the user's trip destination
    - /get_itinerary: Returns the enhanced itinerary generated by /sync_trip
    """
    user_id = request.userId
    trip_id = request.tripId
    destination_input = request.destination_input

    try:
        agent = TravelAgent()
        result = agent.get_enhanced_recommendations(user_id, trip_id, destination_input)
        
        if result.get("status") == "error":
            raise HTTPException(status_code=400, detail=result.get("message"))
        
        return {
            "status": "success",
            "message": "Enhanced recommendations generated successfully",
            "data": result
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/get_place_image")
def get_place_image(request: ImageRequest):
    """Get base64 image for a specific place"""
    try:
        city_doc = cities_collection.find_one({"state": request.state_name, "city": request.city_name})
        if city_doc:
            places = city_doc.get("places", [])
            for place in places:
                if place.get("name") == request.place_name:
                    image_base64 = place.get("image_base64")
                    if image_base64:
                        return {
                            "status": "success",
                            "image_base64": image_base64
                        }
        
        return {
            "status": "error",
            "message": "Image not found"
        }
    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }

# Health check endpoint
@app.get("/health")
def health_check():
    return {"status": "healthy", "message": "Trawell AI API is running"}

