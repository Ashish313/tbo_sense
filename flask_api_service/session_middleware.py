import jwt
from functools import wraps
from flask import request, jsonify, g
import logging

from applications.etcd.init_etcd import global_config

def session_middleware(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # auth_header = request.headers.get("Authorization", None)

        # if auth_header is None:
        #     logging.warning("Missing Authorization header")
        #     return jsonify({
        #         "status": False,
        #         "session_expired": True,
        #         "msg": "Unauthorized request. Missing token."
        #     }), 401

        # parts = auth_header.split(" ")

        # if len(parts) != 2 or parts[0].lower() != "bearer":
        #     logging.warning(f"Invalid Authorization header format: {auth_header}")
        #     return jsonify({
        #         "status": False,
        #         "session_expired": True,
        #         "msg": "Unauthorized request. Invalid token format."
        #     }), 401

        try:

            g.user_id =  "6002292655" #replace with str(raw_uid)
            g.user_name = "sudeep.ignition" #replace with user_name

            # decoded = jwt.decode(token, global_config.config.jwt_secret, algorithms=["HS256"])
            
            # # Aligning with Go middleware reference:
            # # userClaims.Contact -> userId
            # # userClaims.Name -> name
            
            # # Note: JSON keys are typically lowercase. Assuming "contact" and "name".
            # raw_uid = decoded.get("contact")
            # user_name = decoded.get("name")

            # if not raw_uid:
            #     logging.error("Token missing contact")
            #     return jsonify({
            #         "status": False,
            #         "session_expired": True,
            #         "msg": "Invalid session. contact missing in token."
            #     }), 401

            # # Use raw string for Scylla compatibility
            # g.user_id = str(raw_uid)
            # g.user_name = user_name

            # g.bearer_token = token
            # logging.debug(f"JWT decoded successfully: {decoded} (user_id={g.user_id})")

        except jwt.ExpiredSignatureError as e:
            logging.error(f"Token expired: {e}")
            return jsonify({
                "status": False,
                "session_expired": True,
                "msg": "Session expired. Please log in again."
            }), 401
        except jwt.InvalidTokenError as e:
            logging.error(f"Invalid token: {e}")
            return jsonify({
                "status": False,
                "session_expired": True,
                "msg": "Invalid token. Unauthorized access."
            }), 401

        return f(*args, **kwargs)
    return decorated_function
