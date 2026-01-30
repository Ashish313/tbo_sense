from typing import Optional, Dict, Any
from pydantic import BaseModel, Field, ValidationError
from tools.utils import load_data, create_response_json, handle_tool_error

class SearchFlightsInput(BaseModel):
    origin: str = Field(description="Departure city.")
    destination: str = Field(description="Arrival city.")
    date: str = Field(description="Date of travel (e.g., '2023-12-25').")
    airline: str = Field(default="", description="Optional airline filter.")

def search_flights(*args, **kwargs) -> str:
    """
    Search for flights between two cities.
    """
    try:
        # Heuristics to extract state and payload from args
        payload_candidate: Optional[dict] = None

        # If called with named 'payload' in kwargs, use it and remove from kwargs merging
        if 'payload' in kwargs:
            payload_candidate = kwargs.pop('payload')

        # Scan args for dicts
        if args:
            if len(args) >= 2 and isinstance(args[0], dict) and isinstance(args[1], dict):
                payload_candidate = payload_candidate or args[1]
            else:
                for a in args:
                    if isinstance(a, dict):
                        if payload_candidate is None:
                            payload_candidate = a

        # Merge payload_candidate and kwargs into a single input dict
        merged: Dict[str, Any] = {}
        if payload_candidate:
            if not isinstance(payload_candidate, dict):
                return create_response_json(
                    "payload must be a dict",
                    status=False
                )
            merged.update(payload_candidate)

        # Now kwargs contain field names
        merged.update(kwargs)  # explicit kwargs take precedence

        # Validate with Pydantic model
        try:
            validated = SearchFlightsInput(**merged)
        except ValidationError as e:
            return create_response_json(
                f"Invalid payload: {e}",
                status=False
            )

        # Access validated fields
        origin = validated.origin
        destination = validated.destination
        date = validated.date

        all_flights = load_data("flights.json")
        
        # Filter (case-insensitive)
        results = [
            f for f in all_flights
            if f["origin"].lower() == origin.lower() and f["destination"].lower() == destination.lower()
        ]
        
        # Filter by airline if specified
        if validated.airline:
            results = [f for f in results if validated.airline.lower() in f["airline"].lower()]
        
        if not results:
            return create_response_json(f"No flights found from {origin} to {destination}.", status=True)
            
        # Limit to top 10
        results = results[:10]

        return create_response_json(
            f"Found {len(results)} flights from {origin} to {destination}. [View detailed results](http://localhost:3000/view_results?type=flights&location={destination})", # Using location param for consistency/simplicity on client side or update client to handle multiple
            data=results,
            search_type="FLIGHT"
        )

    except Exception as ex:
        return handle_tool_error(ex, "search_flights")
