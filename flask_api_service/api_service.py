import json
import logging
import os
import tempfile
import uuid
import time
from pathlib import Path
from flask import request, jsonify, Flask, g, send_file, render_template
from flask_cors import CORS
from langchain_core.messages import HumanMessage
from langgraph.checkpoint.memory import MemorySaver, InMemorySaver
from langgraph.constants import START, END
from langgraph.graph import StateGraph
from langgraph.prebuilt.tool_node import ToolNode, tools_condition
from applications.scylla.init_scylla import ScyllaConnection
from StateBase import StateBase
from api_call import get_api
from applications.etcd.init_etcd import global_config
from applications.milvus.connect_milvus import MilvusDB



from flask_api_service.session_middleware import session_middleware
from flask_api_service.tool_setup import tools
from db_queries.queries import insert_user_chat_mapping, get_user_chat_mapping_by_id, update_chat_name_by_id, \
    get_user_all_chats, upsert_chat_conversation, get_user_chat_conversation, delete_chat_by_id
from applications.logger.mod import generate_app_log, LogLevels

from flask_api_service.api_helper import whisper_model, chatbot, chatbot_response

from flask_api_service.api_helper import system_prompt

logging.basicConfig(level=logging.WARNING)

app = Flask(__name__)

UPLOAD_DIR = Path("./uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

CORS(app)

graph_builder = StateGraph(StateBase)
graph_builder.add_node("chatbot", chatbot)

tool_node = ToolNode(tools=tools)
graph_builder.add_node("tools", tool_node)

graph_builder.add_node("chatbot_response", chatbot_response)

graph_builder.add_edge(START, "chatbot")

graph_builder.add_conditional_edges(
    "chatbot",
    tools_condition,
)

graph_builder.add_edge("tools", "chatbot_response")
graph_builder.add_edge("chatbot_response", END)

checkpointer = InMemorySaver()
agent = graph_builder.compile(checkpointer=checkpointer, debug=False)

# flask api service

@app.route('/new_chat', methods=['POST'])
@session_middleware
def new_chat():
    api_name = "new_chat"
    start_time = int(time.time() * 1000)
    user_id = g.user_id
    
    # Log Request
    generate_app_log(
        api_name=api_name,
        log_level=LogLevels.Info,
        message=f"Request: New Chat Init",
        start_time=start_time,
        reference_id=user_id,
        user_id=user_id
    )

    try:
        chat_id = str(uuid.uuid4())
        created_date = int(time.time() * 1000)
        lut = int(time.time() * 1000)

        chat_data = {
            "chat_id": chat_id,
            "user_id": user_id,
            "chat_name": "",
            "created_date": created_date,
            "is_deleted": False,
            "lut": lut,
            "chat_initiated": False
        }

        insert_status = insert_user_chat_mapping(chat_data)

        if insert_status:
            response_data = {
                "status": True,
                "chat_id": chat_data["chat_id"]
            }
            # Log Response
            generate_app_log(
                api_name=api_name,
                log_level=LogLevels.Info,
                message=f"Response: {json.dumps(response_data, default=str)}",
                start_time=start_time,
                reference_id=user_id,
                user_id=user_id
            )
            return jsonify(response_data), 200
        else:
            return jsonify({
                "status": False,
                "chat_id": None
            }), 400


    except Exception as e:
        print("Error:", e)
        raw_response = "Sorry, could not answer your question, please try again later.."
        return jsonify({"status": False, "msg": raw_response}), 400

# @app.route('/get_user_profile', methods=['GET'])
# @session_middleware
# def get_user_profile():

#     try:
#         # TBO Hive config removed, returning mock/empty profile
#         # (response, status) = get_api({}, f"{global_config.config.tbohive_api_config.base_url}user_profile",
#         #     g.bearer_token, "", api_name="get_user_profile")
        
#         # Mock response
#         return jsonify({
#             "status": True,
#             "msg": "Profile feature disabled",
#             "data": {}
#         }), 200
#         else:
#             return jsonify({
#                 "status": False,
#                 "msg": response.get("msg", ""),
#                 "data": None
#             }), 400


#     except Exception as e:
#         print("Error:", e)
#         raw_response = "Sorry, could not answer your question, please try again later.."
#         return jsonify({"status": False, "msg": raw_response}), 400

@app.route('/')
def home():
    return send_file('static/index.html')

@app.route('/view_results')
def view_results():
    return render_template('results.html')

@app.route('/api/data/<data_type>.json')
def get_data_json(data_type):
    # Safe mapping to file paths
    # data_type should be hotels, packages, or flights
    if data_type not in ['hotels', 'packages', 'flights']:
        return jsonify({"error": "Invalid data type"}), 400
    
    file_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", f"{data_type}.json")
    if os.path.exists(file_path):
        return send_file(file_path)
    else:
        return jsonify({"error": "Data not found"}), 404

@app.route('/handle_user_query', methods=['POST'])
@session_middleware
def handle_user_query():
    function_name = "handle_user_query"
    api_name = "handle_user_query"
    data = request.json
    query = data.get('query')
    chat_id = data.get('chat_id')
    user_id = g.user_id
    
    start_time = int(time.time() * 1000)
    # Log Request
    generate_app_log(
        api_name=api_name,
        log_level=LogLevels.Info,
        message=f"Request: {json.dumps(data, default=str)}",
        start_time=start_time,
        reference_id=user_id,
        user_id=user_id
    )

    current_time = int(time.time() * 1000)
    data = None
    is_downloadable = False
    ai_response_text = None
    is_end_prompt = False
    is_table_response = False
    is_plot_graph = False
    graph_type = []
    graph_title = ""
    file_name = ""
    file_url = ""
    image = False
    video = False
    audio = False
    button = False
    button_text = []

    try:

        chat_data = get_user_chat_mapping_by_id(chat_id)
        
        # Mock for UI Testing
        if chat_data is None and chat_id == "bc9f871c-6f26-44cc-853c-8ac98209e37a":
             print(f"[{function_name}] Using MOCK chat data for test ID: {chat_id}")
             chat_data = {
                "chat_id": chat_id,
                "user_id": user_id,
                "chat_name": "UI Test Chat",
                "chat_initiated": True
             }

        if chat_data is None:
            return jsonify({
                "status": False,
                "msg": "Chat ID is required",
                "data": data,
                "end_prompt": False,
                "table": False,
                "is_downloadable": False,
                "graph": False,
                "graph_type": graph_type,
                "graph_title": graph_title,
                "timestamp": current_time,
                "image": image,
                "video": video,
                "audio": audio
            }), 400

        if not chat_data.get("chat_initiated", False):
            words = query.strip().split()
            first_four_words = words[:4]

            if not first_four_words:
                return jsonify({"status": False, "msg": "Invalid query", "data": data, "end_prompt": False, "table": False, "is_downloadable": False, "graph": False, "graph_type": graph_type, "graph_title": graph_title, "timestamp": current_time}), 400

            chat_name = " ".join(first_four_words)
            chat_name = chat_name[:100]
            chat_name_updated: bool = update_chat_name_by_id(user_id, chat_id, chat_name)

            if not chat_name_updated:
                print(f"[{function_name}] Update chat name failed: {chat_name}")


        config = {
            "configurable": {
                "thread_id": chat_id,
                "user_id": user_id
            }
        }

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": [{"type": "text", "text": query}]},
        ]

        response = agent.invoke({"messages": messages, "user_id": str(user_id)}, config=config)

        raw_response = response["messages"][-1]

        raw_content = raw_response.content

        print(raw_content)

        if isinstance(raw_content, str):
            try:
                parsed_json = json.loads(raw_content)
                ai_response_text = parsed_json.get("text")
                is_end_prompt = parsed_json.get("end_prompt", False)
                is_table_response = parsed_json.get("table", False)
                is_plot_graph = parsed_json.get("graph", False)
                graph_type = parsed_json.get("graph_type", [])
                graph_title = parsed_json.get("graph_title", "")
                data = parsed_json.get("data")
                is_downloadable = parsed_json.get("is_downloadable", False)
                file_name = parsed_json.get("file_name", "")
                file_url = parsed_json.get("file_url", "")
                image = parsed_json.get("image", False)
                video = parsed_json.get("video", False)
                audio = parsed_json.get("audio", False)
                button = parsed_json.get("button", False)
                button_text = parsed_json.get("button_text", [])
                search_type = parsed_json.get("search_type", "")

            except json.JSONDecodeError as ev:
                print(ev)
                ai_response_text = raw_content
                search_type = ""
        else:
            ai_response_text = raw_content
            search_type = ""

        if ai_response_text is None:
            print("ai_response_text is None")
            return (jsonify({
                "status": False,
                "text": "Sorry, could not answer your question, please try again later..",
                "data": data,
                "end_prompt": False,
                "table": False,
                "is_downloadable": False,
                "graph": False,
                "graph_type": graph_type,
                "graph_title": graph_title,
                "timestamp": current_time,
                "image": image,
                "video": video,
                "audio": audio
            }), 400)

        # prepare mongo conversation data
        conversation_data = {
            "user_query": query,
            "ai_response": ai_response_text,
            "data": data,
            "timestamp": current_time,
            "response_type": "text",
            "end_prompt": is_end_prompt,
            "table": is_table_response,
            "graph": is_plot_graph,
            "graph_type": graph_type,
            "graph_title": graph_title,
            "is_downloadable": is_downloadable,
            "image": image,
            "video": video,
            "audio": audio,
            "button": button,
            "button_text": button_text
        }

        conversation_updated: bool = upsert_chat_conversation(user_id, chat_id, conversation_data)
        if not conversation_updated:
            print(f"[{function_name}] Failed to update conversation: {chat_id}")


        # if is_downloadable is True and file_name != "" and file_url != "":
        #     file_data = {
        #         "file_name": file_name,
        #         "file_url": file_url,
        #         "created_date": int(time.time() * 1000)
        #     }
        #     file_saved: bool = upsert_chat_download_files(seller_id, file_data)
        #
        #     if not file_saved:
        #         print(f"[{function_name}] Failed to update downloaded files in db: {chat_id}")


        response_data = {
            "status": True,
            "text": ai_response_text,
            "data": data,
            "end_prompt": is_end_prompt,
            "table": is_table_response,
            "is_downloadable": is_downloadable,
            "graph": is_plot_graph,
            "graph_type": graph_type,
            "graph_title": graph_title,
            "timestamp": current_time,
            "image": image,
            "video": video,
            "audio": audio,
            "button": button,
            "button_text": button_text,
            "search_type": search_type
        }
        
        # Log Response
        generate_app_log(
            api_name=api_name,
            log_level=LogLevels.Info,
            message=f"Response: {json.dumps(response_data, default=str)}",
            start_time=start_time,
            reference_id=user_id,
            user_id=user_id
        )

        return jsonify(response_data), 200

    except Exception as e:
        print(e)
        raw_response = "Sorry, could not answer your question, please try again later.."
        return jsonify({
            "status": False,
            "text": raw_response,
            "data": data,
            "end_prompt": False,
            "table": False,
            "is_downloadable": False,
            "graph": False,
            "graph_type": graph_type,
            "graph_title": graph_title,
            "timestamp": current_time,
            "image": image,
            "video": video,
            "audio": audio
        }), 400



