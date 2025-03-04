from flask import Flask, request, jsonify
import requests
from urllib.parse import urlencode
import json
import base64
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad

app = Flask(__name__)

# Proxy configuration
proxy_info = "xojksxpy-rotate:zyiuro40f0v1"
proxies = {
    'http': f'http://{proxy_info}@p.webshare.io:80',
    'https': f'http://{proxy_info}@p.webshare.io:80'
}

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

def http_call(url, headers):
    response = requests.get(url, headers=headers, proxies=proxies)
    return response.json()

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
    response = requests.post(url, headers=headers, json=data, proxies=proxies)
    json_data = response.json()
    
    names = []
    for item in json_data["result"]:
         name = item.get("name", "")
         if name != 'قم بتحديث التطبيق من متجر جوجل بلاي':
              names.append(name)

    return names

@app.route('/search', methods=['GET'])
def search_number():
    number = request.args.get('number')
    
    if number:
        try:
            formatted_number = format_number(number)
            numbox = numBox(formatted_number)

            # Eyecon API
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

            eyecon_name = ""
            try:
                eyecon_response = http_call(eyecon_url, eyecon_headers)
                eyecon_name = eyecon_response[0]["name"]
            except (json.JSONDecodeError, IndexError):
                pass

            # Messente API
            messente_url = f"https://messente.com/messente-api/number-lookup/?phone_number=%2B{formatted_number}"
            messente_headers = {"host": "messente.com"}
            try:
                messente_response = http_call(messente_url, messente_headers)
                carrier = messente_response["originalCarrierName"]
                country = messente_response["countryName"]
                timeZone = messente_response["timeZone"]
            except (json.JSONDecodeError, KeyError):
                carrier = ""
                country = ""
                timeZone = ""

            # CallApp API
            callapp_url = f"https://s.callapp.com/callapp-server/csrch?cpn=%2B{formatted_number}&myp=gp.104059830954081456032&ibs=0&cid=0&tk=0007847886&cvc=2140"
            callapp_headers = {"host": "s.callapp.com"}
            unknown_name = ""
            try:
                callapp_response = http_call(callapp_url, callapp_headers)
                unknown_name = callapp_response["name"]
            except (json.JSONDecodeError, KeyError):
                pass

            names = [name for name in [eyecon_name, unknown_name] if name]
            name_string = '/'.join(names) if names else "Not found"

            response = {
                "number": formatted_number,
                "name": name_string,
                "carrier": carrier,
                "country": country,
                "timezone": timeZone,
                "names": numbox
            }

            return jsonify(response), 200
        except Exception as e:
            error_response = {"error": str(e)}
            return jsonify(error_response), 500
    else:
        error_response = {"error": "Invalid request parameters"}
        return jsonify(error_response), 400

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=5000)
