import re


def extract_session_id(session_string: str):
    # Use re.search to find the session ID in the input string
    match = re.search(r'/sessions/([^/]+)/', session_string)
    if match:
        session_id = match.group(1)
        print("Extracted Session ID:", session_id)
    else:
        print("Session ID not found in the input string.")


def get_str_from_food_dict(food_dict: dict):
    result = ", ".join([f"{int(value)} {key}" for key, value in food_dict.items()])
    return result
