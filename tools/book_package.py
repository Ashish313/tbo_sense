from typing import Optional, Dict, Any
from pydantic import BaseModel, Field, ValidationError
from tools.utils import load_data, save_data, create_response_json, handle_tool_error

class BookPackageInput(BaseModel):
    package_id: str = Field(description="ID of the package.")
    travel_date: str = Field(description="Date of travel.")
    travelers: int = Field(description="Number of people.")
    customization: str = Field(default="", description="Any specific requests/customizations.")

def book_package(*args, **kwargs) -> str:
    """
    Book a travel package.
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
            validated = BookPackageInput(**merged)
        except ValidationError as e:
            return create_response_json(f"Invalid payload: {e}", status=False)

        package_id = validated.package_id
        travel_date = validated.travel_date
        travelers = validated.travelers
        customization = validated.customization

        all_pkgs = load_data("packages.json")
        pkg = next((p for p in all_pkgs if p["id"] == package_id), None)
        
        if not pkg:
            return create_response_json(
                "Package ID not found.",
                status=False,
                error="Package ID not found"
            )
            
        booking_id = f"PKG-{package_id}-{travelers}"
        
        booking_details = {
            "booking_id": booking_id,
            "package": pkg["name"],
            "destination": pkg["destination"],
            "date": travel_date,
            "travelers": travelers,
            "customization": customization,
            "status": "Confirmed",
            "docs_link": f"https://travel-bot.com/docs/{booking_id}.zip",
            "type": "package"
        }
        
        # Persist booking
        bookings = load_data("bookings.json")
        if not isinstance(bookings, list):
            bookings = []
        bookings.append(booking_details)
        save_data("bookings.json", bookings)
        
        return create_response_json(
            f"Package booked! Documents: {booking_details['docs_link']}",
            status=True,
            data=booking_details
        )

    except Exception as ex:
        return handle_tool_error(ex, "book_package")
