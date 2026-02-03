from typing import Optional, Dict, Any
from pydantic import BaseModel, Field, ValidationError
from tools.utils import load_data, create_response_json, handle_tool_error

class SearchFlightsInput(BaseModel):
    origin: str = Field(description="Departure city.")
    destination: str = Field(description="Arrival city.")
    date: str = Field(description="Date of travel (e.g., '2023-12-25').")
    airline: str = Field(default="", description="Optional airline filter.")
    passengers: int = Field(default=1, description="Number of travelers.")
    cabin_class: str = Field(default="Economy", description="Cabin class (Economy, Business, First).")
    trip_type: str = Field(default="one-way", description="Trip type: 'one-way' or 'round-trip'.")
    return_date: str = Field(default="", description="Return date for round-trip (YYYY-MM-DD).")
    budget: int = Field(default=0, description="Optional maximum price per ticket.")

def search_flights(*args, **kwargs) -> str:
    """
    Search for flights between cities on specific dates (one-way or round-trip).
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
        airline_filter = validated.airline
        passengers = validated.passengers
        cabin_class = validated.cabin_class
        trip_type = validated.trip_type.lower()
        return_date = validated.return_date
        
        budget = validated.budget
        
        all_flights = load_data("flights.json")
        
        # --- Helper for filtering ---
        def filter_flights(org, dst, travel_date):
            # Using startswith to handle "Delhi" match against "Delhi, India"
            matches = [
                f for f in all_flights
                if org.lower() in f.get("origin", "").lower()
                and dst.lower() in f.get("destination", "").lower()
                and f.get("date") == travel_date
            ]
            
            # Additional Country-based matching check if needed (e.g. searching "India" -> "Maldives")
            # But relying on startswith or "in" might be broad. Let's stick to startswith first.
            
            if airline_filter:
                matches = [f for f in matches if airline_filter.lower() in f["airline"].lower()]
            
            if budget > 0:
                matches = [f for f in matches if f["price"] <= budget]
                
            return matches[:10]

        # 1. Outbound Search
        outbound_results = filter_flights(origin, destination, date)
        
        if not outbound_results:
            return create_response_json(f"No flights found from {origin} to {destination} on {date}.", status=True)

        data_response = {"outbound": outbound_results}
        msg = f"Found {len(outbound_results)} outbound flights."

        # 2. Inbound Search (if round-trip)
        if trip_type == "round-trip":
            if not return_date:
                return create_response_json(
                    "Return date is required for round-trip search. Please provide a return date.", 
                    status=False
                )
            
            inbound_results = filter_flights(destination, origin, return_date)
            data_response["inbound"] = inbound_results
            msg += f" And {len(inbound_results)} return flights."
        
        return create_response_json(
            f"{msg} [View results](http://localhost:3000/view_results?type=flights)",
            status=True,
            data=data_response,
            search_type="FLIGHT"
        )

    except Exception as ex:
        return handle_tool_error(ex, "search_flights")
