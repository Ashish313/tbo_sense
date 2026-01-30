from typing import Annotated, List, Tuple, TypedDict, Any, Optional
from langgraph.graph import add_messages
from langgraph.store.memory import InMemoryStore


# main StateBase Class
class StateBase(TypedDict):
    context: dict[str, Any]
    messages: Annotated[list, add_messages]
    memory_context: str
    entities_pred: List[Tuple[str, int, int, str]]
    serviceability: dict
    follow_up: bool
    remaining_steps: int
    user_id: Optional[str]
    current_intent_tool: str
    execution_order: str
