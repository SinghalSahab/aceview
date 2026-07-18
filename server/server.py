from flask import Flask, jsonify, request
from flask_cors import CORS
import fitz  # PyMuPDF
import os
import tempfile
import pandas as pd
import numpy as np
import pprint
from skillExtractor import parse_resume

app = Flask(__name__)
CORS(app)

@app.route("/api/home", methods=['GET'])
def return_home():
    return jsonify({
        'message': "Server is working fine!",
        'status': 'OK'
    })

@app.route("/api/upload", methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400
    
    file = request.files['file']
    
    # Check filename
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    # Save the uploaded PDF temporarily
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        file_path = tmp.name
        file.save(file_path)

    try:
        # Extract text using PyMuPDF (fitz)
        doc = fitz.open(file_path)
        text = ""
        for page in doc:
            text += page.get_text()
            text += "\n"

        # Clean up the temp file
        os.remove(file_path)

        # Parse using spaCy skillExtractor
        parsed_details = parse_resume(text)

        # Print every detail parsed to the console
        print("\n" + "="*30 + " SPACY PARSED RESUME DETAILS " + "="*30)
        pprint.pprint(parsed_details)
        print("="*89 + "\n")

        validation = parsed_details.get("validation", {})

        # "failed" = no name AND no skills detected — almost certainly a
        # parsing failure (e.g. scanned/image-only PDF), so reject rather
        # than silently passing an unusable profile downstream.
        if validation.get("status") == "failed":
            return jsonify({
                "error": "Resume parsing failed — no name or skills could be detected. "
                         "This usually means the PDF is scanned/image-only or has no "
                         "extractable text. Try a text-based PDF export instead.",
                "issues": validation.get("issues", []),
                "text": text,
                "parsed_details": parsed_details
            }), 422

        # "flagged" = parsed, but something looks thin (e.g. no email) —
        # still returned as a usable profile, with the issues surfaced so
        # the frontend can show a warning instead of pretending it's perfect.
        response_payload = {
            "message": "File parsed successfully"
                        if validation.get("status") == "ok"
                        else "File parsed with warnings",
            "text": text,
            "parsed_details": parsed_details
        }
        return jsonify(response_payload)

    except Exception as e:
        # Best-effort cleanup if we failed before os.remove() above
        if os.path.exists(file_path):
            os.remove(file_path)
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True, port=8080)