from flask import Flask, jsonify, request
from flask_cors import CORS
import fitz  # PyMuPDF
import os
import tempfile

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
            text+="/n"
            text+="Links on this page:/n"
            

        # Clean up the temp file
        os.remove(file_path)

        # Return extracted text
        return jsonify({
            "message": "File parsed successfully",
            "text": text
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True, port=8080)
