import os
import json
import pandas as pd
from pymongo import MongoClient
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from pydantic import SecretStr
import time

# Load environment variables
load_dotenv()
mongo_uri = os.getenv("MONGODB_URI")
groq_api_key = os.getenv("GROQ_API_KEY")

# Connect to MongoDB
client = MongoClient(mongo_uri)
db = client['trawell_ai']
cities_collection = db['cities']

# Load the list of cities for a state
STATE = "Rajasthan"  # Change as needed
cities_df = pd.read_csv("Indian_Cities_States.csv")
cities = cities_df[cities_df['state'].str.lower() == STATE.lower()]['city'].tolist()

# Set up the LLM
llm = ChatGroq(
    api_key=SecretStr(groq_api_key) if groq_api_key else None,
    model="llama3-70b-8192"
)

for city in cities:
    # Skip if this city is already in the database
    if cities_collection.find_one({"state": STATE, "city": city}):
        print(f"Skipping {city} (already in database)")
        continue
    prompt = f"""
    List all major tourist places and activities in {city}, {STATE}, India. 
    For each place, provide:
    - name
    - type (list: e.g., ["historical", "adventure"])
    - description
    - uniqueness
    - rating (out of 5, float)
    - stars (1-5, int)
    - best_time_to_visit
    - tags (list)
    - time_required (e.g., "1-2 days" or in hours)
    - cost (typical cost for main activity, in INR)
    - min_age (minimum recommended age)
    - activities: A list of activities/experiences at the place. For each activity:
      - name
      - type
      - cost
      - min_age
      - duration
      - description
      - tags (list)
      - best_time_of_day (e.g., Morning, Afternoon, Evening)
      - popularity (one of: "unexplored", "most famous", "impromptu")
    Format the output as a JSON array of objects.
    """
    print(f"Processing city: {city}")
    response = llm.invoke(prompt)
    content = response.content if hasattr(response, 'content') else str(response)

    # Only parse if content is a string and not empty
    if isinstance(content, str) and content.strip():
        try:
            places = json.loads(content)
        except json.JSONDecodeError:
            import re
            match = re.search(r'(\[.*\])', content, re.DOTALL)
            if match:
                try:
                    places = json.loads(match.group(1))
                except json.JSONDecodeError:
                    print(f"Malformed JSON for city: {city}")
                    continue
            else:
                print(f"No JSON found for city: {city}")
                continue
    elif isinstance(content, list):
        places = content
    else:
        print(f"No valid data for {city}")
        continue

    # Insert into MongoDB
    if isinstance(places, list) and places:
        doc = {
            "state": STATE,
            "city": city,
            "places": places
        }
        cities_collection.insert_one(doc)
        print(f"Inserted {len(places)} places for {city}")
    else:
        print(f"No valid data for {city}")

    # To avoid rate limits or overloading the LLM API
    time.sleep(5)