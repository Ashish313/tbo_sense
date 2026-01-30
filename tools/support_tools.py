from typing import Optional, Dict, Any
from pydantic import BaseModel, Field, ValidationError
from tools.utils import create_response_json, handle_tool_error

# --- Input Models ---

class GetCancellationPolicyInput(BaseModel):
    booking_type: str = Field(description="One of 'flight', 'hotel', 'package'.")

class CheckBookingStatusInput(BaseModel):
    booking_id: str = Field(description="Booking ID.")

class CancelBookingInput(BaseModel):
    booking_id: str = Field(description="Booking ID.")
    reason: str = Field(description="Reason for cancellation.")

class GetBaggagePolicyInput(BaseModel):
    airline: str = Field(description="Name of the airline.")

class TrackFlightInput(BaseModel):
    flight_number: str = Field(description="Flight number (e.g. 6E-101).")
    date: str = Field(description="Date of flight.")

# --- Tool Functions ---

def _extract_payload(args, kwargs) -> Dict[str, Any]:
    """Helper to extract payload from args/kwargs safely."""
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
    if payload_candidate and isinstance(payload_candidate, dict):
        merged.update(payload_candidate)
    
    merged.update(kwargs)
    return merged

def get_cancellation_policy(*args, **kwargs) -> str:
    """Get cancellation policy for valid booking types."""
    try:
        merged = _extract_payload(args, kwargs)
        try:
            validated = GetCancellationPolicyInput(**merged)
        except ValidationError as e:
            return create_response_json(f"Invalid payload: {e}", status=False)

        booking_type = validated.booking_type
        
        policies = {
            "flight": "Free cancellation up to 24 hours before departure. 50% refund thereafter.",
            "hotel": "Free cancellation up to 48 hours before check-in.",
            "package": "Non-refundable if cancelled within 7 days of travel."
        }
        policy = policies.get(booking_type.lower(), "Policy not found for this type.")
        
        return create_response_json(
            "Retrieved policy.",
            status=True,
            data=policy
        )
    except Exception as ex:
        return handle_tool_error(ex, "get_cancellation_policy")

def check_booking_status(*args, **kwargs) -> str:
    """Check the status of a booking."""
    try:
        merged = _extract_payload(args, kwargs)
        try:
            validated = CheckBookingStatusInput(**merged)
        except ValidationError as e:
            return create_response_json(f"Invalid payload: {e}", status=False)

        booking_id = validated.booking_id
        
        # Mock status based on ID
        status = "Confirmed"
        if "CAN" in booking_id:
            status = "Cancelled"
            
        return create_response_json(
            f"Status is {status}",
            status=True,
            data={"booking_id": booking_id, "status": status}
        )
    except Exception as ex:
        return handle_tool_error(ex, "check_booking_status")

def cancel_booking(*args, **kwargs) -> str:
    """Cancel a booking."""
    try:
        merged = _extract_payload(args, kwargs)
        try:
            validated = CancelBookingInput(**merged)
        except ValidationError as e:
            return create_response_json(f"Invalid payload: {e}", status=False)

        booking_id = validated.booking_id
        reason = validated.reason
        
        return create_response_json(
            "Booking has been cancelled. Refund will be processed in 5-7 days.",
            status=True,
            data={"booking_id": booking_id, "status": "Cancelled", "reason": reason}
        )
    except Exception as ex:
        return handle_tool_error(ex, "cancel_booking")

def get_baggage_policy(*args, **kwargs) -> str:
    """Get baggage policy for an airline."""
    try:
        merged = _extract_payload(args, kwargs)
        try:
            validated = GetBaggagePolicyInput(**merged)
        except ValidationError as e:
            return create_response_json(f"Invalid payload: {e}", status=False)

        airline = validated.airline
        
        return create_response_json(
            f"Baggage policy for {airline}.",
            status=True,
            data="15kg check-in, 7kg cabin."
        )
    except Exception as ex:
        return handle_tool_error(ex, "get_baggage_policy")

def track_flight(*args, **kwargs) -> str:
    """Track valid flight status."""
    try:
        merged = _extract_payload(args, kwargs)
        try:
            validated = TrackFlightInput(**merged)
        except ValidationError as e:
            return create_response_json(f"Invalid payload: {e}", status=False)

        flight_number = validated.flight_number
        date = validated.date
        
        return create_response_json(
            f"Flight {flight_number} is on time.",
            status=True,
            data="On Time"
        )
    except Exception as ex:
        return handle_tool_error(ex, "track_flight")
