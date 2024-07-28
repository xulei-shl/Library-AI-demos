import requests
from dotenv import load_dotenv
import os
import json
from datetime import datetime, timedelta

def get_access_token():
    load_dotenv()

    api_key = os.getenv('API_KEY')
    secret_key = os.getenv('SECRET_KEY')
    token_url = 'https://aip.baidubce.com/oauth/2.0/token'

    url = f"{token_url}?grant_type=client_credentials&client_id={api_key}&client_secret={secret_key}"

    payload = ""
    headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    }

    response = requests.request("POST", url, headers=headers, data=payload)
    response_data = json.loads(response.text)

    access_token = response_data.get('access_token')
    expires_in = response_data.get('expires_in')
    expiration_date = datetime.now() + timedelta(seconds=expires_in)

    token_info = {
        'access_token': access_token,
        'expiration_date': expiration_date.isoformat()
    }

    # Save token.json to the same directory as the script
    script_dir = os.path.dirname(__file__)
    token_file_path = os.path.join(script_dir, 'token.json')
    
    with open(token_file_path, 'w') as token_file:
        json.dump(token_info, token_file)

    return access_token

def load_access_token():
    try:
        # Load token.json from the same directory as the script
        script_dir = os.path.dirname(__file__)
        token_file_path = os.path.join(script_dir, 'token.json')
        
        with open(token_file_path, 'r') as token_file:
            token_info = json.load(token_file)
            expiration_date = datetime.fromisoformat(token_info['expiration_date'])
            if datetime.now() < expiration_date:
                return token_info['access_token']
            else:
                return get_access_token()
    except (FileNotFoundError, json.JSONDecodeError):
        return get_access_token()

    
#测试
if __name__ == '__main__':
    load_access_token()
    print(get_access_token())
