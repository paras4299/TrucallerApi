from flask import Flask, request, jsonify
import requests
import base64
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
from concurrent.futures import ThreadPoolExecutor

app = Flask(__name__)

# Proxy Configuration
proxy_info = "xojksxpy-rotate:zyiuro40f0v1"
proxies = {
    'http': f'http://{proxy_info}@p.webshare.io:80',
    'https': f'http://{proxy_info}@p.webshare.io:80'
}

# Reuse session for better performance
session = requests.Session()
session.proxies = proxies

# Encryption Setup
key = base64.b64decode("mKEP38MTRSMfmSJJiRuVgGJQ2xpzo9o5lsSm/DbkzwY=")
iv = base64.b64decode("AAECAwQFBgcICQoLDA0ODw==")

def get_encode(data):
    cipher = AES.new(key, AES.MODE_CBC, iv)
    padded_data = pad(data.encode(), AES.block_size)
    return base64.b64encode(cipher.encrypt(padded_data)).decode()

def format_number(number):
    """Formats phone number to international format"""
    if number:
        formatted_number = number.replace(' ', '')
        if formatted_number.startswith("+91"):
            return formatted_number[1:]
        elif len(formatted_number) == 10:
            return "91" + formatted_number
        return formatted_number
    return number

def http_call(url, headers):
    """Performs an HTTP GET request and returns JSON response"""
    try:
        response = session.get(url, headers=headers, timeout=5)
        return response.json()
    except requests.RequestException:
        return {}

def numBox(number):
    """Fetches names from NumberBox API"""
    url = 'https://api.numberbox.app/search'
    ccode, phoneNumber = number[:2], number[2:]

    data = {
        'ccode': get_encode(f"%2B{ccode}"),
        'number': get_encode(str(phoneNumber))
    }
    headers = {
        'host': 'api.numberbox.app',
        'device': 'android',
        'content-type': 'application/json; charset=UTF-8',
        'accept-encoding': 'gzip',
        'user-agent': 'okhttp/4.11.0'
    }
    
    try:
        response = session.post(url, headers=headers, json=data, timeout=5)
        json_data = response.json()
        
        # Ensure we collect all valid names
        return list(set(
            item.get("name", "").strip() 
            for item in json_data.get("result", []) 
            if item.get("name") and item.get("name") != 'قم بتحديث التطبيق من متجر جوجل بلاي'
        ))
    except requests.RequestException:
        return []

def fetch_eyecon(formatted_number):
    """Fetches name from Eyecon API"""
    url = f'https://api.eyecon-app.com/app/getnames.jsp?cli={formatted_number}&lang=en'
    headers = {
        "User-Agent": "Mozilla/5.0",
        "accept": "application/json"
    }
    data = http_call(url, headers)
    return data[0]["name"].strip() if data and "name" in data[0] else ""

def fetch_messente(formatted_number):
    """Fetches carrier and location from Messente API"""
    url = f"https://messente.com/messente-api/number-lookup/?phone_number=%2B{formatted_number}"
    headers = {"host": "messente.com"}
    data = http_call(url, headers)
    return (
        data.get("originalCarrierName", "").strip(),
        data.get("countryName", "").strip(),
        data.get("timeZone", "").strip()
    )

def fetch_callapp(formatted_number):
    """Fetches name from CallApp API"""
    url = f"https://s.callapp.com/callapp-server/csrch?cpn=%2B{formatted_number}"
    headers = {"host": "s.callapp.com"}
    data = http_call(url, headers)
    return data.get("name", "").strip() if data and "name" in data else ""

@app.route('/search', methods=['GET'])
def search_number():
    number = request.args.get('number')

    if not number:
        return jsonify({"error": "Invalid request parameters"}), 400

    formatted_number = format_number(number)

    with ThreadPoolExecutor(max_workers=4) as executor:
        future_numbox = executor.submit(numBox, formatted_number)
        future_eyecon = executor.submit(fetch_eyecon, formatted_number)
        future_messente = executor.submit(fetch_messente, formatted_number)
        future_callapp = executor.submit(fetch_callapp, formatted_number)

        numbox = future_numbox.result()
        eyecon_name = future_eyecon.result()
        carrier, country, timeZone = future_messente.result()
        callapp_name = future_callapp.result()

    # Combine all unique names properly
    all_names = set(filter(None, [eyecon_name, callapp_name] + numbox))
    name_string = ' / '.join(all_names) if all_names else "Not found"

    response = {
        "number": formatted_number,
        "name": name_string,
        "carrier": carrier,
        "country": country,
        "timezone": timeZone,
        "names": list(all_names)
    }

    return jsonify(response), 200

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000, threaded=True)
