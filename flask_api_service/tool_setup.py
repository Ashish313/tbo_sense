from typing import Dict, Any, Optional, List
from langchain_core.tools import StructuredTool
from pydantic import BaseModel, Field

from tools.search_hotels import search_hotels, SearchHotelsInput
from tools.search_flights import search_flights, SearchFlightsInput
from tools.create_itinerary import create_itinerary, CreateItineraryInput
from tools.book_flight import book_flight, BookFlightInput
from tools.book_hotel import book_hotel, BookHotelInput
from tools.search_packages import search_packages, SearchPackagesInput
from tools.book_package import book_package, BookPackageInput
from tools.support_tools import (
    get_cancellation_policy, GetCancellationPolicyInput,
    check_booking_status, CheckBookingStatusInput,
    cancel_booking, CancelBookingInput,
    get_baggage_policy, GetBaggagePolicyInput,
    track_flight, TrackFlightInput
)
from tools.book_trip import book_trip, BookTripInput
from tools.view_bookings import view_bookings, ViewBookingsInput

# ==========================================
# Structured Tools
# ==========================================

search_hotels_tool = StructuredTool.from_function(
    func=search_hotels,
    name="search_hotels",
    description=(
        "Search for hotels based on location, dates, and budget.\n\n"
        "USE THIS TOOL FOR:\n"
        "- Finding accommodation in a specific city\n"
        "- Checking hotel prices and availability\n"
        "- Filtering hotels by budget or number of guests\n\n"
        "COMMON QUESTION TYPES:\n"
        "✓ 'Find me a hotel in Maldives for next week'\n"
        "✓ 'Show me cheap hotels in Maldives'\n"
        "✓ 'I need a 5-star hotel in Maldives'\n"
        "✓ 'Hotels in Maldives under $100'\n"
        "✓ 'Looking for a place to stay in Maldives'\n\n"
        "PARAMETER:\n"
        "- location: Target city (required)\n"
        "- check_in: Date of arrival (required)\n"
        "- budget: Max price limit (optional)\n"
        "- guests: Count of people (default: 2)\n\n"
        "- min_rating: Minimum hotel rating (default: 0)\n\n"
        "EXAMPLES:\n"
        "User: 'Find hotels in Maldives'\n"
        "→ Call: search_hotels(location='Maldives', check_in='2024-02-01')\n"
    ),
    args_schema=SearchHotelsInput
)

search_flights_tool = StructuredTool.from_function(
    func=search_flights,
    name="search_flights",
    description=(
        "Search for flights between cities on specific dates.\n\n"
        "USE THIS TOOL FOR:\n"
        "- Finding flight tickets\n"
        "- Checking flight schedules and availability\n"
        "- Comparing flight options between destinations\n\n"
        "COMMON QUESTION TYPES:\n"
        "✓ 'Flights from Delhi to Maldives'\n"
        "✓ 'I want to fly to Maldives on 25th Dec'\n"
        "✓ 'Show me flights to Maldives'\n"
        "✓ 'Is there a flight from Mumbai to Goa tomorrow?'\n\n"
        "PARAMETER:\n"
        "- origin: Departure city (required)\n"
        "- destination: Arrival city (required)\n"
        "- date: Travel date (required)\n"
        "- airline: Airline name (optional, e.g., 'IndiGo', 'Vistara')\n"
        "- passengers: Number of travelers (optional, default 1)\n"
        "- cabin_class: Economy/Business/First (optional, default Economy)\n"
        "- trip_type: 'one-way' or 'round-trip' (optional, default one-way)\n"
        "- return_date: YYYY-MM-DD (required if trip_type='round-trip')\n"
        "- budget: Max price limit (optional)\n\n"
        "EXAMPLES:\n"
        "User: 'Flight from Delhi to Maldives'\n"
        "→ Call: search_flights(origin='Delhi', destination='Maldives', date='2024-03-10')\n"
        "User: '2 tickets to Bali business class'\n"
        "→ Call: search_flights(origin='...', destination='Bali', ..., passengers=2, cabin_class='Business')\n"
        "User: 'Round trip to Maldives from 1st to 5th Feb'\n"
        "→ Call: search_flights(..., trip_type='round-trip', date='2024-02-01', return_date='2024-02-05')\n"
    ),
    args_schema=SearchFlightsInput
)

