import json
import re
import uuid
from typing import Optional, Dict, Any, Tuple, List
from datetime import datetime, timedelta, timezone
import chromadb
from chromadb.utils import embedding_functions
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langchain_core.rate_limiters import InMemoryRateLimiter
from langchain_ollama import ChatOllama
from pydantic import ValidationError
from applications.etcd.init_etcd import global_config
from StateBase import StateBase
import torch._dynamo
import whisper
from flask_api_service.tool_setup import tools, TOOL_REGISTRY
torch._dynamo.config.suppress_errors = True

# audio pipe
whisper_model = None
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"
whisper_model = whisper.load_model("base", device=DEVICE)

# ============================================
# INITIALIZATION
# ============================================

# Rate limiter and model setup
rate_limiter = InMemoryRateLimiter(
    requests_per_second=10,
    check_every_n_seconds=0.2,
    max_bucket_size=50
)
# Audio setup
DEVICE = "cuda" if torch.cuda.is_available() else "cpu"

# Config
global_config.read_etcd_config(file_path="config")

# LLM
llm = ChatOllama(
    base_url="http://localhost:11434",
    model="gpt-oss:20b",
    temperature=0.0,
    repeat_penalty=10,
    extract_reasoning=True,
    num_predict=8000,
    rate_limiter=rate_limiter,
    stop=["<|call|>"]
)

decision_llm = ChatOllama(
    base_url="http://localhost:11434",
    model="gpt-oss:20b",
    temperature=0.0,
    extract_reasoning=True,
    format="json",          # helps Ollama return clean JSON
    num_predict=4096,
    stop=["\n\n", "```"]    # prevent extra text
)

# System prompt
system_prompt = """
Reasoning: high

You are **TBO Sense**, the TBO AI travel assistant.  
Only introduce yourself if the user greets you or asks who you are.  
Never mention AI models or companies.

### CORE RULES
1. **No assumptions**
   - Never invent values, IDs, parameters, or tools.
   - Always ask the user for missing information.
   - If unsure: say “I'm not sure. Please clarify.”

2. **Tool Usage**
   - Use ONLY the tools provided.
   - Show required + optional parameters clearly.
   - Collect all required parameters before running a tool.
   - Never run a tool without explicit user confirmation.

3. **Confirmation Flow**
   - Acknowledge request → collect missing details → show all parameters →  
     ask: **“Type 'yes' to proceed or 'no' to edit.”**  
   - Run tool only after user types **yes**.

### DOMAIN LIMIT
You can answer questions about:
1. **Travel bookings**: search and book hotels, flights, and holiday packages.
2. **Itineraries**: create and manage travel itineraries based on preferences.
3. **Trip management**: check booking status, cancel bookings, view cancellation policies, and track flights.

If the question is completely unrelated to travel (e.g., e-commerce, logistics, recipes, sports, etc.), answer exactly:  
**"I can help only with travel-related queries such as flights, hotels, holiday packages, and itineraries. Please ask something related to TBO travel services."**

If the question is about comparison between TBO and competitors (like MakeMyTrip, Expedia, etc.), answer exactly:  
**"I can't compare TBO with other travel companies. Please ask something related to TBO services."**

"""



