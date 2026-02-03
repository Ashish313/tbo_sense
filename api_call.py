import requests
from bson import ObjectId
import json
import time
from applications.logger.mod import generate_app_log, LogLevels



def post_api(data: dict, url: str, token: str, user_id: str, api_name: str = "post_api"):
    
    if isinstance(user_id, ObjectId):
        user_id =  str(user_id)

    headers = {
        'Authorization': "Bearer "+ token,
        'Content-Type': 'application/json',
        'X-Seller-Id': user_id
    }

    start_time = int(time.time() * 1000)
    # Log Request
    generate_app_log(
        api_name=api_name,
        log_level=LogLevels.Info,
        message=f"Request: {json.dumps(data, default=str)} URL: {url}",
        start_time=start_time,
        reference_id=user_id,
        user_id=user_id
    )

    try:
        response = requests.post(url, json=data, headers=headers)
        response.raise_for_status()  # Raise error for bad responses
        
        resp_json = response.json()
        # Log Success Response
        generate_app_log(
            api_name=api_name,
            log_level=LogLevels.Info,
            message=f"Response: {json.dumps(resp_json, default=str)}",
            start_time=start_time,
            reference_id=user_id,
            user_id=user_id
        )
        return resp_json, True
    except requests.exceptions.HTTPError as e:
        error_details = ""
        try:
             error_details = e.response.text
        except:
             pass
        
        error_msg = f"Error: {str(e)} Details: {error_details}"
        # Log Error
        generate_app_log(
            api_name=api_name,
            log_level=LogLevels.Error,
            message=error_msg,
            start_time=start_time,
            reference_id=user_id,
            user_id=user_id
        )
        return {"error": str(e), "details": error_details, "status_code": e.response.status_code}, False
    except requests.exceptions.RequestException as e:
        error_msg = str(e)
        # Log Error
        generate_app_log(
            api_name=api_name,
            log_level=LogLevels.Error,
            message=f"Error: {error_msg}",
            start_time=start_time,
            reference_id=user_id,
            user_id=user_id
        )
        return {"error": error_msg}, False

def get_api(params: dict, url: str, token: str, user_id: str, api_name: str = "get_api"):
    
    if isinstance(user_id, ObjectId):
        user_id =  str(user_id)

    headers = {
        'Authorization': "Bearer "+ token,
        'Content-Type': 'application/json',
        'X-Seller-Id': user_id
    }

    start_time = int(time.time() * 1000)
    # Log Request
    generate_app_log(
        api_name=api_name,
        log_level=LogLevels.Info,
        message=f"Params: {json.dumps(params, default=str)} URL: {url}",
        start_time=start_time,
        reference_id=user_id,
        user_id=user_id
    )

    try:
        response = requests.get(url, params=params, headers=headers)
        response.raise_for_status()  # Raise error for bad responses
        
        resp_json = response.json()
        # Log Success Response
        generate_app_log(
            api_name=api_name,
            log_level=LogLevels.Info,
            message=f"Response: {json.dumps(resp_json, default=str)}",
            start_time=start_time,
            reference_id=user_id,
            user_id=user_id
        )
        return resp_json, True
    except requests.exceptions.HTTPError as e:
        error_details = ""
        try:
             error_details = e.response.text
        except:
             pass
        
        error_msg = f"Error: {str(e)} Details: {error_details}"
        # Log Error
        generate_app_log(
            api_name=api_name,
            log_level=LogLevels.Error,
            message=error_msg,
            start_time=start_time,
            reference_id=user_id,
            user_id=user_id
        )
        return {"error": str(e), "details": error_details, "status_code": e.response.status_code}, False
    except requests.exceptions.RequestException as e:
        error_msg = str(e)
        # Log Error
        generate_app_log(
            api_name=api_name,
            log_level=LogLevels.Error,
            message=f"Error: {error_msg}",
            start_time=start_time,
            reference_id=user_id,
            user_id=user_id
        )
        return {"error": error_msg}, False