@app.route('/get_chat_conversation', methods=['GET'])
@session_middleware
def get_chat_conversation():
    chat_id = request.args.get('chat_id')
    user_id = g.user_id

    if not chat_id:
        return jsonify({"status": False, "msg": "Chat ID is required"}), 400


    conversation_data = get_user_chat_conversation(user_id, chat_id)

    if not conversation_data:
        return jsonify({"status": False, "chat_data": None}), 200

    return {"status": True, "chat_data": conversation_data}, 200




@app.route('/get_chat_history', methods=['GET'])
@session_middleware
def get_chat_history():
    user_id = g.user_id
    try:
        chat_list = get_user_all_chats(user_id)

        if chat_list:
            return jsonify({"status": True, "chat_list": chat_list}), 200
        else:
            return jsonify({"status": True, "chat_list": []}), 400

    except Exception as e:
        print("Error:", e)
        raw_response = "Sorry, could not answer your question, please try again later.."
        return jsonify({"status": False, "msg": raw_response}), 400



@app.route('/delete_chat', methods=['POST'])
@session_middleware
def delete_chat():
    function_name = "delete_chat"
    data = request.json
    chat_id = data.get('chat_id')
    user_id = g.user_id

    try:
        chat_deleted = delete_chat_by_id(user_id, chat_id)

        if chat_deleted:
            return jsonify({"status": True, "msg": "Chat deleted successfully"}), 200
        else:
            return jsonify({"status": False, "msg": ""}), 400


    except Exception as e:
        print(f"{function_name} Error:", e)
        raw_response = "Sorry, could not answer your question, please try again later.."
        return jsonify({"status": False, "msg": raw_response}), 400




@app.route("/transcribe", methods=["POST"])
def transcribe():
    if "audio" not in request.files:
        return jsonify({"error": "No audio file provided"}), 400

    audio_file = request.files["audio"]

    # Save to a temporary file
    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
        audio_file.save(tmp.name)
        tmp_path = tmp.name

    try:
        result = whisper_model.transcribe(tmp_path, language="en")  # force English
        return jsonify({"text": result["text"].strip()})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        os.remove(tmp_path)


@app.route("/health", methods=["GET"])
def health():
    return "OK", 200


if __name__ == '__main__':

    import argparse
    parser = argparse.ArgumentParser(description='AI Assistant API Service')
    parser.add_argument('--env', type=str, default='DEV', help='Environment (DEV, SIT, UAT, PROD)')
    args = parser.parse_args()

    # Set environment in global config
    global_config.current_env = args.env
    print(f"Current Environment: {global_config.current_env}")

    # Initialize database connections
    ScyllaConnection.init_connection()
    MilvusDB.connect()


    # Start Flask app
    host = global_config.config.flask_api_service.host
    port = global_config.config.flask_api_service.port
    debug = global_config.config.flask_api_service.debug

    print(f"Starting Flask app on {host}:{port}")
    app.run(host=host, debug=debug, port=port)
