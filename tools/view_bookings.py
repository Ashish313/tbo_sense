from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field, ValidationError
from tools.utils import load_data, create_response_json, handle_tool_error

class ViewBookingsInput(BaseModel):
    booking_type: Optional[str] = Field(
        default=None, 
        description="Filter by booking type (e.g., 'flight', 'hotel', 'package'). If not provided, shows all bookings."
    )

def view_bookings(*args, **kwargs) -> str:
    """
    View user bookings (flights, hotels, packages).
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
            validated = ViewBookingsInput(**merged)
        except ValidationError as e:
            return create_response_json(f"Invalid payload: {e}", status=False)

        booking_type = validated.booking_type

        bookings = load_data("bookings.json")
        if not isinstance(bookings, list):
            bookings = []

        if booking_type:
            bookings = [b for b in bookings if b.get("type") == booking_type]

        if not bookings:
            return create_response_json(
                "No bookings found.",
                status=True,
                data=[]
            )

        return create_response_json(
            f"Found {len(bookings)} booking(s).",
            status=True,
            data=bookings,
            table=True # Hint to UI to render as table if possible
        )

    except Exception as ex:
        return handle_tool_error(ex, "view_bookings")
