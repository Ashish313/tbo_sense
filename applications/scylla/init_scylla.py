import atexit
from cassandra.cluster import Cluster, ExecutionProfile, EXEC_PROFILE_DEFAULT, ConsistencyLevel
from cassandra.auth import PlainTextAuthProvider
from cassandra.policies import ConstantReconnectionPolicy, DCAwareRoundRobinPolicy, TokenAwarePolicy
from applications.etcd.init_etcd import global_config

class ScyllaConnection:
    _session = None
    _cluster = None

    @staticmethod
    def init_connection():
        if ScyllaConnection._session is None:
            print("ScyllaDB connection initiated...")
            scylla_config = global_config.config.scylla
            auth_provider = PlainTextAuthProvider(
                username=scylla_config.username,
                password=scylla_config.password
            )
            
            # Create execution profile for Quorum consistency and 5s request timeout
            # Adding explicit Load Balancing Policy to silence warning and ensure correct routing
            profile = ExecutionProfile(
                consistency_level=ConsistencyLevel.QUORUM,
                request_timeout=5.0,
                load_balancing_policy=TokenAwarePolicy(DCAwareRoundRobinPolicy())
            )

            # Parse host and port from config string (e.g. "1.2.3.4:9042" or "1.2.3.4")
            host_str = scylla_config.host.strip()
            if ":" in host_str:
                host_ip, port_str = host_str.split(":")
                host_port = int(port_str)
            else:
                host_ip = host_str
                host_port = 9042

            ScyllaConnection._cluster = Cluster(
                [host_ip],
                port=host_port,
                auth_provider=auth_provider,
                connect_timeout=5.0,
                control_connection_timeout=5.0,
                reconnection_policy=ConstantReconnectionPolicy(5.0, None),
                execution_profiles={EXEC_PROFILE_DEFAULT: profile}
            )

            # Note: set_core_connections_per_host is restricted for protocol versions > 2.
            # Modern Scylla/Cassandra drivers manage connections automatically efficiently.
            # We skip explicit pooling configuration for compatibility.

            ScyllaConnection._session = ScyllaConnection._cluster.connect()
            
            # Ensure keyspace exists
            keyspace = scylla_config.keyspace
            ScyllaConnection._session.execute(f"""
                CREATE KEYSPACE IF NOT EXISTS {keyspace}
                WITH replication = {{'class': 'SimpleStrategy', 'replication_factor': 1}}
            """)
            ScyllaConnection._session.set_keyspace(keyspace)

            # Ensure tables exist
            ScyllaConnection._create_tables()

            print("ScyllaDB connected successfully...")

    @staticmethod
    def _create_tables():
        # User Chats Table
        ScyllaConnection._session.execute("""
            CREATE TABLE IF NOT EXISTS chatbot_user_chats (
                user_id text,
                chat_id text,
                chat_name text,
                created_date bigint,
                lut bigint,
                is_deleted boolean,
                chat_initiated boolean,
                PRIMARY KEY (user_id, chat_id)
            )
        """)

        # Chat Conversations Table
        ScyllaConnection._session.execute("""
            CREATE TABLE IF NOT EXISTS chatbot_user_conversations (
                user_id text,
                chat_id text,
                timestamp bigint,
                message_json text,
                is_conversation_ended boolean,
                PRIMARY KEY ((user_id, chat_id), timestamp)
            ) WITH CLUSTERING ORDER BY (timestamp ASC)
        """)

    @staticmethod
    def get_session():
        if ScyllaConnection._session is None:
            ScyllaConnection.init_connection()
        return ScyllaConnection._session

    @staticmethod
    def close_connection():
        if ScyllaConnection._cluster:
            ScyllaConnection._cluster.shutdown()
            print("ScyllaDB connection closed.")

# Register close on app exit
atexit.register(ScyllaConnection.close_connection)
