from flask import Flask, request, jsonify
import requests
import base64
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
from concurrent.futures import ThreadPoolExecutor, as_completed

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

def encrypt(data):
    """Encrypts the given data using AES-CBC encryption."""
    cipher = AES.new(key, AES.MODE_CBC, iv)
    padded_data = pad(data.encode(), AES.block_size)
    return base64.b64encode(cipher.encrypt(padded_data)).decode()

def format_number(number):
    """Formats phone number to international format"""
    number = number.strip().replace(' ', '')
    if number.startswith("+91"):
        return number[1:]
    elif len(number) == 10:
        return "91" + number
    return number

def fetch_data(url, headers=None, method='get', data=None):
    """Fetches data from an API with retry mechanism."""
    try:
        if method == 'post':
            response = session.post(url, headers=headers, json=data, timeout=3)
        else:
            response = session.get(url, headers=headers, timeout=3)
        if response.status_code == 200:
            return response.json()
    except requests.RequestException:
        return {}
    return {}

def fetch_numberbox(number):
    """Fetches names from NumberBox API"""
    url = 'https://api.numberbox.app/search'
    ccode, phone_number = number[:2], number[2:]

    data = {
        'ccode': encrypt(f"%2B{ccode}"),
        'number': encrypt(str(phone_number))
    }
    headers = {
        'host': 'api.numberbox.app',
        'device': 'android',
        'content-type': 'application/json; charset=UTF-8',
        'accept-encoding': 'gzip',
        'user-agent': 'okhttp/4.11.0'
    }
    
    result = fetch_data(url, headers=headers, method='post', data=data)
    return list(set(item.get("name", "").strip() for item in result.get("result", []) if item.get("name"))) if result else []

def fetch_eyecon(number):
    """Fetches name from Eyecon API"""
    url = f'https://api.eyecon-app.com/app/getnames.jsp?cli={number}&lang=en'
    headers = {"User-Agent": "Mozilla/5.0", "accept": "application/json"}
    data = fetch_data(url, headers)
    return data[0].get("name", "") if data else ""

def fetch_messente(number):
    """Fetches carrier, country, and timezone from Messente API"""
    url = f"https://messente.com/messente-api/number-lookup/?phone_number=%2B{number}"
    headers = {"host": "messente.com"}
    data = fetch_data(url, headers)
    return (
        data.get("originalCarrierName", ""),
        data.get("countryName", ""),
        data.get("timeZone", "")
    )

def fetch_callapp(number):
    """Fetches name from CallApp API"""
    url = f"https://s.callapp.com/callapp-server/csrch?cpn=%2B{number}&myp=gp.104059830954081456032&ibs=0&cid=0&tk=0007847886&cvc=2140"
    headers = {"host": "s.callapp.com"}
    data = fetch_data(url, headers)
    return data.get("name", "")

@app.route('/search', methods=['GET'])
def search_number():
    number = request.args.get('number')

    if not number:
        return jsonify({"error": "Invalid request parameters"}), 400

    formatted_number = format_number(number)

    # Using multi-threading for faster API calls
    with ThreadPoolExecutor(max_workers=4) as executor:
        future_to_api = {
            executor.submit(fetch_numberbox, formatted_number): "numberbox",
            executor.submit(fetch_eyecon, formatted_number): "eyecon",
            executor.submit(fetch_messente, formatted_number): "messente",
            executor.submit(fetch_callapp, formatted_number): "callapp"
        }

        results = {api: None for api in future_to_api.values()}

        for future in as_completed(future_to_api):
            api_name = future_to_api[future]
            try:
                results[api_name] = future.result()
            except Exception as e:
                results[api_name] = None

    # Extract API results
    numbox_names = results["numberbox"] or []
    eyecon_name = results["eyecon"] or ""
    callapp_name = results["callapp"] or ""
    carrier, country, timeZone = results["messente"] or ("", "", "")

    # Build name string
    names = [name for name in [eyecon_name, callapp_name] if name]
    name_string = "/".join(names) if names else "Not found"

    response = {
        "number": formatted_number,
        "name": name_string,
        "carrier": carrier,
        "country": country,
        "timezone": timeZone,
        "names": numbox_names
    }

    return jsonify(response), 200

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000, threaded=True)
