from typing import Optional, Dict, Any
from pydantic import BaseModel, Field, ValidationError
from tools.utils import load_data, create_response_json, handle_tool_error

class SearchPackagesInput(BaseModel):
    destination: str = Field(default="", description="Optional destination filter. Leave empty if not specified.")
    duration: str = Field(default="", description="Optional duration string (e.g. '5D/4N'). Leave empty if not specified.")
    budget: float = Field(default=0.0, description="Optional max budget. Set to 0 if not specified.")
    package_type: str = Field(default="", description="Optional type (e.g. 'Honeymoon', 'Family'). Leave empty if not specified.")

def search_packages(*args, **kwargs) -> str:
    """
    Search for travel packages.
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
            validated = SearchPackagesInput(**merged)
        except ValidationError as e:
            return create_response_json(f"Invalid payload: {e}", status=False)

        destination = validated.destination
        budget = validated.budget
        package_type = validated.package_type

        all_pkgs = load_data("packages.json")
        results = all_pkgs
        
        if destination:
            results = [p for p in results if destination.lower() in p["destination"].lower()]
            
        if package_type:
            results = [p for p in results if package_type.lower() == p["type"].lower()]
            
        # Treat 0.0 as "no budget limit"
        if budget > 0:
            results = [p for p in results if p["price"] <= budget]
            
        # Limit to top 10
        if len(results) > 10:
             results = results[:10]
            
        if not results:
            return create_response_json(
                "No packages found matching criteria.",
                status=True,
                data=[]
            )
            
        return create_response_json(
            f"Found {len(results)} packages. [View detailed results](http://localhost:3000/view_results?type=packages&destination={destination})",
            status=True,
            data=results,
            search_type="PACKAGE"
        )

    except Exception as ex:
        return handle_tool_error(ex, "search_packages")
