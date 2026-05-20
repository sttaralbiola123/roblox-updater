from flask import Flask, request, jsonify, render_template
import requests
import json

app = Flask(__name__)

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/update-birthdate', methods=['POST'])
def update_birthdate():
    data = request.json or {}
    roblosecurity = data.get("cookie")
    password = data.get("password")
    
    challenge_id = data.get("challengeId")
    challenge_metadata = data.get("challengeMetadata")

    new_birthday = {
        "birthMonth": 6,
        "birthDay": 5,
        "birthYear": 2015
    }

    if not roblosecurity or not password:
        return jsonify({"success": False, "message": "Kulang ang Cookie o Password."}), 400

    # Linisin ang cookie (tanggalin ang mga whitespace kung mayroon)
    roblosecurity = roblosecurity.trim() if hasattr(roblosecurity, 'trim') else roblosecurity.strip()

    session = requests.Session()
    session.cookies.set(".ROBLOSECURITY", roblosecurity, domain=".roblox.com")

    # Gumamit ng pekeng mobile headers para isipin ng Roblox na galing ito sa totoong cellphone
    headers = {
        "User-Agent": "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Mobile Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Content-Type": "application/json;charset=UTF-8",
        "Origin": "https://www.roblox.com",
        "Referer": "https://www.roblox.com/"
    }

    # 1. Kukuha ng XSRF Token gamit ang mas ligtas na endpoint ng Roblox
    try:
        # Sinusubukan nating kuhanin ang token sa auth endpoint
        token_resp = session.post("https://auth.roblox.com/v2/login", headers=headers, json={})
        xsrf_token = token_resp.headers.get("x-csrf-token")
        
        # Kung wala doon, subukan sa logout endpoint gaya ng dati
        if not xsrf_token:
            token_resp = session.post("https://auth.roblox.com/v2/logout", headers=headers)
            xsrf_token = token_resp.headers.get("x-csrf-token")
            
    except Exception as e:
        return jsonify({"success": False, "message": f"Hindi makakonekta sa Roblox: {str(e)}"}), 500
    
    if not xsrf_token:
        return jsonify({"success": False, "message": "Expired o maling Cookie. Hindi makakuha ng CSRF token."}), 400

    # Idagdag ang CSRF Token sa mga susunod na headers
    headers["x-csrf-token"] = xsrf_token

    # Kung may ipinasang captcha data mula sa frontend, isama ito
    if challenge_id and challenge_metadata:
        headers["Rblx-Challenge-Id"] = challenge_id
        headers["Rblx-Challenge-Type"] = "chef"
        headers["Rblx-Challenge-Metadata"] = challenge_metadata

    payload = {
        "birthMonth": new_birthday["birthMonth"],
        "birthDay": new_birthday["birthDay"],
        "birthYear": new_birthday["birthYear"],
        "password": password
    }

    # 2. Ipadala ang aktuwal na request sa Roblox Birthdate endpoint
    try:
        response = session.post(
            "https://users.roblox.com/v1/birthdate", 
            headers=headers, 
            data=json.dumps(payload) # Tiyaking naka-strict JSON format ang payload
        )
    except Exception as e:
        return jsonify({"success": False, "message": f"Nagka-error sa pagpapadala ng data: {str(e)}"}), 500

    # CASE A: Tagumpay!
    if response.status_code == 200:
        return jsonify({"success": True, "message": "Birthdate updated successfully!"})

    # CASE B: Humihingi ng Captcha (403 Error na may kasamang challenge headers)
    elif response.status_code == 403 and response.headers.get("Rblx-Challenge-Type") == "chef":
        return jsonify({
            "success": False,
            "captcha_required": True,
            "challengeId": response.headers.get("Rblx-Challenge-Id"),
            "challengeMetadata": response.headers.get("Rblx-Challenge-Metadata")
        }), 403

    # CASE C: Tinanggihan dahil sa maling password, o dahil block ang IP ng Render
    else:
        # Ibabalik natin ang eksaktong mensahe mula sa Roblox para malaman natin ang tunay na dahilan
        error_msg = "Tinanggihan ng Roblox."
        try:
            roblox_json = response.json()
            if "errors" in roblox_json and len(roblox_json["errors"]) > 0:
                error_msg = roblox_json["errors"][0].get("message", "Maling detalye o proteksyon ng Roblox.")
        except:
            if response.status_code == 403:
                error_msg = "IP Block ng Roblox (Hinarang ng Roblox ang server ng Render)."
        
        return jsonify({
            "success": False, 
            "message": f"{error_msg} (Status Code: {response.status_code})"
        }), response.status_code

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
