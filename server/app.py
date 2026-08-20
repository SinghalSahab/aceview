import os
import tempfile
import pprint
import fitz  # PyMuPDF
import pandas as pd
import numpy as np
from sqlalchemy import text
from db.db import SessionLocal
from skills.skillExtractor import parse_resume

from fastapi import FastAPI, File, UploadFile, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

app = FastAPI(
    title="AceView Server",
    description="Python FastAPI backend server for AceView handling PDF parsing and text extraction.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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


@app.get("/api/home")
def return_home():
    return {
        "message": "Server is working fine!",
        "status": "OK"
    }


@app.get("/health/db")
def database_health():
    db = SessionLocal()
    try:
        result = db.execute(text("SELECT 1")).scalar()
        return {
            "database": "connected",
            "result": result
        }
    finally:
        db.close()


@app.post("/api/upload")
async def upload_file(file: UploadFile = File(...)):
    if not file.filename:
        return JSONResponse(status_code=400, content={"error": "No selected file"})

    # Save the uploaded PDF temporarily
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp:
        file_path = tmp.name
        contents = await file.read()
        tmp.write(contents)

    try:
        # Extract text using PyMuPDF (fitz)
        doc = fitz.open(file_path)
        text_content = ""
        for page in doc:
            text_content += page.get_text()
            text_content += "\n"
        doc.close()

        # Word-level layout + hyperlink annotations (needed for link resolution)
        layout = _extract_page_layout(file_path)

        # Clean up the temp file
        if os.path.exists(file_path):
            os.remove(file_path)

        # Parse using spaCy skillExtractor
        parsed_details = parse_resume(text_content, layout=layout)

        # Print every detail parsed to the console
        print("\n" + "="*30 + " SPACY PARSED RESUME DETAILS " + "="*30)
        pprint.pprint(parsed_details)
        print("="*89 + "\n")

        validation = parsed_details.get("validation", {})

        # "failed" = no name AND no skills detected
        if validation.get("status") == "failed":
            return JSONResponse(
                status_code=422,
                content={
                    "error": "Resume parsing failed — no name or skills could be detected. "
                             "This usually means the PDF is scanned/image-only or has no "
                             "extractable text. Try a text-based PDF export instead.",
                    "issues": validation.get("issues", []),
                    "text": text_content,
                    "parsed_details": parsed_details
                }
            )

        response_payload = {
            "message": "File parsed successfully"
                        if validation.get("status") == "ok"
                        else "File parsed with warnings",
            "text": text_content,
            "parsed_details": parsed_details
        }
        return response_payload

    except Exception as e:
        if os.path.exists(file_path):
            os.remove(file_path)
        return JSONResponse(status_code=500, content={"error": str(e)})


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8080, reload=True)