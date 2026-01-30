import json
import os
from typing import List
from pydantic import BaseModel

class FlaskApiServiceConfig(BaseModel):
    host: str
    port: int
    debug: bool

class MilvusConfig(BaseModel):
    host: str
    port: str
    alias: str

class ScyllaConfig(BaseModel):
    host: str
    username: str
    password: str
    keyspace: str

class AppConfig(BaseModel):
    flask_api_service: FlaskApiServiceConfig
    milvus_config: MilvusConfig
    scylla: ScyllaConfig
    jwt_secret: str

class GlobalConfig:
    def __init__(self):
        self.config: AppConfig = None
        self.current_env = 'DEV'
        self.load_local_config()

    def load_local_config(self):
        """Load configuration from local.json file."""
        config_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'local.json')
        try:
            with open(config_path, 'r') as f:
                data = json.load(f)
                self.config = AppConfig(**data)
                print("Configuration loaded from local.json")
        except FileNotFoundError:
            print(f"Error: local.json not found at {config_path}")
            # Initialize None, app should probably fail fast if config is missing
        except Exception as e:
            print(f"Error loading local.json: {e}")
            raise e

    def read_etcd_config(self, file_path):
        """Deprecated: kept for compatibility."""
        pass

global_config = GlobalConfig()
