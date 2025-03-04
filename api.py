from flask import Flask, request, jsonify
import requests
from concurrent.futures import ThreadPoolExecutor
import json
import base64
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
import time

app = Flask(__name__)

# Proxy configuration
proxy_info = "xojksxpy-rotate:zyiuro40f0v1"
proxies = {
    'http': f'http://{proxy_info}@p.webshare.io:80',
    'https': f'http://{proxy_info}@p.webshare.io:80'
}

# Session for connection pooling
session = requests.Session()

def format_number(number):
    if number:
        formatted_number = number.replace(' ', '')
        if formatted_number.startswith("+91"):
            return formatted_number[1:]
        elif len(formatted_number) == 10:
            return "91" + formatted_number
        else:
            return formatted_number
    return number

def http_call(url, headers, timeout=5):
    try:
        response = session.get(url, headers=headers, proxies=proxies, timeout=timeout)
        return response.json()
    except (requests.exceptions.RequestException, json.JSONDecodeError) as e:
        return {"error": str(e)}

key = base64.b64decode("mKEP38MTRSMfmSJJiRuVgGJQ2xpzo9o5lsSm/DbkzwY=")
iv = base64.b64decode("AAECAwQFBgcICQoLDA0ODw==")

def get_encode(data):
    cipher = AES.new(key, AES.MODE_CBC, iv)
    padded_data = pad(data.encode(), AES.block_size)
    encoded = base64.b64encode(cipher.encrypt(padded_data)).decode()
    return encoded

def get_decode(data):
    cipher = AES.new(key, AES.MODE_CBC, iv)
    decrypted_data = cipher.decrypt(base64.b64decode(data))
    unpadded_data = unpad(decrypted_data, AES.block_size)
    return unpadded_data.decode()
    
def numBox(number):
    url = 'https://api.numberbox.app/search'
    ccode = number[:2]
    phoneNumber = number[2:]
    
    encoded_ccode = get_encode(f"%2B{ccode}")
    encoded_number = get_encode(str(phoneNumber))
    data = {
        'ccode': encoded_ccode,
        'number': encoded_number
    }
    headers = {
        'host': 'api.numberbox.app',
        'device': 'android',
        'content-type': 'application/json; charset=UTF-8',
        'accept-encoding': 'gzip',
        'user-agent': 'okhttp/4.11.0'
    }
    
    try:
        response = session.post(url, headers=headers, json=data, proxies=proxies, timeout=5)
        json_data = response.json()
        
        names = []
        for item in json_data.get("result", []):
            name = item.get("name", "")
            if name != 'Ù‚Ù… Ø¨ØªØ­Ø¯ÙŠØ« Ø§Ù„ØªØ·Ø¨ÙŠÙ‚ Ù…Ù† Ù…ØªØ¬Ø± Ø¬ÙˆØ¬Ù„ Ø¨Ù„Ø§ÙŠ':
                names.append(name)
        return names
    except Exception:
        return []

def fetch_eyecon(formatted_number):
    eyecon_url = f'https://api.eyecon-app.com/app/getnames.jsp?cli={formatted_number}&lang=en&is_callerid=true&is_ic=true&cv=vc_494_vn_4.0.494_a&requestApi=okHttp&source=MenifaFragment'
    eyecon_headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.88 Safari/537.36",
        "accept": "application/json",
        "e-auth-v": "e1",
        "e-auth": "1e942fe9-5b71-4c3f-9ee7-56344780dee0",
        "e-auth-c": "24",
        "e-auth-k": "PgdtSBeR0MumR7fO",
        "accept-charset": "UTF-8"
    }
    
    try:
        eyecon_response = http_call(eyecon_url, eyecon_headers)
        return eyecon_response[0]["name"] if eyecon_response and isinstance(eyecon_response, list) and len(eyecon_response) > 0 else ""
    except (IndexError, KeyError, TypeError):
        return ""

def fetch_messente(formatted_number):
    messente_url = f"https://messente.com/messente-api/number-lookup/?phone_number=%2B{formatted_number}"
    messente_headers = {"host": "messente.com"}
    
    try:
        messente_response = http_call(messente_url, messente_headers)
        return {
            "carrier": messente_response.get("originalCarrierName", ""),
            "country": messente_response.get("countryName", ""),
            "timeZone": messente_response.get("timeZone", "")
        }
    except (KeyError, TypeError):
        return {"carrier": "", "country": "", "timeZone": ""}

def fetch_callapp(formatted_number):
    callapp_url = f"https://s.callapp.com/callapp-server/csrch?cpn=%2B{formatted_number}&myp=gp.104059830954081456032&ibs=0&cid=0&tk=0007847886&cvc=2140"
    callapp_headers = {"host": "s.callapp.com"}
    
    try:
        callapp_response = http_call(callapp_url, callapp_headers)
        return callapp_response.get("name", "")
    except (KeyError, TypeError):
        return ""

@app.route('/search', methods=['GET'])
def search_number():
    start_time = time.time()
    number = request.args.get('number')
    
    if not number:
        return jsonify({"error": "Invalid request parameters"}), 400
    
    try:
        formatted_number = format_number(number)
        
        # Use ThreadPoolExecutor to make API calls in parallel
        with ThreadPoolExecutor(max_workers=4) as executor:
            numbox_future = executor.submit(numBox, formatted_number)
            eyecon_future = executor.submit(fetch_eyecon, formatted_number)
            messente_future = executor.submit(fetch_messente, formatted_number)
            callapp_future = executor.submit(fetch_callapp, formatted_number)
            
            # Get results from futures
            numbox_names = numbox_future.result()
            eyecon_name = eyecon_future.result()
            messente_data = messente_future.result()
            callapp_name = callapp_future.result()
        
        # Process names
        names = [name for name in [eyecon_name, callapp_name] if name]
        name_string = '/'.join(names) if names else "Not found"
        
        response = {
            "number": formatted_number,
            "name": name_string,
            "carrier": messente_data.get("carrier", ""),
            "country": messente_data.get("country", ""),
            "timezone": messente_data.get("timeZone", ""),
            "names": numbox_names,
            "response_time": f"{time.time() - start_time:.2f} seconds"
        }
        
        return jsonify(response), 200
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000, threaded=True)
