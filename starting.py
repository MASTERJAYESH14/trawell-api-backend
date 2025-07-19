from langchain.agents import Tool
from langchain.agents import initialize_agent
from langchain_groq import ChatGroq
from dotenv import load_dotenv
load_dotenv()


# --- Sub-agent: Seasonal Hotspot ---
def seasonal_hotspot_agent(travel_dates: str):
    month = int(travel_dates[5:7])
    if month in [12, 1, 2]:
        return "Winter: Try Manali, Gulmarg, or Jaipur"
    elif month in [4, 5, 6]:
        return "Summer: Try Coorg, Ooty, or Meghalaya"
    else:
        return "Monsoon/Post-Monsoon: Try Lonavala, Chikmagalur"

# --- Sub-agent: Regional Contrast ---
def regional_contrast_agent(region: str):
    mapping = {
        "Punjab": "Try South India or beachside destinations like Goa or Kerala",
        "Kerala": "Try North India like Himachal or Rajasthan",
        "Himachal": "Try Goa, Udaipur, or Rann of Kutch"
    },
    return mapping.get(region, "Explore new regions outside your home zone")

# --- Sub-agent: Cultural Suggestions ---
def cultural_agent(region: str):
    culture_map = {
        "Punjab": "Visit Golden Temple, Virasat-e-Khalsa",
        "UP": "Visit Ayodhya, Kashi Vishwanath, and Sarnath",
        "Maharashtra": "Visit Shirdi and Ajanta-Ellora"
    }
    return culture_map.get(region, "Explore local religious and historical sites")

# --- Sub-agent: Personality Mapper ---
def personality_agent(profile: str):
    # profile = JSON-like string, or keys like "Adventure, Cultural"
    if "Relaxation" in profile and "Cultural" in profile:
        return "You’d enjoy peaceful yet meaningful trips like Rishikesh or Varanasi"
    elif "Adventure" in profile:
        return "Try Rishikesh for rafting or Manali for trekking"
    elif "Fun" in profile:
        return "Consider Goa or Bangalore for lively energy"
    return "Suggesting destinations based on mixed personality traits"

tools = [
    Tool(
        name="SeasonalHotspot",
        func=seasonal_hotspot_agent,
        description="Suggests hotspots based on travel dates"
    ),
    Tool(
        name="RegionalContrast",
        func=regional_contrast_agent,
        description="Suggests contrasting destinations based on user's current region"
    ),
    Tool(
        name="CulturalSuggestions",
        func=cultural_agent,
        description="Suggests culturally significant locations based on region"
    ),
    Tool(
        name="PersonalityBasedRecommendations",
        func=personality_agent,
        description="Suggests destinations based on user personality"
    )
]

llm = ChatGroq(model_name= "llama3-8b-8192",)
agent = initialize_agent(
    tools,
    llm,
    agent_type="zero-shot-react-description",
    verbose=True
)

query = """
My travel dates are 2025-12-22 to 2025-12-28.
I live in Punjab.
My travel personality includes Relaxation and Cultural interests.
What destinations do you suggest?
"""

response = agent.run(query)
print("\n🧭 Trawell Agentic AI Suggestion:\n", response)
