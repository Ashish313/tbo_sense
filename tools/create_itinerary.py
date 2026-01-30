from typing import Optional, Dict, Any
from pydantic import BaseModel, Field, ValidationError
from tools.utils import load_data, create_response_json, handle_tool_error

class CreateItineraryInput(BaseModel):
    destination: str = Field(description="City to visit.")
    duration_days: int = Field(description="Number of days for the trip.")
    purpose: str = Field(description="Purpose of visit (e.g., 'leisure', 'business').")
    budget: float = Field(default=5000.0, description="Max budget in INR (e.g. 5000.0, 10000.50).")

def create_itinerary(*args, **kwargs) -> str:
    """
    Create a travel itinerary based on user preferences.
    """
    try:
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
            validated = CreateItineraryInput(**merged)
        except ValidationError as e:
            return create_response_json(f"Invalid payload: {e}", status=False)

        destination = validated.destination
        duration_days = validated.duration_days
        purpose = validated.purpose
        budget = validated.budget
        
        # Numeric budget only
        budget_msg = f" within {budget:.2f} INR"
        
        destinations_data = load_data("destinations.json")
        
        # Check if we have data for this destination
        # Case-insensitive lookup
        city_data = None
        for city, data in destinations_data.items():
            if city.lower() == destination.lower():
                city_data = data
                break
                
        if not city_data:
            return create_response_json(
                f"Sorry, we don't have itinerary data for {destination} yet.",
                status=False,
                error="Destination not found"
            )
            
        # Check purpose
        purpose_key = purpose.lower()
        if purpose_key not in city_data:
            # Fallback to first available key or error
            available = list(city_data.keys())
            if available:
                purpose_key = available[0] # Fallback
            else:
                return create_response_json(
                    f"No activities found for {destination}.",
                    status=False,
                    error="No activities"
                )

        activities = city_data[purpose_key]
        
        # Truncate or loop if duration > available days (simplified: just return what we have)
        selected_activities = activities[:duration_days]
        
        result_data = {
            "destination": destination,
            "duration": duration_days,
            "purpose": purpose,
            "itinerary": selected_activities
        }
        
        return create_response_json(
            f"Generated {len(selected_activities)}-day {purpose} itinerary for {destination}{budget_msg}.",
            status=True,
            data=result_data,
            search_type="ITINERARY"
        )

    except Exception as ex:
        return handle_tool_error(ex, "create_itinerary")
