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


def _extract_page_layout(pdf_path):
    """
    Extract word-level text layout and hyperlink annotations per page.

    This exists because resume PDFs almost always embed URLs as invisible
    link annotations behind short visible anchor text (e.g. the word
    "GitHub" or "Live"), not as literal visible URL text — plain
    page.get_text() extraction cannot see these links at all, which is why
    link extraction was previously always empty. page.get_links() is the
    only way to retrieve them, and word-level bounding boxes are needed
    alongside them so skillExtractor can figure out (a) which visible word
    each link sits behind, and (b) which resume section/project the link
    belongs to, purely from vertical position on the page.

    y-coordinates are offset by a running total of previous pages' heights
    so positions stay monotonically increasing across a multi-page resume,
    which is what lets skillExtractor compare positions across pages with
    simple less-than/greater-than checks.
    """
    doc = fitz.open(pdf_path)
    pages = []
    y_offset = 0.0

    for page_index, page in enumerate(doc):
        words = page.get_text("words")  # (x0,y0,x1,y1,word,block_no,line_no,word_no)
        word_entries = [
            {
                "text": w[4],
                "x0": w[0], "x1": w[2],
                "y0": w[1] + y_offset, "y1": w[3] + y_offset,
                "block": w[5], "line": w[6], "word_no": w[7],
                "page": page_index,
            }
            for w in words
        ]

        link_entries = []
        for link in page.get_links():
            if link.get("kind") == fitz.LINK_URI and link.get("uri"):
                rect = link["from"]
                link_entries.append({
                    "uri": link["uri"],
                    "x0": rect.x0, "x1": rect.x1,
                    "y0": rect.y0 + y_offset, "y1": rect.y1 + y_offset,
                })

        pages.append({"words": word_entries, "links": link_entries})
        y_offset += page.rect.height

    doc.close()
    return pages


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
        doc.close()

        # Word-level layout + hyperlink annotations (needed for link resolution)
        layout = _extract_page_layout(file_path)

        # Clean up the temp file
        os.remove(file_path)

        # Parse using spaCy skillExtractor
        parsed_details = parse_resume(text, layout=layout)

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