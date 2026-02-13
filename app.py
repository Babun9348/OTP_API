from flask import Flask, request, jsonify
from flask_cors import CORS
import random

app = Flask(__name__)
CORS(app)


PRESET_OTPS = ["1234", "5678", "7889", "1209"]


@app.post("/otp/send")
def send_otp():
    otp = random.choice(PRESET_OTPS)
    return jsonify({
        "success": True,
        "otp": otp
    })


@app.get("/loans/accounts")
def loan_accounts():
    return jsonify({
        "success": True,
        "accounts": [
            {
                "loan_account_id": "LA1001",
                "loan_type": "Home Loan",
                "tenure": "120 months"
            },
            {
                "loan_account_id": "LA2002",
                "loan_type": "Personal Loan",
                "tenure": "36 months"
            }
        ]
    })


@app.get("/loans/details/<loan_id>")
def loan_details(loan_id):

    data = {
        "LA1001": {
            "tenure": "120 months",
            "interest_rate": "8.5%",
            "principal_pending": "450000",
            "interest_pending": "12000",
            "nominee": "Father"
        },
        "LA2002": {
            "tenure": "36 months",
            "interest_rate": "12%",
            "principal_pending": "150000",
            "interest_pending": "6000",
            "nominee": "Mother"
        }
    }

    if loan_id in data:
        return jsonify({"success": True, **data[loan_id]})
    else:
        return jsonify({"success": False, "message": "Loan not found"}), 404


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)

