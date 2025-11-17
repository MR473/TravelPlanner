from tools import opentripmap_search
from dotenv import load_dotenv
import os
load_dotenv()

OTM_API_KEY = os.getenv("OPENTRIPMAP_API_KEY")

result = opentripmap_search.func(
    city="Paris",
    interests=["amusement_park"],
    limit=5,
)

print(result)
