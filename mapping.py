from typing import Dict
def get_mapping() -> Dict[str, str]:
    """
    Returns a mapping of user interests to Geoapify Places categories.
    """
    return {
    "park": "leisure.park",
    "landmark": "tourism,heritage",
    "attractions": "tourism.attraction",
    "restaurant": "catering.restaurant, catering",
    "bar": "catering.bar",
    "entertainment": "entertainment",
    "nature": "natural",
    "tradition": "religion, tourism.cultural",
    "culture": "religion, tourism.cultural",
    "stay": "accommodation",
    "room": "accommodation",
}