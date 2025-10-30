from flask import Flask, request, jsonify  # type: ignore
from flask_limiter import Limiter  # type: ignore
from flask_limiter.util import get_remote_address  # type: ignore
from rag_pipeline import generate_answer
import multiprocessing
import os

API_KEY = os.environ.get("CHATBOT_API_KEY")

app = Flask(__name__)

limiter = Limiter(get_remote_address, app=app, default_limits=["10 per minute"])


def is_valid_api_key():
    client_key = request.headers.get("X-API-Key")
    return client_key == API_KEY


@app.route("/ask", methods=["POST"])
@limiter.limit("10 per minute")
def ask_question():
    if not is_valid_api_key():
        return jsonify({"error": "Unauthorized – Invalid or missing API key"}), 401

    data = request.get_json()
    if not data or "question" not in data:
        return jsonify({"error": "Missing 'question' field in request"}), 400

    try:
        answer = generate_answer(data["question"])
        return jsonify({"answer": answer})
    except Exception as e:
        import traceback

        print("⚠️ Error occurred:")
        traceback.print_exc()
        return jsonify({"error": "Server error", "details": str(e)}), 500


if __name__ == "__main__":
    multiprocessing.set_start_method("spawn", force=True)
    app.run(host="0.0.0.0", port=8000, debug=False)