create_itinerary_tool = StructuredTool.from_function(
    func=create_itinerary,
    name="create_itinerary",
    description=(
        "Generate a travel itinerary based on destination and preferences.\n\n"
        "USE THIS TOOL FOR:\n"
        "- Planning a trip structure\n"
        "- Getting suggestions for activities\n"
        "- Creating a day-by-day travel plan\n\n"
        "COMMON QUESTION TYPES:\n"
        "✓ 'Plan a 5-day trip to Maldives'\n"
        "✓ 'I want a 3-day itinerary for Maldives'\n"
        "✓ 'Suggest a honeymoon trip to Maldives'\n"
        "✓ 'Business trip plan for Maldives within 10000 INR'\n\n"
        "PARAMETER:\n"
        "- destination: Target city (required)\n"
        "- duration_days: Length of trip (required)\n"
        "- purpose: leisure/business (required)\n"
        "- budget: max price in INR (float) (optional)\n\n"
        "EXAMPLES:\n"
        "User: 'Make a 4 day plan for Maldives'\n"
        "→ Call: create_itinerary(destination='Maldives', duration_days=4, purpose='leisure')\n"
    ),
    args_schema=CreateItineraryInput
)

book_flight_tool = StructuredTool.from_function(
    func=book_flight,
    name="book_flight",
    description=(
        "Book a specific flight using its ID.\n\n"
        "USE THIS TOOL FOR:\n"
        "- Confirming a flight reservation\n"
        "- Finalizing a flight booking for passengers\n\n"
        "COMMON QUESTION TYPES:\n"
        "✓ 'Book flight FL-123'\n"
        "✓ 'Reserve this flight for me and my wife'\n"
        "✓ 'Confirm booking for flight 6E-202'\n\n"
        "PARAMETER:\n"
        "- flight_id: Unique ID from search results (required)\n"
        "- num_travelers: Count of passengers (required)\n"
        "- passenger_names: List of names (required)\n\n"
        "EXAMPLES:\n"
        "User: 'Book flight AI-101 for John'\n"
        "→ Call: book_flight(flight_id='AI-101', num_travelers=1, passenger_names=['John'])\n"
    ),
    args_schema=BookFlightInput
)

book_hotel_tool = StructuredTool.from_function(
    func=book_hotel,
    name="book_hotel",
    description=(
        "Book a specific hotel room.\n\n"
        "USE THIS TOOL FOR:\n"
        "- Reserving a hotel room\n"
        "- Confirming accommodation booking\n\n"
        "COMMON QUESTION TYPES:\n"
        "✓ 'Book the Hilton hotel'\n"
        "✓ 'Reserve a room at Hotel California'\n"
        "✓ 'Confirm my stay at the Marriott'\n\n"
        "PARAMETER:\n"
        "- hotel_id: Unique ID from search results (required)\n"
        "- check_in: Start date (required)\n"
        "- check_out: End date (required)\n"
        "- room_type: Standard/Deluxe/etc (required)\n"
        "- guests: Count of people (required)\n\n"
        "EXAMPLES:\n"
        "User: 'Book hotel H-999 for 2 nights'\n"
        "→ Call: book_hotel(hotel_id='H-999', ...)\n"
    ),
    args_schema=BookHotelInput
)

search_packages_tool = StructuredTool.from_function(
    func=search_packages,
    name="search_packages",
    description=(
        "Search for pre-planned holiday packages.\n\n"
        "USE THIS TOOL FOR:\n"
        "- Finding vacation deals\n"
        "- Browsing honeymoon, family, or adventure packages\n"
        "- Looking for all-inclusive trips\n\n"
        "COMMON QUESTION TYPES:\n"
        "✓ 'Show me holiday packages for Maldives'\n"
        "✓ 'Honeymoon packages under $2000'\n"
        "✓ 'Family trips to Europe'\n\n"
        "PARAMETER:\n"
        "- destination: Target region (optional)\n"
        "- budget: Max price (optional)\n"
        "- package_type: e.g. Honeymoon (optional)\n\n"
        "EXAMPLES:\n"
        "User: 'Maldives packages'\n"
        "→ Call: search_packages(destination='Maldives')\n"
    ),
    args_schema=SearchPackagesInput
)

