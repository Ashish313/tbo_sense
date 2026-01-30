from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, ValidationError
from tools.utils import load_data, save_data, create_response_json, handle_tool_error

class BookFlightInput(BaseModel):
    flight_id: str = Field(description="The ID of the flight to book.")
    num_travelers: int = Field(description="Number of people travelling.")
    passenger_names: List[str] = Field(description="List of passenger names.")

def book_flight(*args, **kwargs) -> str:
    """
    Book a specific flight for passengers.
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
            validated = BookFlightInput(**merged)
        except ValidationError as e:
            return create_response_json(f"Invalid payload: {e}", status=False)

        flight_id = validated.flight_id
        num_travelers = validated.num_travelers
        passenger_names = validated.passenger_names

        all_flights = load_data("flights.json")
        flight = next((f for f in all_flights if f["id"] == flight_id), None)
        
        if not flight:
            return create_response_json(
                "Flight ID not found.",
                status=False,
                error="Flight ID not found"
            )
            
        # Mocking a booking process
        total_price = flight["price"] * num_travelers
        booking_id = f"BKG-{flight_id}-{num_travelers}"
        
        booking_details = {
            "booking_id": booking_id,
            "flight": flight,
            "passengers": passenger_names,
            "total_price": total_price,
            "status": "Confirmed",
            "ticket_pdf": f"https://travel-bot.com/tickets/{booking_id}.pdf",
            "type": "flight"
        }

        # Persist booking
        bookings = load_data("bookings.json")
        if not isinstance(bookings, list):
            bookings = []
        bookings.append(booking_details)
        save_data("bookings.json", bookings)
        
        return create_response_json(
            f"Flight booked successfully! Ticket sent to {booking_details['ticket_pdf']}",
            status=True,
            data=booking_details
        )
        
    except Exception as ex:
        return handle_tool_error(ex, "book_flight")
