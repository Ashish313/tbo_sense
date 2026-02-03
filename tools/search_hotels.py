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
    Search for hotels in a specific location, considering availability on check-in date.
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
        check_in = validated.check_in
        budget = validated.budget
        min_rating = validated.min_rating
        
        all_hotels = load_data("hotels.json")
        
        results = []
        for hotel in all_hotels:
            # 1. Location match (fuzzy check)
            if location.lower() not in hotel["location"].lower() and location.lower() not in hotel.get("name", "").lower():
                continue
                
            # 2. Date/Availability check
            price_to_display = hotel.get("price_per_night", 0)
            
            # If hotel has availability data and we have a check_in date
            if check_in and "availability" in hotel:
                avail_data = hotel["availability"].get(check_in)
                if avail_data:
                    if avail_data.get("status") != "available":
                        continue  # Skip if sold out on this date
                    price_to_display = avail_data.get("price", price_to_display)
                else:
                    # Date not explicitly listed in availability map
                    # Fallback policy: if map exists but date missing, assume unavailable or rely on base?
                    # Let's rely on base price but mark as "request" if needed. 
                    # For now, just use base price to be permissive.
                    pass
            
            # 3. Budget check (using the specific date's price)
            if budget > 0 and price_to_display > budget:
                continue
            
            # 4. Rating check
            if min_rating > 0 and hotel.get("rating", 0) < min_rating:
                continue
                
            # Create result entry (copy to avoid mutating original cache)
            result_entry = hotel.copy()
            result_entry["price_per_night"] = price_to_display
            
            # Crucial: Remove the massive 'availability' map from the response to save tokens
            result_entry.pop("availability", None) 
            
            results.append(result_entry)
            
        if not results:
            return create_response_json(f"No hotels found in {location} for {check_in} within constraints.", status=True)

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