book_package_tool = StructuredTool.from_function(
    func=book_package,
    name="book_package",
    description=(
        "Book a specific holiday package.\n\n"
        "USE THIS TOOL FOR:\n"
        "- Confirming a package tour reservation\n\n"
        "COMMON QUESTION TYPES:\n"
        "✓ 'Book the Maldives Delight package'\n"
        "✓ 'I want to buy this package'\n\n"
        "PARAMETER:\n"
        "- package_id: Unique ID (required)\n"
        "- travel_date: Start date (required)\n"
        "- travelers: Count of people (required)\n\n"
        "EXAMPLES:\n"
        "User: 'Book package P-505'\n"
        "→ Call: book_package(package_id='P-505', ...)\n"
    ),
    args_schema=BookPackageInput
)

get_cancellation_policy_tool = StructuredTool.from_function(
    func=get_cancellation_policy,
    name="get_cancellation_policy",
    description=(
        "Retrieve cancellation rules for bookings.\n\n"
        "USE THIS TOOL FOR:\n"
        "- Checking refund eligibility\n"
        "- Understanding cancellation charges\n\n"
        "COMMON QUESTION TYPES:\n"
        "✓ 'What is the cancellation policy for flights?'\n"
        "✓ 'Can I cancel my hotel booking?'\n"
        "✓ 'Is my package refundable?'\n\n"
        "PARAMETER:\n"
        "- booking_type: 'flight', 'hotel', or 'package' (required)\n"
    ),
    args_schema=GetCancellationPolicyInput
)

check_booking_status_tool = StructuredTool.from_function(
    func=check_booking_status,
    name="check_booking_status",
    description=(
        "Check current status of an existing booking.\n\n"
        "USE THIS TOOL FOR:\n"
        "- Verifying if a booking is confirmed\n"
        "- Checking PNR status\n\n"
        "COMMON QUESTION TYPES:\n"
        "✓ 'Is my flight confirmed?'\n"
        "✓ 'Check status for booking ID BKG-123'\n\n"
        "PARAMETER:\n"
        "- booking_id: Unique reference ID (required)\n"
    ),
    args_schema=CheckBookingStatusInput
)

cancel_booking_tool = StructuredTool.from_function(
    func=cancel_booking,
    name="cancel_booking",
    description=(
        "Process a cancellation for a booking.\n\n"
        "USE THIS TOOL FOR:\n"
        "- Cancelling a flight, hotel, or package\n"
        "- Requesting a refund (if applicable)\n\n"
        "COMMON QUESTION TYPES:\n"
        "✓ 'Cancel my flight BKG-999'\n"
        "✓ 'I want to cancel my hotel reservation'\n\n"
        "PARAMETER:\n"
        "- booking_id: Unique reference ID (required)\n"
        "- reason: Why are you cancelling? (required)\n"
    ),
    args_schema=CancelBookingInput
)

get_baggage_policy_tool = StructuredTool.from_function(
    func=get_baggage_policy,
    name="get_baggage_policy",
    description=(
        "Get baggage allowance information for an airline.\n\n"
        "USE THIS TOOL FOR:\n"
        "- Checking check-in and cabin bag limits\n"
        "- Finding excess baggage rules\n\n"
        "COMMON QUESTION TYPES:\n"
        "✓ 'How much luggage is allowed on Emirates?'\n"
        "✓ 'Baggage policy for Indigo'\n\n"
        "PARAMETER:\n"
        "- airline: Name of airline (required)\n"
    ),
    args_schema=GetBaggagePolicyInput
)

track_flight_tool = StructuredTool.from_function(
    func=track_flight,
    name="track_flight",
    description=(
        "Get real-time status of a flight.\n\n"
        "USE THIS TOOL FOR:\n"
        "- Checking if a flight is on time\n"
        "- Finding gate information or delays\n\n"
        "COMMON QUESTION TYPES:\n"
        "✓ 'Is flight 6E-101 on time?'\n"
        "✓ 'Track flight AI-202'\n\n"
        "PARAMETER:\n"
        "- flight_number: e.g. AA-123 (required)\n"
        "- date: Flight date (required)\n"
    ),
    args_schema=TrackFlightInput
)

