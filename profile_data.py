import json

def ask_multiple_choice(question, options):
    print(f"\n{question}")
    for key, value in options.items():
        print(f"{key}. {value['text']}")
    selected = input("Enter your choices separated by commas (e.g., 1,3): ")
    return selected.strip().split(",")


perfect_trip_options = {
    "1": {"text": "Chilling by the beach with no rush", "tags": ["relaxing", "coastal"]},
    "2": {"text": "Exploring historical spots and museums", "tags": ["cultural", "heritage"]},
    "3": {"text": "Doing adventurous stuff like hiking or scuba", "tags": ["adventure", "thrill"]},
    "4": {"text": "Visiting temples or ashrams for peace", "tags": ["spiritual", "quiet"]},
    "5": {"text": "Luxury staycation with food/spa", "tags": ["luxury", "comfort"]}
}

group_type_options = {
    "1": {"text": "Solo – I love doing my own thing", "tags": ["solo"]},
    "2": {"text": "With friends – we like exploring together", "tags": ["friends"]},
    "3": {"text": "With family – comfort and safety matter", "tags": ["family"]},
    "4": {"text": "With a partner – something cozy & romantic", "tags": ["partner", "romantic"]}
}

activity_options = {
    "1": {"text": "Nature & scenery", "tags": ["nature", "scenic"]},
    "2": {"text": "Local food & markets", "tags": ["food", "cultural"]},
    "3": {"text": "Adventure sports and treks", "tags": ["adventure", "outdoors"]},
    "4": {"text": "Spiritual sites & walks", "tags": ["spiritual", "heritage"]},
    "5": {"text": "Hidden/offbeat local places", "tags": ["unexplored", "offbeat"]}
}

pace_options = {
    "1": {"text": "Fast-paced – cover as much as I can!", "tags": ["fast"]},
    "2": {"text": "Balanced – mix of exploring and chilling", "tags": ["balanced"]},
    "3": {"text": "Laid-back – just vibes, no rush", "tags": ["slow"]}
}

mood_options = {
    "1": {"text": "Peaceful & quiet", "tags": ["peaceful"]},
    "2": {"text": "Festive & fun", "tags": ["festive"]},
    "3": {"text": "Romantic & scenic", "tags": ["romantic", "scenic"]},
    "4": {"text": "Thrilling & wild", "tags": ["thrilling", "wild"]},
    "5": {"text": "Rich in culture & heritage", "tags": ["cultural", "heritage"]}
}

def extract_tags(selections, options_map):
    tags = []
    for sel in selections:
        tags.extend(options_map.get(sel, {}).get("tags", []))
    return list(set(tags))

# Collect user inputs
print("Welcome to Trawell Personality & Trip Preference Builder")

age = int(input("Enter your age: "))
gender = input("Enter your gender (male/female/other): ")
location = input("Enter your current location (city): ")
destination = input("Where are you planning to go? (destination): ")
travel_dates = input("Enter your travel dates (e.g., 2025-12-22 to 2025-12-28): ")
budget = int(input("Enter your budget in INR (e.g., 15000): "))

# Ask core personality questions
vibe_selections = ask_multiple_choice("1. What's your idea of a perfect trip?", perfect_trip_options)
group_selections = ask_multiple_choice("2. How do you usually prefer to travel?", group_type_options)
activity_selections = ask_multiple_choice("3. What excites you more on a trip?", activity_options)
pace_selections = ask_multiple_choice("4. How do you like to pace your trips?", pace_options)
mood_selections = ask_multiple_choice("5. What kind of vibe are you looking for?", mood_options)

# Generate profile
user_profile = {
    "age": age,
    "gender": gender,
    "location": location,
    "destination": destination,
    "travel_dates": travel_dates,
    "budget": budget,
    "vibe": extract_tags(vibe_selections, perfect_trip_options),
    "group": extract_tags(group_selections, group_type_options),
    "activities": extract_tags(activity_selections, activity_options),
    "pace": extract_tags(pace_selections, pace_options),
    "mood": extract_tags(mood_selections, mood_options)
}

print("\n🧠 Your Agentic AI Profile:\n")
print(json.dumps(user_profile, indent=2))
