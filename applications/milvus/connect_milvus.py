from pymilvus import connections

from applications.etcd.init_etcd import global_config



class MilvusDB:
    _instance = None
    _connected = False
    _alias = None
    _id = None
    _host = None
    _port = None

    # connection with milvus db
    @classmethod
    def connect(cls):
        # updating class variables
        cls._alias = global_config.config.milvus_config.alias
        cls._host = global_config.config.milvus_config.host
        cls._port = global_config.config.milvus_config.port

        print(f"{cls._host}:{cls._port}:{cls._alias}")
        if not cls._connected:
            connections.connect(
                alias = cls._alias,
                host = cls._host,
                port = cls._port,
            )
            cls._connected = True
            print(f"Connected to Milvus at {cls._host}:{cls._port} with alias '{cls._alias}'")

    # function for disconnect
    @classmethod
    def disconnect(cls):
        if cls._connected:
            connections.disconnect(cls._alias)
            cls._connected = False
            print(f"Disconnected from Milvus alias '{cls._alias}'")

    # function for get instance of milvus db
    @classmethod
    def get_connection(cls):
        return connections.get_connection(cls._alias)