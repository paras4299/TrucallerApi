from flask import Flask, request, jsonify
import asyncio
import aiohttp

app = Flask(__name__)

async def fetch(session, url, headers):
    try:
        async with session.get(url, headers=headers) as response:
            return response
    except aiohttp.ClientConnectionError:
        return None

async def get_data(url, headers):
    async with aiohttp.ClientSession() as session:
        response = await fetch(session, url, headers)
        if response:
            if 'application/json' in response.headers.get('Content-Type', ''):
                data = await response.json()
            else:
                data = await response.text()
        else:
            data = None
    return data

@app.route('/search', methods=['GET'])
async def get_phone_info():
    number = request.args.get('number')
    if len(number) >= 10:
        formatted_number = format_number(number)

        urls = [
            f'https://api.eyecon-app.com/app/getnames.jsp?cli={formatted_number}&lang=en&is_callerid=true&is_ic=true&cv=vc_494_vn_4.0.494_a&requestApi=okHttp&source=MenifaFragment',
            f"https://messente.com/messente-api/number-lookup/?phone_number=%2B{formatted_number}",
            f"https://s.callapp.com/callapp-server/csrch?cpn=%2B{formatted_number}&myp=gp.104059830954081456032&ibs=0&cid=0&tk=0007847886&cvc=2140"
        ]
        headers = [
            {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.88 Safari/537.36",
                "accept": "application/json",
                "e-auth-v": "e1",
                "e-auth": "1e942fe9-5b71-4c3f-9ee7-56344780dee0",
                "e-auth-c": "24",
                "e-auth-k": "PgdtSBeR0MumR7fO",
                "accept-charset": "UTF-8"
            },
            {"host": "messente.com"},
            {"host": "s.callapp.com"}
        ]
        
        try:
            responses = await asyncio.gather(*(get_data(url, header) for url, header in zip(urls, headers)))
            
            name = responses[0][0]["name"] if responses[0] else ""
            carrier = responses[1]["originalCarrierName"] if responses[1] else ""
            country = responses[1]["countryName"] if responses[1] else ""
            timeZone = responses[1]["timeZone"] if responses[1] else ""
            unknown_name = responses[2]["name"] if responses[2] else ""
            
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
        except Exception as e:
            error_response = {"error": str(e)}
            return jsonify(error_response), 500
    else:
        error_response = {"error": "Invalid Number. Please enter a valid phone number."}
        return jsonify(error_response), 400

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

if __name__ == '__main__':
    app.run()
