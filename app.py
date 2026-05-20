from flask import Flask, request, jsonify, render_template
import requests
import json

app = Flask(__name__)

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/update-birthdate', methods=['POST'])
def update_birthdate():
    try:
        data = request.get_json(force=True) or {}
    except Exception:
        return jsonify({"success": False, "message": "Maling format ng data na ipinadala sa server."}), 400

    roblosecurity = data.get("cookie", "")
    password = data.get("password", "")
    challenge_id = data.get("challengeId")
    challenge_metadata = data.get("challengeMetadata")

    # Linisin ang cookie gamit ang purong python strip
    roblosecurity = str(roblosecurity).strip()

    if not roblosecurity or not password:
        return jsonify({"success": False, "message": "Kulang ang Cookie o Password."}), 400

    new_birthday = {
        "birthMonth": 6,
        "birthDay": 5,
        "birthYear": 2015
    }

    session = requests.Session()
    session.cookies.set(".ROBLOSECURITY", roblosecurity, domain=".roblox.com")

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Content-Type": "application/json;charset=UTF-8",
        "Origin": "https://www.roblox.com",
        "Referer": "https://www.roblox.com/"
    }

    # 1. Kukuha ng XSRF Token sa Roblox
    try:
        token_resp = session.post("https://auth.roblox.com/v2/logout", headers=headers)
        xsrf_token = token_resp.headers.get("x-csrf-token")
    except Exception as e:
        return jsonify({"success": False, "message": f"Hindi makakonekta ang Render sa Roblox: {str(e)}"}), 500
    
    if not xsrf_token:
        return jsonify({"success": False, "message": "Expired o maling Cookie. Hindi makakuha ng CSRF token mula sa Roblox."}), 400

    headers["x-csrf-token"] = xsrf_token

    # Isama ang mga challenge headers kung galing sa natapos na captcha
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

    # 2. Ipadala ang request sa Roblox API
    try:
        response = session.post(
            "https://users.roblox.com/v1/birthdate", 
            headers=headers, 
            data=json.dumps(payload)
        )
    except Exception as e:
        return jsonify({"success": False, "message": f"Nagka-error sa pag-send sa Roblox: {str(e)}"}), 500

    # CASE A: Tagumpay!
    if response.status_code == 200:
        return jsonify({"success": True, "message": "Birthdate updated successfully!"})

    # CASE B: Humihingi ng Captcha (403 Code)
    elif response.status_code == 403 and response.headers.get("Rblx-Challenge-Type") == "chef":
        return jsonify({
            "success": False,
            "captcha_required": True,
            "challengeId": response.headers.get("Rblx-Challenge-Id"),
            "challengeMetadata": response.headers.get("Rblx-Challenge-Metadata")
        }), 403

    # CASE C: Error
    else:
        error_msg = "Tinanggihan ng Roblox."
        try:
            roblox_json = response.json()
            if "errors" in roblox_json and len(roblox_json["errors"]) > 0:
                error_msg = roblox_json["errors"][0].get("message", "Maling detalye.")
        except:
            if response.status_code == 403:
                error_msg = "IP Block ng Roblox Server (Hinarang ng Roblox ang IP ng Render)."
        
        return jsonify({
            "success": False, 
            "message": f"{error_msg} (Status Code: {response.status_code})"
        }), response.status_code

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
