from langchain_core.rate_limiters import InMemoryRateLimiter
from langchain_ollama import ChatOllama
from applications.etcd.init_etcd import global_config

# rate_limiter = InMemoryRateLimiter(requests_per_second=1, check_every_n_seconds=0.1, max_bucket_size=10)
#
# global_config.read_etcd_config(file_path="config")
#
# llm = ChatOllama(
#     base_url=global_config.config.chatbot_config.base_url,
#     model=global_config.config.chatbot_config.model,
#     temperature=0.0,
#     num_predict=8192,
#     rate_limiter=rate_limiter,
# )

