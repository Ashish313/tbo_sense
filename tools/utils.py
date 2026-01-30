import json
import os
import time
from typing import List, Dict, Any

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")

def load_data(filename: str) -> Any:
    """Load JSON data from the data directory."""
    path = os.path.join(DATA_DIR, filename)
    if not os.path.exists(path):
        return [] if filename.endswith("s.json") else {} # Simple heuristic
    with open(path, "r") as f:
        return json.load(f)

def save_data(filename: str, data: Any) -> None:
    """Save JSON data to the data directory."""
    path = os.path.join(DATA_DIR, filename)
    with open(path, "w") as f:
        json.dump(data, f, indent=2)

def create_response_json(
        text: str,
        status: bool = True,
        error: str = None,
        data: Any = None,
        search_type: str = None,
        table: bool = False
) -> str:
    """Create standardized JSON response."""
    response = {
        "text": text,
        "search_type": search_type,
        "end_prompt": True,
        "table": table,
        "data": data,
        "graph": False,
        "graph_type": [],
        "graph_title": "",
        "is_downloadable": False,
        "image": False,
        "video": False,
        "audio": False,
        "button": False,
        "prompt_text": "",
        "button_text": [],
        "source": "rag_search",
        "timestamp": int(time.time() * 1000),
        "status": status
    }

    if error:
        response["error"] = error

    return json.dumps(response, indent=2)

def handle_tool_error(ex: Exception, tool_name: str) -> str:
    return create_response_json(
        f"Error in {tool_name}: {str(ex)}",
        status=False,
        error=str(ex)
    )

def format_response(status: str, data: Any, message: str = "") -> str:
    """Legacy helper - forwarding to new structure."""
    is_success = (status == "success")
    return create_response_json(
        text=message,
        status=is_success,
        data=data
    )
