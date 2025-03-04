from flask import Flask, request, jsonify
import aiohttp
import asyncio
import base64
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad

app = Flask(__name__)

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

async def fetch(session, url, headers=None, json_data=None, method="GET"):
    """Fetch data asynchronously using aiohttp"""
    try:
        async with session.request(method, url, headers=headers, json=json_data, timeout=5) as response:
            return await response.json()
    except Exception:
        return {}

async def fetch_eyecon(session, formatted_number):
    url = f'https://api.eyecon-app.com/app/getnames.jsp?cli={formatted_number}&lang=en'
    headers = {"User-Agent": "Mozilla/5.0"}
    data = await fetch(session, url, headers)
    return data[0]["name"] if data else ""

async def fetch_messente(session, formatted_number):
    url = f"https://messente.com/messente-api/number-lookup/?phone_number=%2B{formatted_number}"
    headers = {"host": "messente.com"}
    data = await fetch(session, url, headers)
    return (
        data.get("originalCarrierName", ""),
        data.get("countryName", ""),
        data.get("timeZone", "")
    )

async def fetch_callapp(session, formatted_number):
    url = f"https://s.callapp.com/callapp-server/csrch?cpn=%2B{formatted_number}"
    headers = {"host": "s.callapp.com"}
    data = await fetch(session, url, headers)
    return data.get("name", "")

async def fetch_numbox(session, formatted_number):
    """Fetches names from NumberBox API"""
    url = 'https://api.numberbox.app/search'
    ccode, phoneNumber = formatted_number[:2], formatted_number[2:]
    
    data = {'ccode': get_encode(f"%2B{ccode}"), 'number': get_encode(str(phoneNumber))}
    headers = {'host': 'api.numberbox.app', 'device': 'android', 'content-type': 'application/json'}
    
    json_data = await fetch(session, url, headers, json_data=data, method="POST")
    return [item.get("name", "") for item in json_data.get("result", []) if item.get("name") != 'قم بتحديث التطبيق من متجر جوجل بلاي']

@app.route('/search', methods=['GET'])
async def search_number():
    number = request.args.get('number')
    if not number:
        return jsonify({"error": "Invalid request parameters"}), 400

    formatted_number = format_number(number)

    async with aiohttp.ClientSession() as session:
        tasks = [
            fetch_numbox(session, formatted_number),
            fetch_eyecon(session, formatted_number),
            fetch_messente(session, formatted_number),
            fetch_callapp(session, formatted_number)
        ]
        numbox, eyecon_name, messente_data, callapp_name = await asyncio.gather(*tasks)
    
    carrier, country, timeZone = messente_data
    name_string = '/'.join([eyecon_name, callapp_name]) or "Not found"

    response = {
        "number": formatted_number,
        "name": name_string,
        "carrier": carrier,
        "country": country,
        "timezone": timeZone,
        "names": numbox
    }

    return jsonify(response), 200

if __name__ == '__main__':
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5000)
