# main.py
from fastapi import FastAPI, HTTPException
from google.cloud import firestore
from pymongo import MongoClient
from pydantic import BaseModel
from datetime import datetime
import os
import dotenv

dotenv.load_dotenv()

# Initialize FastAPI
app = FastAPI()

# Initialize Firestore
firestore_client = firestore.Client()

# Initialize MongoDB
mongo_client = MongoClient(os.getenv("MONGODB_URI"))
mongo_db = mongo_client["trawell"]
mongo_collection = mongo_db["trip_requests"]

# Request model
class SyncRequest(BaseModel):
    userId: str
    tripId: str

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

        return {"message": "Trip synced to MongoDB successfully."}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
