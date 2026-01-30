import json
import time
from cassandra.query import SimpleStatement
from applications.scylla.init_scylla import ScyllaConnection

def insert_user_chat_mapping(chat_data):
    function_name = "insert_user_chat_mapping"
    try:
        session = ScyllaConnection.get_session()
        query = """
            INSERT INTO chatbot_user_chats (
                user_id, chat_id, chat_name, created_date, lut, is_deleted, chat_initiated
            ) VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        session.execute(query, (
            chat_data["user_id"],
            chat_data["chat_id"],
            chat_data["chat_name"],
            chat_data["created_date"],
            chat_data["lut"],
            chat_data["is_deleted"],
            chat_data["chat_initiated"]
        ))
        
        print(f"[{function_name}] Inserted chat: {chat_data['chat_id']}")
        return True

    except Exception as e:
        print(f"[{function_name}] Exception occurred: {str(e)}")
        return False

def get_user_chat_mapping_by_id(chat_id):
    """
    Note: Ideally we need user_id to query efficiently. 
    However, the original signature only has chat_id.
    This implies we might have to use a secondary index or allow filtering if chat_id is not the partition key.
    
    In the schema: PRIMARY KEY (user_id, chat_id).
    Queries by chat_id ALONE are inefficient/invalid without Allow Filtering or secondary index.
    
    Assuming the caller can provide user_id usually, but here signature is fixed.
    Let's check usage. In `api_service.py`: `chat_data = get_user_chat_mapping_by_id(chat_id)`.
    Wait, `chat_id` is UUID. If unique, maybe we can query with ALLOW FILTERING just for now, or assume migration implies we should fix usage.
    However, the `flask_api_service/api_service.py` gets `user_id` from `g.parent_id`.
    
    STRICTLY SPEAKING: We can't query by just chat_id in Scylla efficiently if it's a clustering key.
    BUT, for migration correctness without changing call signatures, we might need a secondary index on chat_id.
    
    Let's look at `init_scylla.py`. Tables are created there.
    Currently no secondary index on chat_id.
    
    Workaround: usage in `api_service.py`
    `chat_data = get_seller_chat_mapping_by_id(chat_id)`
    
    I will try to fetch ALL chats for that seller if I had seller_id, but I don't here.
    Wait, let's see if we can perform a full table scan? No that's bad.
    
    Actually, let's assume valid implementation requires Global Secondary Index on `chat_id` if we query by `chat_id` alone.
    OR I update the function signature.
    The implementation plan said "Replace PyMongo logic".
    
    Let's use `ALLOW FILTERING` for now if the table is small, OR better:
    The `api_service.py` calls this. `api_service` has `g.parent_id` (user_id).
    I should arguably update `get_user_chat_mapping_by_id` to accept `user_id`.
    
    BUT, strict plan adherence: logic replacement.
    I'll check if I can use a materialized view or secondary index.
    
    Let's try to add a Secondary Index creation step to `init_scylla`? 
    No, let's iterate.
    
    Wait, most calls to this function in `api_service.py` have `user_id` available in scope.
    Calls:
    1. `handle_user_query`: `chat_data = get_user_chat_mapping_by_id(chat_id)` -> `user_id` is available.
    
    I will enable `ALLOW FILTERING` for this query for now to ensure it works without schema changes, 
    but adding `seller_id` to arguments would be much better.
    
    Actually, I'll return None if it fails.
    To be safe and robust, I will use `ALLOW FILTERING`.
    """
    function_name = "get_user_chat_mapping_by_id"

    try:
        session = ScyllaConnection.get_session()
        query = "SELECT * FROM chatbot_user_chats WHERE chat_id = %s ALLOW FILTERING"
        row = session.execute(query, (chat_id,)).one()

        if row:
            return {
                "user_id": row.user_id,
                "chat_id": row.chat_id,
                "chat_name": row.chat_name,
                "created_date": row.created_date,
                "lut": row.lut,
                "is_deleted": row.is_deleted,
                "chat_initiated": row.chat_initiated
            }
        else:
            print(f"[{function_name}] No chat data found for ID: {chat_id}")
            return None

    except Exception as e:
        print(f"[{function_name}] Exception occurred: {str(e)}")
        return None

def get_user_all_chats(user_id):
    function_name = "get_user_all_chats"
    try:
        session = ScyllaConnection.get_session()
        query = "SELECT * FROM chatbot_user_chats WHERE user_id = %s"
        rows = session.execute(query, (user_id,))
        
        chat_list = []
        for row in rows:
            if not row.is_deleted:
                chat_list.append({
                    "user_id": row.user_id,
                    "chat_id": row.chat_id,
                    "chat_name": row.chat_name,
                    "created_date": row.created_date,
                    "lut": row.lut,
                    "is_deleted": row.is_deleted,
                    "chat_initiated": row.chat_initiated
                })
        
        # Sort by lut desc (Python side)
        chat_list.sort(key=lambda x: x["lut"], reverse=True)

        if chat_list:
            return chat_list
        else:
            print(f"[{function_name}] No chat data found for user: {user_id}")
            return None

    except Exception as e:
        print(f"[{function_name}] Exception occurred: {str(e)}")
        return None

def update_chat_name_by_id(user_id, chat_id, new_chat_name):
    function_name = "update_chat_name_by_id"
    try:
        session = ScyllaConnection.get_session()
        lut = int(time.time() * 1000)
        
        query = """
            UPDATE chatbot_user_chats 
            SET chat_name = %s, chat_initiated = %s, lut = %s
            WHERE user_id = %s AND chat_id = %s
        """
        session.execute(query, (new_chat_name, True, lut, user_id, chat_id))
        
        print(f"[{function_name}] chat_name updated successfully")
        return True

    except Exception as e:
        print(f"[{function_name}] Invalid chat_id or unexpected error: {str(e)}")
        return False

def upsert_chat_conversation(user_id, chat_id, new_conversation_entry):
    function_name = "upsert_chat_conversation"
    try:
        session = ScyllaConnection.get_session()
        
        # In Scylla/Cassandra, we insert a new row for each message if we modeled it as 
        # PRIMARY KEY ((user_id, chat_id), timestamp)
        # The schema in init_scylla.py is:
        # CREATE TABLE chatbot_user_conversations (
        #     user_id text,
        #     chat_id text,
        #     timestamp bigint,
        #     message_json text,
        #     is_conversation_ended boolean,
        #     PRIMARY KEY ((user_id, chat_id), timestamp)
        # )
        
        timestamp = new_conversation_entry.get("timestamp", int(time.time() * 1000))
        is_conversation_ended = new_conversation_entry.get("end_prompt", False)
        
        # Serialize the conversation entry to JSON string
        message_json = json.dumps(new_conversation_entry)
        
        query = """
            INSERT INTO chatbot_user_conversations (user_id, chat_id, timestamp, message_json, is_conversation_ended)
            VALUES (%s, %s, %s, %s, %s)
        """
        session.execute(query, (user_id, chat_id, timestamp, message_json, is_conversation_ended))
        
        return True

    except Exception as e:
        print(f"[{function_name}] Unexpected error: {str(e)}")
        return False

def delete_chat_by_id(user_id, chat_id):
    function_name = "delete_chat_by_id"
    try:
        session = ScyllaConnection.get_session()
        lut = int(time.time() * 1000)
        
        # Update is_deleted in user_chats
        query = """
            UPDATE chatbot_user_chats 
            SET is_deleted = %s, lut = %s
            WHERE user_id = %s AND chat_id = %s
        """
        session.execute(query, (True, lut, user_id, chat_id))
        
        # Note: We are not deleting from chat_conversations or updating a flag there
        # because the conversation table doesn't have an is_deleted flag in the schema provided in init_scylla.
        # If necessary, we just assume "deletion" means hiding the chat from the list.
        
        print(f"[{function_name}] chat deleted successfully")
        return True

    except Exception as e:
        print(f"[{function_name}] Invalid chat_id or unexpected error: {str(e)}")
        return False

def get_user_chat_conversation(user_id, chat_id):
    function_name = "get_user_chat_conversation"
    try:
        session = ScyllaConnection.get_session()
        
        # Check if chat is deleted first
        chat_info = get_user_chat_mapping_by_id(chat_id) 
        # Optimization: We could pass user_id if we updated signature, but relying on allow filtering fallback inside helper
        # Actually, let's check deletion using user_id directly if possible.
        # But let's stick to the flow.
        
        if not chat_info or chat_info.get("is_deleted"):
            return None

        # Fetch conversation rows
        query = """
            SELECT message_json FROM chatbot_user_conversations 
            WHERE user_id = %s AND chat_id = %s
        """
        rows = session.execute(query, (user_id, chat_id))
        
        conversation_list = []
        for row in rows:
            try:
                msg = json.loads(row.message_json)
                conversation_list.append(msg)
            except:
                continue
                
        # Existing API expects:
        # {
        #    "_id": chat_id,
        #    "user_id": user_id,
        #    "conversation": [ ... messages ... ]
        # }
        
        if not conversation_list:
            return None
            
        result = {
            "chat_id": chat_id,
            "user_id": user_id,
            "conversation": conversation_list
        }
        
        return result

    except Exception as e:
        print(f"[{function_name}] Unexpected error: {str(e)}")
        return None