class ChromaToolRetriever:
    """Handles vector indexing and retrieval of tool descriptions."""

    def __init__(self, tool_registry: Dict[str, Dict[str, Any]], collection_name: str = "tool_library"):
        self.client = chromadb.Client()
        self.embedding_function = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name="BAAI/bge-m3"  # "mixedbread-ai/mxbai-embed-large-v1"
        )
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            embedding_function=self.embedding_function
        )
        self.tool_registry = tool_registry
        self._index_tools()

    def _index_tools(self):
        descriptions: List[str] = [data["description"] for data in self.tool_registry.values()]
        ids: List[str] = list(self.tool_registry.keys())
        self.collection.add(documents=descriptions, ids=ids)
        print(f"Indexed {len(ids)} tools into ChromaDB.")

    def retrieve_tool_and_score(self, query: str, k: int = 1) -> Tuple[Optional[str], float, List[Tuple[str, float]]]:
        """
        Retrieves the top tool name, its similarity score, and the list of all retrieved
        tool-score pairs.

        Returns:
            (top_tool_name, top_similarity_score, all_results_list)
        """
        results = self.collection.query(
            query_texts=[query],
            n_results=k
        )

        all_results: List[Tuple[str, float]] = []

        # Check if we have any results for the query
        if results and results["ids"] and results["ids"][0] and results["distances"] and results["distances"][0]:

            # Extract the list of IDs and distances for the single query
            tool_ids = results["ids"][0]
            distances = results["distances"][0]

            # Process all retrieved results
            for tool_name, distance in zip(tool_ids, distances):
                # Simple heuristic to map L2 distance (lower is better, typically 0 to ~1.4)
                # to a 0-1 similarity score (higher is better).
                # The maximum value is used to ensure the score doesn't go below 0.0
                similarity_score = max(0.0, 1.0 - (distance / 1.5))
                all_results.append((tool_name, similarity_score))

            # The top result is the first element, as ChromaDB returns results sorted by distance
            top_tool_name = all_results[0][0]
            top_similarity_score = all_results[0][1]

            return (top_tool_name, top_similarity_score, all_results)

        # Return structure if no results are found
        return (None, 0.0, [])

def extract_user_message(messages: List) -> str:
    """Extract the last user message from conversation history"""
    for msg in reversed(messages):
        if isinstance(msg, HumanMessage):
            # Handle standard string content
            content = msg.content
            if isinstance(content, str):
                return content
            # Handle list format (e.g., from multimodal API)
            if isinstance(content, list):
                for item in content:
                    if isinstance(item, dict) and item.get('type') == 'text':
                        return item.get('text', '')
            # Fallback for unexpected content types
            return str(content)
    return ""

def truncate_history(messages, max_messages=10):
    """Keep fewer messages to reduce context confusion"""
    if len(messages) <= max_messages:
        return messages

    # Keep System messages at the start
    system_msgs = [m for m in messages if isinstance(m, SystemMessage)]
    non_system_msgs = [m for m in messages if not isinstance(m, SystemMessage)]

    recent_non_system = non_system_msgs[-max_messages + len(system_msgs):]

    return system_msgs + recent_non_system

def extract_clean_json_tool(text: str) -> Optional[Dict[str, Any]]:
    """
    Returns the first valid JSON object/array parsed into a Python dict/list,
    or None if nothing valid is found.
    """
    # Look for a curly brace or square bracket block
    match = re.search(r'(\{.*\}|\[.*\])', text, flags=re.DOTALL)
    if not match:
        return None

    json_str = match.group(1)
    try:
        # Use simple cleaning heuristic to strip surrounding text
        start_index = json_str.find('{')
        end_index = json_str.rfind('}')
        if end_index > start_index:
            clean_str = json_str[start_index:end_index + 1]
        else:
            clean_str = json_str

        # print(f"\n input text: {text}\n") # Debugging print removed
        return json.loads(clean_str)
    except json.JSONDecodeError:
        return None

# INTENT CHANGE THRESHOLD: 0.4 (fallback, but now LLM decides primarily)
INTENT_CHANGE_THRESHOLD = 0.65  # Still keep as fallback if LLM fails to parse
system_prompt_msg = SystemMessage(content=system_prompt)
tool_retriever = ChromaToolRetriever(TOOL_REGISTRY)

