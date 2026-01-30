import threading

from langchain_community.embeddings import SentenceTransformerEmbeddings
from langchain_milvus import Milvus
from pymilvus import connections, Collection, utility
from pymilvus.client.types import LoadState

from applications.etcd.init_etcd import global_config

# Initialize embedding model only once
embeddings = SentenceTransformerEmbeddings(model_name="all-MiniLM-L6-v2")

# Global variable for static connection
_vector_store = None
_lock = threading.Lock()

index_params = {
    "metric_type": "COSINE",   # Use cosine similarity for semantic embeddings
    "index_type": "HNSW",      # Efficient approximate nearest neighbor search
    "params": {"M": 16, "efConstruction": 200}
}

def get_vector_store(collection_name, text_field, summary_embedding):
    global _vector_store
    with _lock:
        if _vector_store is None:
            # connection with milvus
            _vector_store = Milvus(
                embedding_function=embeddings,
                collection_name=collection_name,
                connection_args={
                    "uri": global_config.config.milvus_config.uri,
                    "async_client": False
                },
                text_field=text_field,
                vector_field=summary_embedding,
                index_params=index_params
            )

            # 2. Explicitly connect with pymilvus for collection load
            connections.connect(uri=global_config.config.milvus_config.uri)

    # checking if collection is not loaded then loading again
    load_state = utility.load_state(collection_name)

    if load_state != LoadState.Loaded:
        collection = Collection(collection_name)
        collection.load()

    return _vector_store