from pymongo import MongoClient
import uuid
from dotenv import load_dotenv
import os

load_dotenv()
mongodb_uri = os.getenv('MONGODB_URI')
print(f"Loaded URI: '{mongodb_uri}'")
#conneting to mongodb with pymongo
client = MongoClient(mongodb_uri) #establishing connection
db = client['trawell_ai'] #creating database named 'trawell_ai'
user_collection = db['users'] #create collection/table named users and giving it object name as user_colelction


def ask_with_options(question, options):
    print(question)
    for idx, option in enumerate(options, 1):
        print(f"{idx}. {option}")
    while True:
        try:
            choice = int(input("Enter the number of your choice: "))
            if 1 <= choice <= len(options):
                return options[choice - 1]
            else:
                print("Please enter a valid number.")
        except ValueError:
            print("Please enter a number.")

def ask_multi_select(question, options):
    print(question)
    for idx, option in enumerate(options, 1):
        print(f"{idx}. {option}")
    print("You can select multiple options (e.g., 1,3,5).")
    while True:
        choices = input("Enter your choices: ")
        try:
            indices = [int(x.strip()) for x in choices.split(",") if x.strip()]
            if all(1 <= idx <= len(options) for idx in indices):
                # Remove duplicates and preserve order
                seen = set()
                selected = []
                for idx in indices:
                    if idx not in seen:
                        selected.append(options[idx - 1])
                        seen.add(idx)
                return selected
            else:
                print("Please enter valid numbers from the list.")
        except ValueError:
            print("Please enter numbers separated by commas.")

# Define options for each question
excites_options = [
    "Exploring new places", "Meeting new people", "Relaxing", "Adventure activities",
    "Spiritual experiences", "Food & culture", "Other"
]
free_time_options = [
    "Outdoor adventures", "Visiting historical sites", "Meditation/yoga", "Shopping",
    "Socializing", "Reading/quiet time", "Other"
]
travel_style_options = [
    "I love spontaneous plans", "I prefer a well-planned itinerary", "I like a mix of both"
]
group_size_options = [
    "Solo", "Couple", "Small group (3-5)", "Large group (6+)"
]
new_things_options = [
    "Always excited", "Sometimes", "Only if comfortable", "Prefer familiar things"
]

# Collect user data from terminal
user_profile = {
    "user_id": str(uuid.uuid4()),
    "name": input("Enter your name: "),
    "age": int(input("Enter your age: ")),
    "travel_dates": input("Enter travel dates (YYYY-MM-DD to YYYY-MM-DD): "),
    "start_place": input("Enter your start place: "),
    "destination": input("Enter your destination: "),
    "budget": float(input("Enter your budget (INR): ")),
    "personality_answers": {
        "travel_excites": ask_multi_select(
            "What excites you most about traveling?", excites_options
        ),
        "free_time": ask_multi_select(
            "How do you prefer to spend your free time during a trip?", free_time_options
        ),
        "travel_style": ask_with_options(
            "Which statement best describes your travel style?", travel_style_options
        ),
        "group_size": ask_with_options(
            "What's your ideal group size for a trip?", group_size_options
        ),
        "new_things": ask_with_options(
            "How do you feel about trying new things (food, activities, experiences)?", new_things_options
        ),
    }
}

user_collection.insert_one(user_profile)
print("User profile saved to users table in trawell ai database under trawell cluster")