def chatbot(state: StateBase) -> StateBase:
    """Enhanced chatbot – RAG → LLM decides intent (follow-up vs new) safely."""
    try:
        # 1. Truncate history
        state["messages"] = truncate_history(state.get("messages", []), max_messages=10)

        # 2. Extract latest user message
        user_message = extract_user_message(state["messages"])

        print(f"\n{'=' * 60}")
        print(f"USER MESSAGE: {user_message[:100]}...")
        print(f"{'=' * 60}")

        # 3. Current intent from previous turn
        current_intent_tool = state.get("current_intent_tool")
        print(f"Current Stored Intent: {current_intent_tool}")

        # 4. RAG – get top-3 candidate tools
        _, _, tools_list = tool_retriever.retrieve_tool_and_score(user_message, k=3)
        candidate_tools = []
        for tool_tuple in tools_list:
            tool_key, score = tool_tuple
            print(f"Retrieved candidate: {tool_key} (Score: {score:.2f})")
            if tool_key in TOOL_REGISTRY:
                entry = TOOL_REGISTRY[tool_key]
                tool_obj = entry.get("tool")
                schema = entry.get("schema")
                if tool_obj and schema:
                    candidate_tools.append({
                        "name": tool_key,
                        "description": entry["description"],
                        "schema": schema,
                        "score": round(score, 3)
                    })

        history = " | ".join(
            str(m.content).replace("\n", " ").strip()
            for m in state.get("messages", [])
            if str(m.content).strip()
        )

        full_history = f"Full conversation history: {history}"

        # 5. **SAFE INTENT DECISION PROMPT** – using f-string (no KeyError ever)
        intent_decision_prompt = f"""
        You are a strict JSON-only Intent Classification Agent.

        Your job:
        - Decide if the user message is a "followup" or "new" intent.
        - Select exactly ONE tool based on the highest semantic score.
        - You must ALWAYS return valid JSON. Never return blank output.

        -----------------------
        CLASSIFICATION RULES
        -----------------------

        1. FOLLOWUP  
           - User is providing details, parameters, confirmations, or continuing the active intent.

        2. NEW  
           - User asks anything unrelated to the current tool/task.
           - OR the highest-scoring candidate tool clearly matches the request better than the current intent.

        3. TOOL SELECTION  
           - Pick the tool with the **highest score**, not the first.
           - If multiple tools have similar scores (difference < 0.03):  
                → Prefer the tool that best semantically matches the user message.
           - If NO tool score ≥ 0.60:  
                → selected_tool = "none".

        4. MULTIPLE TASKS IN ONE MESSAGE  
           - Identify if the user asked for more than one unrelated task.
           - If yes:
                → decision = "new"
                → selected_tool = "none"
                → reason = "User attempted multiple tasks; only one can be processed."

        5. OUTPUT FORMAT  
           You MUST output ONLY this JSON format:

        {{
          "decision": "followup" | "new",
          "selected_tool": "<tool_name or none>",
          "reason": "<short justification>"
        }}

        Never return empty output. Never include explanations outside JSON.

        -----------------------
        DATA
        -----------------------

        Current intent: {current_intent_tool or "None"}

        User message:
        {user_message}

        Conversation history (compressed):
        {full_history}

        Candidate tools (with scores):
        {json.dumps(candidate_tools, indent=2) if candidate_tools else "[]"}
        """

        # 6. Call a lightweight LLM for decision
        decision_response = decision_llm.invoke(
            [SystemMessage(content=intent_decision_prompt)]
        )
        decision_text = getattr(decision_response, "content", "").strip()

        print("##########################")
        print(decision_text)
        print("##########################")

        # 7. Robust JSON extraction
        parsed_decision = extract_clean_json_tool(decision_text)

        # 8. Fallback if LLM fails to give JSON
        if not parsed_decision or not isinstance(parsed_decision, dict):
            print("Warning: LLM decision parsing failed. Using score-threshold fallback.")
            top_tool_name = tools_list[0][0] if tools_list else None
            top_score = tools_list[0][1] if tools_list else 0.0
            print(f"top_score: {top_score}")
            if top_score >= INTENT_CHANGE_THRESHOLD and top_tool_name:
                current_intent_tool = top_tool_name
                print(f"Fallback: INTENT SET to {current_intent_tool}")
            elif not current_intent_tool and top_tool_name:
                current_intent_tool = top_tool_name
        else:
            decision = parsed_decision.get("decision", "").lower()
            selected = parsed_decision.get("selected_tool")
            reason = parsed_decision.get("reason", "No reason")

            print(f"LLM Decision: {decision} | Tool: {selected} | Reason: {reason}")

            if decision == "followup":
                # keep current tool (even if None → will stay conversational)
                pass
            elif decision == "new":
                current_intent_tool = selected if selected != "none" else None
                print(f"INTENT SWITCHED → {current_intent_tool}")

        # 9. Update state
        state["current_intent_tool"] = current_intent_tool

        # 10. Bind only the decided tool (or top-2 candidates if undecided)
        tools_to_bind = []
        if current_intent_tool and current_intent_tool in TOOL_REGISTRY:
            tool_obj = TOOL_REGISTRY[current_intent_tool].get("tool")
            if tool_obj:
                tools_to_bind.append(tool_obj)
        else:
            # fallback: bind top-2 candidates
            for cand in candidate_tools[:2]:
                obj = TOOL_REGISTRY.get(cand["name"], {}).get("tool")
                if obj:
                    tools_to_bind.append(obj)

        print(f"Binding tools: {[t.name for t in tools_to_bind]}")

        # 11. Main LLM messages
        # 11. Build structured messages for the agent

        # Add current time in IST
        ist_offset = timedelta(hours=5, minutes=30)
        current_time_ist = datetime.now(timezone(ist_offset)).strftime("%Y-%m-%d %H:%M:%S IST")
        time_context_msg = SystemMessage(content=f"Current Date and Time (IST): {current_time_ist}")

        messages_for_llm = [
            system_prompt_msg,
            time_context_msg
        ]




        # Add intent-specific schema if available
        if current_intent_tool:
            schema = TOOL_REGISTRY.get(current_intent_tool, {}).get("schema", {})
            messages_for_llm.append(
                SystemMessage(
                    content=(
                        f"Current intent: '{current_intent_tool}'. "
                        f"Extract parameters ONLY for this tool.\n\n"
                        f"Schema:\n{json.dumps(schema, indent=2)}"
                    )
                )
            )
        else:
            messages_for_llm.append(
                SystemMessage(content="No matched tool. Respond as a helpful assistant.")
            )

        # IMPORTANT: append ONLY Message objects (not strings)
        messages_for_llm.extend(state["messages"])

        # 12. Main LLM call
        main_llm = ChatOllama(
            base_url="http://localhost:11434",
            model="gpt-oss:20b",
            temperature=0.0,
            repeat_penalty=10,
            num_predict=4096,
            rate_limiter=rate_limiter,
            extract_reasoning=True,
            stop=["<|call|>"]
        )

        llm_with_tools = main_llm.bind_tools(tools_to_bind or tools)  # fallback to all tools if empty
        response = llm_with_tools.invoke(messages_for_llm)

        # 13. Native tool calls (LangChain format)
        if getattr(response, "tool_calls", None):
            print("Native tool_calls detected.")
            return {
                "messages": state["messages"] + [response],
                "current_intent_tool": current_intent_tool
            }

        # 14. Fallback JSON extraction for Ollama raw output
        parsed_json = extract_clean_json_tool(getattr(response, "content", ""))

        # Handle list output (e.g. if LLM returns [{}])
        if isinstance(parsed_json, list):
            if len(parsed_json) > 0 and isinstance(parsed_json[0], dict):
                parsed_json = parsed_json[0]
            else:
                parsed_json = None

        if parsed_json and current_intent_tool:
            print(f"Extracted JSON for {current_intent_tool}")
            return {
                "messages": state["messages"] + [AIMessage(
                    content=response.content,
                    tool_calls=[{
                        "name": current_intent_tool,
                        "args": parsed_json.get("parameters", parsed_json.get("arguments", {})),
                        "id": str(uuid.uuid4())
                    }]
                )],
                "current_intent_tool": current_intent_tool
            }

        # 15. Plain text response
        content = getattr(response, "content", "Sorry, I couldn't generate a response.")
        return {
            "messages": state["messages"] + [AIMessage(content=content)],
            "current_intent_tool": current_intent_tool
        }

    except Exception as e:
        print(f"ERROR in chatbot: {e}")
        import traceback
        traceback.print_exc()
        return {
            "messages": state.get("messages", []) + [AIMessage(content="Something went wrong. Please try again.")],
            "current_intent_tool": None
        }