view_bookings_tool = StructuredTool.from_function(
    func=view_bookings,
    name="view_bookings",
    description=(
        "View a list of your existing bookings.\n\n"
        "USE THIS TOOL FOR:\n"
        "- Checking what flights/hotels/packages you have booked\n"
        "- Retrieving booking details\n\n"
        "COMMON QUESTION TYPES:\n"
        "✓ 'Show my bookings'\n"
        "✓ 'What flights have I booked?'\n"
        "✓ 'List my hotel reservations'\n\n"
        "PARAMETER:\n"
        "- booking_type: 'flight', 'hotel', or 'package' (optional)\n"
    ),
    args_schema=ViewBookingsInput
)

book_trip_tool = StructuredTool.from_function(
    func=book_trip,
    name="book_trip",
    description=(
        "Unified tool to book flights, hotels, or packages.\n\n"
        "USE THIS TOOL FOR:\n"
        "- Booking any type of trip (flight/hotel/package)\n"
        "- When user wants to proceed with a booking\n\n"
        "COMMON QUESTION TYPES:\n"
        "✓ 'I want to book this flight'\n"
        "✓ 'Book the hotel for me'\n"
        "✓ 'Proceed with package booking'\n\n"
        "PARAMETER:\n"
        "- booking_type: 'flight', 'hotel', or 'package' (required)\n"
        "- details: Optional dictionary of booking details\n"
    ),
    args_schema=BookTripInput
)

# List of tools to export
tools = [
    search_hotels_tool,
    search_flights_tool,
    create_itinerary_tool,
    book_flight_tool,
    book_hotel_tool,
    search_packages_tool,
    book_package_tool,
    get_cancellation_policy_tool,
    check_booking_status_tool,
    cancel_booking_tool,
    get_baggage_policy_tool,
    track_flight_tool,
    view_bookings_tool,
    book_trip_tool
]

# ==========================================
# Tool Registry
# ==========================================

