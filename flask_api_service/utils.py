import json

def jsonify(doc):
    if isinstance(doc, list):
        return [jsonify(d) for d in doc]
    if isinstance(doc, dict):
        return {k: jsonify(v) for k, v in doc.items()}
    return doc


def convert_object_id_to_string(obj_id):
    return str(obj_id)