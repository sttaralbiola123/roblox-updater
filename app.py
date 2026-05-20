from flask import Flask, request, jsonify, render_template
import requests

app = Flask(__name__)

# Pag-load sa harap ng website (Frontend)
@app.route('/')
def home():
    return render_template('index.html')

# Ang API endpoint na humahawak sa Roblox request at Captcha
@app.route('/update-birthdate', methods=['POST'])
def update_birthdate():
    data = request.json or {}
    roblosecurity = data.get("cookie")
    password = data.get("password")
    
    # Sasagutin ito ng frontend kapag tapos na ang captcha ng user
    challenge_id = data.get("challengeId")
    challenge_metadata = data.get("challengeMetadata")

    # Target na Birthdate na itatakda (June 5, 2015)
    new_birthday = {
        "birthMonth": 6,
        "birthDay": 5,
        "birthYear": 2015
    }

    if not roblosecurity:
        return jsonify({"success": False, "message": "Walang ipinasang Cookie."}), 400

    # Siguraduhing tama ang format ng cookie para sa requests
    if not roblosecurity.startswith("_|WARNING"):
        # Kung sakaling kulang, nilalagyan natin ng standard warning wrapper ang simula
        pass

    session = requests.Session()
    session.cookies.set(".ROBLOSECURITY", roblosecurity, domain=".roblox.com")

    # 1. Kukuha ng XSRF Token sa Roblox
    try:
        resp = session.post("https://auth.roblox.com/v2/logout")
        xsrf_token = resp.headers.get("x-csrf-token")
    except Exception:
        return jsonify({"success": False, "message": "Hindi makakonekta sa Roblox server."}), 500
    
    if not xsrf_token:
        return jsonify({"success": False, "message": "Invalid o Expired na ang Cookie."}), 400

    # 2. Ihanda ang Headers
    headers = {
        "Content-Type": "application/json",
        "x-csrf-token": xsrf_token,
        "Referer": "https://www.roblox.com/",
        "Origin": "https://www.roblox.com",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }

    # Kung ang request ay nanggaling sa natapos na captcha, isasama ang mga tokens na ito
    if challenge_id and challenge_metadata:
        headers["Rblx-Challenge-Id"] = challenge_id
        headers["Rblx-Challenge-Type"] = "chef"
        headers["Rblx-Challenge-Metadata"] = challenge_metadata

    # 3. Payload na ipapadala sa Roblox
    payload = {
        "birthMonth": new_birthday["birthMonth"],
        "birthDay": new_birthday["birthDay"],
        "birthYear": new_birthday["birthYear"],
        "password": password
    }

    # 4. Fire ang request sa Roblox API
    try:
        response = session.post("https://users.roblox.com/v1/birthdate", headers=headers, json=payload)
    except Exception:
        return jsonify({"success": False, "message": "Nagka-error sa pag-send sa Roblox."}), 500

    # CASE A: Tagumpay!
    if response.status_code == 200:
        return jsonify({"success": True, "message": "Birthdate updated successfully!"})

    # CASE B: Humihingi ng Captcha ang Roblox (403 Code)
    elif response.status_code == 403 and response.headers.get("Rblx-Challenge-Type") == "chef":
        return jsonify({
            "success": False,
            "captcha_required": True,
            "challengeId": response.headers.get("Rblx-Challenge-Id"),
            "challengeMetadata": response.headers.get("Rblx-Challenge-Metadata")
        }), 403

    # CASE C: Ibang error tulad ng Maling Password
    else:
        return jsonify({
            "success": False, 
            "message": "Tinanggihan ng Roblox ang request.", 
            "details": response.text
        }), response.status_code

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
