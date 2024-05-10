from flask import Flask, request, jsonify
import requests
import json

app = Flask(__name__)

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
    response = requests.get(url, headers=headers)
    return response.json()
    
@app.route('/search', methods=['GET'])
def get_phone_info():
    number = request.args.get('number')
    if len(number) >= 10:
        formatted_number = format_number(number)

        url = f'https://api.eyecon-app.com/app/getnames.jsp?cli={formatted_number}&lang=en&is_callerid=true&is_ic=true&cv=vc_494_vn_4.0.494_a&requestApi=okHttp&source=MenifaFragment'
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.88 Safari/537.36",
            "accept": "application/json",
            "e-auth-v": "e1",
            "e-auth": "1e942fe9-5b71-4c3f-9ee7-56344780dee0",
            "e-auth-c": "24",
            "e-auth-k": "PgdtSBeR0MumR7fO",
            "accept-charset": "UTF-8"
        }

        try:
            res = http_call(url, headers)
            name = res[0]["name"]
        except (json.JSONDecodeError, IndexError):
            name = ""

        url1 = f"https://messente.com/messente-api/number-lookup/?phone_number=%2B{formatted_number}"
        headers1 = {
            "host": "messente.com"
        }
        try:
            res1 = http_call(url1, headers1)
            carrier = res1["originalCarrierName"]
            country = res1["countryName"]
            timeZone = res1["timeZone"]
        except (json.JSONDecodeError, KeyError):
            carrier = ""
            country = ""
            timeZone = ""

        url2 = f"https://s.callapp.com/callapp-server/csrch?cpn=%2B{formatted_number}&myp=gp.104059830954081456032&ibs=0&cid=0&tk=0007847886&cvc=2140"
        headers2 = {
            "host": "s.callapp.com"
        }
        try:
            res2 = http_call(url2, headers2)
            unknown_name = res2["name"]
        except (json.JSONDecodeError, KeyError):
            unknown_name = ""

        if name and unknown_name:
           names = f"{name}/{unknown_name}"
        elif name:
           names = name
        elif unknown_name:
           names = unknown_name
        else:
           names = "Not found"

        response = {
            "number": formatted_number,
            "name": names,
            "carrier": carrier,
            "country": country,
            "timezone": timeZone
        }

        return jsonify(response), 200
    else:
        error_response = {"error": "Invalid Number. Please enter a valid phone number."}
        return jsonify(error_response), 400

if __name__ == '__main__':
    app.run()
