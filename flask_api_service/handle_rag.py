import json
import time

from langchain_core.messages import AIMessage

from applications.etcd.init_etcd import global_config
from applications.milvus.milvus_connection import get_vector_store
from costants.milvus_collections import ARTICLE_RAG
from StateBase import StateBase


def rag_search_node(state: StateBase):
    """Fallback node when no tool matches. Performs RAG-based retrieval using direct embedding search."""
    try:
        # Getting user message from state
        messages = state.get("messages", [])

        # Get the last user message
        user_query = None
        for msg in reversed(messages):
            if hasattr(msg, 'content') and not isinstance(msg, AIMessage):
                user_query = msg.content if isinstance(msg.content, str) else str(msg.content)
                break

        if not user_query:
            response_json = json.dumps({
                "text": "I couldn't understand your query. Please try again.",
                "end_prompt": True,
                "table": False,
                "data": None,
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
            })
            return {"messages": [AIMessage(content=response_json)]}

        # Initialize vector store with embedding field
        vector_store = get_vector_store(
            ARTICLE_RAG,
            "content",
            "article_embedding"
        )

        # Perform direct similarity search on embedding field
        search_results = vector_store.similarity_search_with_score(
            query=user_query,
            k=15
        )

        # Filter by score threshold (Milvus returns distance, lower is better for cosine)
        # Adjust threshold based on your distance metric
        score_threshold = global_config.config.milvus_config.fallback_vector_similarity_threshold  # For cosine distance, lower means more similar
        best_score = 2
        filtered_results = []
        for doc, score in search_results:
            print(score)
            if score > best_score:
                best_score = score
            if score <= score_threshold and score < best_score:
                if len(filtered_results) == 0:
                    filtered_results.append(doc)
                else:
                    filtered_results[0] = doc

        if not filtered_results:
            response_json = json.dumps({
                "text": "No relevant content found for your query.",
                "end_prompt": True,
                "table": False,
                "data": None,
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
                "status": True
            })
            return {"messages": [AIMessage(content=response_json)]}

        # Get the most relevant document (first one after filtering)
        most_relevant_doc = filtered_results[0]
        final_text = most_relevant_doc.page_content

        response_json = json.dumps({
            "text": final_text,
            "end_prompt": True,
            "table": False,
            "data": None,
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
            "status": True
        })

        return {"messages": [AIMessage(content=response_json)]}

    except Exception as ex:
        error_response_json = json.dumps({
            "text": "I couldn't understand your query. Please try again.",
            "end_prompt": True,
            "table": False,
            "data": None,
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
            "status": False,
            "error": str(ex)
        })

        return {"messages": [AIMessage(content=error_response_json)]}