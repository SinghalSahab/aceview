# AceView Python FastAPI Server ⚡

This directory contains the Python FastAPI backend server for AceView, which handles PDF parsing and text extraction.

For complete project documentation, overview, and setup guides, please refer to the main [Root README](../README.md).

## Quick Start (Backend)

1. **Set up virtual environment**:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Run the server**:
   ```bash
   python app.py
   # or
   uvicorn app:app --port 8080 --reload
   ```
   The backend runs on port 8080 by default. Interactive API documentation is available at `http://localhost:8080/docs`.