# ============================================
# KEEP YOUR EXISTING FUNCTIONS
# ============================================

def is_valid_json(text: str) -> Tuple[bool, bool]:
    try:
        data = json.loads(text)
        end_prompt = data.get("end_prompt", False)
        special_keys = ["table", "image", "video", "audio", "graph", "text"]
        if any(key in data for key in special_keys):
            return False, end_prompt
        return True, end_prompt
    except Exception as e:
        return True, True


# Assuming ValidationError is imported from where it's defined (e.g., Pydantic)
# Assuming AIMessage, SystemMessage, HumanMessage, and StateBase are imported

def handle_response_exception(state, response, current_intent_tool):
    """
    Handles exceptions during response processing, maintaining the
    current_intent_tool in the returned state.
    """
    try:
        # Successful flow: Just add the new response message to the history
        return {"messages": state["messages"] + [response], "current_intent_tool": current_intent_tool}

    # Catch specific validation errors (e.g., from Pydantic)
    except ValidationError as ve:
        error_details = []
        for e in ve.errors():
            loc = " -> ".join(str(p) for p in e["loc"])
            msg = e["msg"]
            val = e.get("input", "")
            error_details.append(f"Field `{loc}`: {msg} (value: `{val}`)")
        user_friendly_error = "⚠️ Input validation failed:\n" + "\n".join(error_details)

        # Return an AIMessage with the error and preserve the tool state
        return {
            "messages": state["messages"] + [AIMessage(content=user_friendly_error)],
            "current_intent_tool": current_intent_tool
        }

    # Catch any other unexpected exception
    except Exception as e:
        # Note: You should ideally log 'e' here for debugging
        print(f"❌ Unexpected Error in Handler: {e}")

        # Return a generic error message and preserve the tool state
        return {
            "messages": state["messages"] + [
                AIMessage(content="❌ An unexpected error occurred. Please check your inputs and try again.")],
            "current_intent_tool": current_intent_tool
        }


