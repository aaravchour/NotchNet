from flask import Flask, request, jsonify  # type: ignore
from flask_limiter import Limiter  # type: ignore
from flask_limiter.util import get_remote_address  # type: ignore
from rag_pipeline import generate_answer
import multiprocessing
import os
import time
import secrets

API_KEY = os.environ.get("CHATBOT_API_KEY")

app = Flask(__name__)

limiter = Limiter(get_remote_address, app=app, default_limits=["10 per minute"])


issued_tokens = {}

TOKEN_TTL = 600


def is_valid_api_key():
    client_key = request.headers.get("X-API-Key")
    return client_key == API_KEY


def is_valid_temp_token(token):
    now = time.time()
    # purge expired
    expired = [t for t, exp in issued_tokens.items() if exp < now]
    for t in expired:
        issued_tokens.pop(t, None)
    # check current token
    return token in issued_tokens and issued_tokens[token] > now


@app.route("/get_token", methods=["POST"])
def get_token():
    """Client (the mod) calls this with the real API key once to get a temp token."""
    if not is_valid_api_key():
        return jsonify({"error": "Unauthorized – invalid or missing API key"}), 401

    temp_token = secrets.token_urlsafe(32)
    issued_tokens[temp_token] = time.time() + TOKEN_TTL
    return jsonify({"token": temp_token, "expires_in": TOKEN_TTL})


@app.route("/ask", methods=["POST"])
@limiter.limit("10 per minute")
def ask_question():
    auth = request.headers.get("Authorization", "")
    token = auth.removeprefix("Bearer ").strip()

    if not token or not is_valid_temp_token(token):
        return jsonify({"error": "Unauthorized – invalid or expired token"}), 401

    data = request.get_json()
    if not data or "question" not in data:
        return jsonify({"error": "Missing 'question' field"}), 400

    try:
        answer = generate_answer(data["question"])
        return jsonify({"answer": answer})
    except Exception as e:
        import traceback

        traceback.print_exc()
        return jsonify({"error": "Server error", "details": str(e)}), 500


if __name__ == "__main__":
    multiprocessing.set_start_method("spawn", force=True)
    app.run(host="0.0.0.0", port=8000, debug=False)