def get_tool_registry():
    registry = {}

    registry["search_hotels"] = {
        "tool": search_hotels_tool,
        "description": f"""
            1. Search for hotels in Maldives
            2. Check hotel prices and availability
            3. Find hotels within a specific budget
            4. Look for accommodation for specific dates
            5. Find hotels for families or groups (guest count)
            6. "Find a hotel in Maldives"
            7. "Show me cheap hotels in Maldives"
            8. "I need a 5-star resort in Maldives"
            9. "Are there any hotels available next week?"
            10. "Find hotels with rating 4 and above"
            11. "Show me highly rated hotels in Maldives"
        """,
        "schema": SearchHotelsInput.model_json_schema()
    }

    registry["search_flights"] = {
        "tool": search_flights_tool,
        "description": f"""
            1. Search for flight tickets between cities
            2. Check availability of flights on specific dates
            3. Compare flight options for travel
            4. "Find flights from Delhi to Maldives"
            5. "Ticket from India to Maldives on 1st Jan"
            6. "Are there flights to Maldives tomorrow?"
            7. "Search air tickets"
            8. "Show me Indigo flights to Maldives"
            9. "Find flights with Emirates"
            10. "Flights for 2 people"
            11. "Business class flight to London"
            12. "Find me 2 tickets to Dubai in Business Class"
            13. "Round trip flights from Delhi to Maldives from 1st to 5th Feb"
            14. "Return ticket from Mumbai to Dubai departing 10th March returning 15th March"
            15. "Flights to Delhi under 5000"
            16. "Cheap flights to Mumbai"
            17. "Budget flight to London"
            18. "Show me flights to Dubai below 40000"
            19. "Find me 2 tickets to Maldives under 20000"
            20. "Business class to London under 100000"
        """,
        "schema": SearchFlightsInput.model_json_schema()
    }

    registry["create_itinerary"] = {
        "tool": create_itinerary_tool,
        "description": f"""
            1. Create a travel itinerary for a destination
            2. Plan a day-by-day trip schedule
            3. Suggest activities for leisure or business trips
            4. "Plan a 3-day trip to Maldives"
            5. "Make an itinerary for Bali"
            6. "Suggest things to do in Maldives"
            7. "Travel plan for a week in Maldives with 5000.0 budget"
        """,
        "schema": CreateItineraryInput.model_json_schema()
    }

    registry["book_flight"] = {
        "tool": book_flight_tool,
        "description": f"""
            1. Book a specific flight using flight ID
            2. Reserve flight tickets for passengers
            3. "Book flight AI-202"
            4. "Confirm this flight for me"
            5. "Proceed with flight booking"
        """,
        "schema": BookFlightInput.model_json_schema()
    }

    registry["book_hotel"] = {
        "tool": book_hotel_tool,
        "description": f"""
            1. Book a hotel room using hotel ID
            2. Reserve accommodation for checking dates
            3. "Book this hotel"
            4. "Reserve a room at the Marriott"
            5. "Confirm booking for Hotel XYZ"
        """,
        "schema": BookHotelInput.model_json_schema()
    }

    registry["search_packages"] = {
        "tool": search_packages_tool,
        "description": f"""
            1. Search for holiday/vacation packages
            2. Find honeymoon, family, or adventure trips
            3. Look for all-inclusive travel packages
            4. "Show me holiday packages for Maldives"
            5. "Honeymoon trips to Maldives"
            6. "Family vacation packages"
            7. "Give me 3 days 4 nights package to maldives"
            8. "Suggest a budget 5D/4N package to maldives"
        """,
        "schema": SearchPackagesInput.model_json_schema()
    }

    registry["book_package"] = {
        "tool": book_package_tool,
        "description": f"""
            1. Book a specific holiday package
            2. Confirm reservation for a tour package
            3. "Book this package"
            4. "Reserve the honeymoon package"
        """,
        "schema": BookPackageInput.model_json_schema()
    }

    registry["get_cancellation_policy"] = {
        "tool": get_cancellation_policy_tool,
        "description": f"""
            1. Get cancellation and refund rules
            2. Check if a booking is refundable
            3. "What is the cancellation policy?"
            4. "Can I cancel my flight?"
        """,
        "schema": GetCancellationPolicyInput.model_json_schema()
    }

    registry["check_booking_status"] = {
        "tool": check_booking_status_tool,
        "description": f"""
            1. Check if a booking is confirmed or pending
            2. Track PNR status
            3. "Is my booking confirmed?"
            4. "Check status of BKG-123"
        """,
        "schema": CheckBookingStatusInput.model_json_schema()
    }

    registry["cancel_booking"] = {
        "tool": cancel_booking_tool,
        "description": f"""
            1. Cancel an existing booking
            2. Request cancellation for flight/hotel
            3. "Cancel my booking"
            4. "I want to cancel flight AI-101"
        """,
        "schema": CancelBookingInput.model_json_schema()
    }

    registry["get_baggage_policy"] = {
        "tool": get_baggage_policy_tool,
        "description": f"""
            1. Check baggage allowance for airlines
            2. Find luggage limits
            3. "What is the baggage limit for Indigo?"
            4. "How many bags can I carry?"
        """,
        "schema": GetBaggagePolicyInput.model_json_schema()
    }

    registry["track_flight"] = {
        "tool": track_flight_tool,
        "description": f"""
            1. Track real-time flight status
            2. Check if flight is delayed
            3. "Is my flight on time?"
            4. "Track flight AA-100"
        """,
        "schema": TrackFlightInput.model_json_schema()
    }

    registry["view_bookings"] = {
        "tool": view_bookings_tool,
        "description": f"""
            1. View all confirmed bookings
            2. List flight, hotel, or package reservations
            3. "Show my bookings"
            4. "What have I booked so far?"
            5. "List my flight bookings"
            6. "Show me my hotel reservations"
        """,
        "schema": ViewBookingsInput.model_json_schema()
    }

    registry["book_trip"] = {
        "tool": book_trip_tool,
        "description": f"""
            1. Book any trip (flight, hotel, package)
            2. "Book flight"
            3. "Reserve hotel"
            4. "Buy package"
        """,
        "schema": BookTripInput.model_json_schema()
    }

    return registry

TOOL_REGISTRY = get_tool_registry()

