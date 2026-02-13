from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime
import os
import random
import re
import time

app = Flask(__name__)
CORS(app)  # allow cross-origin requests for testing


OTP_EXPIRY_SECONDS = int(os.getenv("OTP_EXPIRY_SECONDS", "300"))          # 5 minutes
RESEND_COOLDOWN_SECONDS = int(os.getenv("RESEND_COOLDOWN_SECONDS", "30")) # 30 seconds
MAX_ATTEMPTS = int(os.getenv("MAX_ATTEMPTS", "5"))
RETURN_OTP_IN_RESPONSE = os.getenv("RETURN_OTP_IN_RESPONSE", "true").lower() == "true"

# Assignment-matching OTPs (optional)
USE_PRESET_OTPS = os.getenv("USE_PRESET_OTPS", "true").lower() == "true"
PRESET_OTPS = ["1234", "5678", "7889", "1209"]



def normalize_phone(raw: str) -> str:
    """Keep digits only. Handles +91, spaces, dashes."""
    if raw is None:
        return ""
    digits = re.sub(r"\D+", "", str(raw))
    # If number includes India country code 91 and length > 10, keep last 10 digits
    if len(digits) > 10 and digits.endswith(digits[-10:]):
        digits = digits[-10:]
    return digits

def is_valid_phone(phone: str) -> bool:
    # For your flows, enforce 10 digits (India). If you want 10-15, change regex.
    return bool(re.fullmatch(r"\d{10}", phone or ""))

def normalize_dob(raw: str) -> str:
    """Accepts YYYY-MM-DD, DD-MM-YYYY, DD/MM/YYYY and returns YYYY-MM-DD."""
    if raw is None:
        return ""
    s = str(raw).strip()
    for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y"):
        try:
            dt = datetime.strptime(s, fmt)
            return dt.strftime("%Y-%m-%d")
        except Exception:
            pass
    return ""

def is_valid_dob_iso(dob_iso: str) -> bool:
    try:
        datetime.strptime(dob_iso, "%Y-%m-%d")
        return True
    except Exception:
        return False

def generate_otp() -> str:
    if USE_PRESET_OTPS:
        return random.choice(PRESET_OTPS)
    # 6-digit random
    return "".join(str(random.randint(0, 9)) for _ in range(6))

def api_ok(**kwargs):
    base = {"success": True}
    base.update(kwargs)
    return jsonify(base), 200

def api_err(status_code: int, code: str, message: str, **kwargs):
    base = {"success": False, "error": {"code": code, "message": message}}
    base.update(kwargs)
    return jsonify(base), status_code


@app.get("/health")
def health():
    return api_ok(ok=True)

@app.post("/otp/send")
def otp_send():
    data = request.get_json(silent=True) or {}
    phone = normalize_phone(data.get("phone"))
    dob_iso = normalize_dob(data.get("dob"))

    if not is_valid_phone(phone):
        return api_err(400, "INVALID_PHONE", "Phone must be 10 digits.")
    if not dob_iso or not is_valid_dob_iso(dob_iso):
        return api_err(400, "INVALID_DOB", "DOB must be a valid date (YYYY-MM-DD or DD-MM-YYYY).")

    now = time.time()
    existing = OTP_STORE.get(phone)

    # Cooldown check
    if existing and (now - existing.get("last_sent_at", 0)) < RESEND_COOLDOWN_SECONDS:
        wait = int(RESEND_COOLDOWN_SECONDS - (now - existing.get("last_sent_at", 0)))
        return api_err(
            429, "RESEND_COOLDOWN",
            f"Please wait {wait}s before requesting OTP again.",
            retry_after_seconds=wait
        )

    otp = generate_otp()
    OTP_STORE[phone] = {
        "otp": otp,
        "dob": dob_iso,
        "expires_at": now + OTP_EXPIRY_SECONDS,
        "last_sent_at": now,
        "attempts": 0
    }

    payload = {
        "message": "OTP generated",
        "phone": phone,
        "dob": dob_iso,
        "expires_in_seconds": OTP_EXPIRY_SECONDS
    }

    # For demo/testing in Yellow.ai — keep OTP visible
    if RETURN_OTP_IN_RESPONSE:
        payload["otp"] = otp

    return api_ok(**payload)

@app.post("/otp/verify")
def otp_verify():
    data = request.get_json(silent=True) or {}
    phone = normalize_phone(data.get("phone"))
    otp_in = str(data.get("otp", "")).strip()
    dob_iso = normalize_dob(data.get("dob")) if data.get("dob") else ""

    if not is_valid_phone(phone):
        return api_err(400, "INVALID_PHONE", "Phone must be 10 digits.")
    if not otp_in or not re.fullmatch(r"\d{4,6}", otp_in):
        return api_err(400, "INVALID_OTP", "OTP must be 4 to 6 digits.")

    record = OTP_STORE.get(phone)
    if not record:
        return api_err(404, "OTP_NOT_FOUND", "No OTP requested for this phone.")

    now = time.time()

    if now > record["expires_at"]:
        OTP_STORE.pop(phone, None)
        return api_err(410, "OTP_EXPIRED", "OTP expired. Please request a new OTP.")

    if record["attempts"] >= MAX_ATTEMPTS:
        OTP_STORE.pop(phone, None)
        return api_err(429, "TOO_MANY_ATTEMPTS", "Too many wrong attempts. Request a new OTP.")

    # Optional DOB check (recommended for banking)
    # If dob was provided in verify request, enforce match
    if dob_iso:
        if not is_valid_dob_iso(dob_iso):
            return api_err(400, "INVALID_DOB", "DOB must be valid.")
        if dob_iso != record["dob"]:
            return api_err(401, "DOB_MISMATCH", "DOB does not match the OTP request.")

    if otp_in == record["otp"]:
        OTP_STORE.pop(phone, None)
        return api_ok(message="OTP verified")

    record["attempts"] += 1
    left = MAX_ATTEMPTS - record["attempts"]
    return api_err(401, "OTP_MISMATCH", f"Invalid OTP. Attempts left: {left}", attempts_left=left)


if __name__ == "__main__":

    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "5000")), debug=True)