def chatbot_response(state: StateBase):
    """
    The main response function, primarily intended to process and format tool outputs.
    """
    try:
        # 1. Retrieve the current tool state
        current_intent_tool = state.get("current_intent_tool")

        system_message = [SystemMessage(
            content=(
                """
                You are **TBO Co-Pilot**. Your ONLY job is to display tool responses clearly.

                📌 RULES
                1. Never generate your own answer. Output ONLY what the tool returns.  
                2. You may reformat for readability — but never change values.  
                3. If the tool returns nothing/null → say: **"The tool did not return any data."**
                """
            )
        )]


        # Ensure messages list is not empty before accessing the last element
        if not state["messages"]:
            return {"messages": [AIMessage(content="No user message provided.")],
                    "current_intent_tool": current_intent_tool}

        # 2. Check if the last message content requires an LLM response (i.e., is a tool result)
        # Assuming is_valid_json extracts/checks for the tool output structure.

        is_ai_response, end_prompt = is_valid_json(state["messages"][-1].content)

        if is_ai_response:
             # 3. Invoke LLM to process the tool output
            last_message_content = state["messages"][-1].content

            # The LLM's role is to reformat the tool output (last_message_content)
            response = llm.invoke(system_message + [HumanMessage(content=last_message_content)])

            # 4. Use the corrected handler with all required arguments
            return handle_response_exception(state, response, current_intent_tool)

        # 5. Passthrough (if it wasn't a tool result to be processed)
        # This state typically shouldn't be reached if the flow is: User -> Tool -> LLM
        # But if it is, we return the state as is, without adding a new message.
        return {
            "messages": state["messages"],
            "current_intent_tool": current_intent_tool
        }

    except Exception as e:
        print(f"❌ ERROR in chatbot_response: {e}")
        # Return an error message while preserving the full history and tool state
        return {
            "messages": state["messages"] + [AIMessage(content="An unhandled error occurred in the response phase.")],
            "current_intent_tool": None
        }
