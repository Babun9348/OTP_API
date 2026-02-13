from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import random
import time

app = Flask(__name__)
CORS(app)

PRESET_OTPS = ["1234", "5678", "7889", "1209"]
OTP_STORE = {}

OTP_EXPIRY_SECONDS = int(os.getenv("OTP_EXPIRY_SECONDS", "300"))

def ok(**kwargs):
    payload = {"success": True}
    payload.update(kwargs)
    return jsonify(payload), 200

def err(code, message, status=400, **kwargs):
    payload = {"success": False, "error": {"code": code, "message": message}}
    payload.update(kwargs)
    return jsonify(payload), status


@app.get("/health")
def health():
    return ok(ok=True)


@app.post("/otp/send")
def send_otp():
    data = request.get_json(silent=True) or {}
    phone = str(data.get("phone", "")).strip()
    dob = str(data.get("dob", "")).strip()

    if not phone or len(phone) < 10:
        return err("INVALID_PHONE", "Phone is required (min 10 digits).", 400)
    if not dob:
        return err("INVALID_DOB", "DOB is required.", 400)

    otp = random.choice(PRESET_OTPS)
    OTP_STORE[phone] = {"otp": otp, "expires_at": time.time() + OTP_EXPIRY_SECONDS}

    return ok(
        message="OTP generated",
        phone=phone,
        dob=dob,
        otp=otp,
        expires_in_seconds=OTP_EXPIRY_SECONDS
    )


@app.post("/otp/verify")
def verify_otp():
    data = request.get_json(silent=True) or {}
    phone = str(data.get("phone", "")).strip()
    otp_in = str(data.get("otp", "")).strip()

    rec = OTP_STORE.get(phone)
    if not rec:
        return err("OTP_NOT_FOUND", "No OTP requested for this phone.", 404)

    if time.time() > rec["expires_at"]:
        OTP_STORE.pop(phone, None)
        return err("OTP_EXPIRED", "OTP expired. Please request again.", 410)

    if otp_in == rec["otp"]:
        OTP_STORE.pop(phone, None)
        return ok(message="OTP verified")

    return err("OTP_MISMATCH", "Invalid OTP.", 401)


@app.get("/loans/accounts")
def loan_accounts():
    data = request.get_json(silent=True) or {}
    phone = str(data.get("phone", "")).strip()
    dob = str(data.get("dob", "")).strip()
    full = bool(data.get("full", False))

    if not phone or not dob:
        return err("AUTH_REQUIRED", "phone and dob are required.", 401)

    accounts_min = [
        {"loan_account_id": "LA1001", "loan_type": "Home Loan", "tenure": "120 months"},
        {"loan_account_id": "LA2002", "loan_type": "Personal Loan", "tenure": "36 months"}
    ]

    if not full:
        return ok(accounts=accounts_min)
    accounts_big = []
    for a in accounts_min:
        big = {
            **a,
            "internal_bank_code": "YB-INT-0091",
            "audit_date": "2026-02-13",
            "branch_code": "BR001",
            "customer_segment": "Retail",
            "risk_bucket": "R2",
            "co_borrower": None,
            "disbursement_date": "2022-05-15",
            "last_payment_date": "2026-01-10",
            "emi_amount": "14500",
            "emi_due_date": "10",
            "currency": "INR",
            "status": "ACTIVE",
            "product_code": "PRD-LOAN-01",
            "source_system": "COREBANK",
            "extra_notes": "demo-field"
        }
        accounts_big.append(big)

    return ok(accounts=accounts_big)


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
        return ok(loan_account_id=loan_id, **data[loan_id])

    return err("LOAN_NOT_FOUND", "Loan not found.", 404)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")))


