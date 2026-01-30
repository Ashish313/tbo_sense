from typing import Optional, Dict, Any
from pydantic import BaseModel, Field, ValidationError
from tools.utils import load_data, create_response_json, handle_tool_error

class SearchHotelsInput(BaseModel):
    location: str = Field(description="City or area name (e.g., 'Dubai', 'Paris').")
    check_in: str = Field(description="Check-in date (e.g., '2023-12-25').")
    budget: float = Field(default=0.0, description="Optional max price per night. Set to 0 if not specified.")
    guests: int = Field(default=2, description="Number of guests.")
    min_rating: float = Field(default=0.0, description="Minimum hotel rating (0-5).")

def search_hotels(*args, **kwargs) -> str:
    """
    Search for hotels in a specific location.
    """
    try:
        # Heuristics to extract state and payload from args
        payload_candidate: Optional[dict] = None

        if 'payload' in kwargs:
            payload_candidate = kwargs.pop('payload')

        if args:
            if len(args) >= 2 and isinstance(args[0], dict) and isinstance(args[1], dict):
                payload_candidate = payload_candidate or args[1]
            else:
                for a in args:
                    if isinstance(a, dict):
                        if payload_candidate is None:
                            payload_candidate = a

        merged: Dict[str, Any] = {}
        if payload_candidate:
            if not isinstance(payload_candidate, dict):
                return create_response_json("payload must be a dict", status=False)
            merged.update(payload_candidate)

        merged.update(kwargs)

        try:
            validated = SearchHotelsInput(**merged)
        except ValidationError as e:
            return create_response_json(f"Invalid payload: {e}", status=False)

        location = validated.location
        budget = validated.budget
        
        all_hotels = load_data("hotels.json")
        
        # Filter by location (case-insensitive)
        results = [
            h for h in all_hotels 
            if h["location"].lower() == location.lower()
        ]
        
        # Filter by budget (treat 0.0 as no limit)
        if budget > 0:
            results = [h for h in results if h["price_per_night"] <= budget]

        # Filter by rating
        if validated.min_rating > 0:
            results = [h for h in results if h.get("rating", 0) >= validated.min_rating]
            
        if not results:
            return create_response_json(f"No hotels found in {location} within budget.", status=True)

        # Limit to top 10
        results = results[:10]
        
        return create_response_json(
            f"Found {len(results)} hotels in {location}. [View detailed results](http://localhost:3000/view_results?type=hotels&location={location})",
            status=True,
            data=results,
            search_type="HOTEL"
        )

    except Exception as ex:
        return handle_tool_error(ex, "search_hotels")
