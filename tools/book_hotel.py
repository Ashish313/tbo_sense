from typing import Optional, Dict, Any
from pydantic import BaseModel, Field, ValidationError
from tools.utils import load_data, save_data, create_response_json, handle_tool_error

class BookHotelInput(BaseModel):
    hotel_id: str = Field(description="The ID of the hotel.")
    check_in: str = Field(description="Check-in date (YYYY-MM-DD).")
    check_out: str = Field(description="Check-out date (YYYY-MM-DD).")
    room_type: str = Field(description="Type of room (e.g., 'Standard', 'Deluxe', 'Suite').")
    guests: int = Field(description="Number of guests.")

def book_hotel(*args, **kwargs) -> str:
    """
    Book a hotel room.
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
            validated = BookHotelInput(**merged)
        except ValidationError as e:
            return create_response_json(f"Invalid payload: {e}", status=False)

        hotel_id = validated.hotel_id
        check_in = validated.check_in
        check_out = validated.check_out
        room_type = validated.room_type
        guests = validated.guests

        all_hotels = load_data("hotels.json")
        hotel = next((h for h in all_hotels if h["id"] == hotel_id), None)
        
        if not hotel:
            return create_response_json(
                "Hotel ID not found.",
                status=False,
                error="Hotel ID not found"
            )
            
        # Mock booking
        booking_id = f"HTL-{hotel_id}-{room_type[:3].upper()}"
        
        booking_details = {
            "booking_id": booking_id,
            "hotel_name": hotel["name"],
            "dates": f"{check_in} to {check_out}",
            "room_type": room_type,
            "guests": guests,
            "status": "Confirmed",
            "invoice_pdf": f"https://travel-bot.com/invoices/{booking_id}.pdf",
            "type": "hotel"
        }
        
        # Persist booking
        bookings = load_data("bookings.json")
        if not isinstance(bookings, list):
            bookings = []
        bookings.append(booking_details)
        save_data("bookings.json", bookings)
        
        return create_response_json(
            f"Hotel booked successfully! Invoice: {booking_details['invoice_pdf']}",
            status=True,
            data=booking_details
        )
        
    except Exception as ex:
        return handle_tool_error(ex, "book_hotel")
