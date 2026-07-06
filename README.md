# AceView 🚀

AceView is an AI-powered mock interview practice, feedback, and document analysis platform. It provides candidates with a realistic chat-based mock interview environment for both technical and non-technical roles, qualitative performance feedback, and Retrieval-Augmented Generation (RAG) capabilities to chat with uploaded resumes and preparation documents (PDFs).

---

## 🏗️ Project Structure

The project is organized as a monorepo with separate frontend and backend directories:

```
aceview/
├── client/          # Next.js 15 frontend application
│   ├── app/         # App router containing dashboard, rag, and page views
│   ├── components/  # Reusable React components (Dropzone, Chat, etc.)
│   ├── constants/   # App constants, mock data, and AI schemas
│   ├── prisma/      # Database schema definitions (MongoDB integration)
│   └── public/      # Static assets (images, icons, etc.)
└── server/          # Python Flask backend server
    └── server.py    # Main server entrypoint (PDF parser & test endpoints)
```

---

## 🌟 Key Features

1. **AI-Ready Mock Interviews Dashboard**
   - Clean, modern dashboard interface detailing past interview performance (e.g., scores, dates, qualitative summaries).
   - Predefined templates for top companies across technical and behavioral domains (HackerRank, Facebook, Spotify, Adobe, TikTok, etc.).
   - Expandable conversational logic for voice/text integration using LLMs and agentic flows.

2. **Resume & Preparation Document RAG (PDF Chat)**
   - Drag-and-drop file upload zone supporting PDFs up to 10MB.
   - Real-time text extraction on the Flask server.
   - Interactive document-guided chat components.

3. **Modern Styling & Premium UI**
   - High-fidelity dark mode interface.
   - Smooth glassmorphism design accents.
   - Interactive hover micro-animations and custom responsive card grids.

---

## 🛠️ Tech Stack

### Frontend
- **Framework**: Next.js 15 (App Router) & React 19
- **Languages**: TypeScript, JavaScript
- **Styling**: Tailwind CSS, Material UI (MUI), Lucide React Icons
- **Database ORM**: Prisma (configured for MongoDB)
- **Authentication**: Clerk Auth
- **File Uploads**: UploadThing & React Dropzone

### Backend
- **Framework**: Flask (Python 3) & Flask-CORS
- **PDF Extraction**: PyMuPDF (`fitz`)

---

## 🚀 Getting Started

Follow the steps below to set up and run both client and server applications.

### 1. Prerequisites
- **Node.js** (v18.x or later)
- **Python** (3.8 or later)
- **MongoDB** instance (local or Atlas)

---

### 2. Backend Setup (`server/`)

1. Navigate to the server folder:
   ```bash
   cd server
   ```

2. Create and activate a Python virtual environment:
   ```bash
   # Create venv
   python3 -m venv venv
   
   # Activate venv (macOS/Linux)
   source venv/bin/activate
   
   # Activate venv (Windows)
   venv\Scripts\activate
   ```

3. Install required packages:
   ```bash
   pip install Flask flask-cors PyMuPDF
   ```

4. Run the Flask development server:
   ```bash
   python server.py
   ```
   The backend will start running on **`http://localhost:8080`**.

---

### 3. Frontend Setup (`client/`)

1. Navigate to the client folder:
   ```bash
   cd client
   ```

2. Install the dependencies:
   ```bash
   npm install
   ```

3. Configure your Environment Variables:
   Create a `.env` file in the `client/` root directory (refer to `.env.example` below). You will need Clerk, UploadThing, and MongoDB connection keys.

4. Generate the Prisma Client:
   ```bash
   npx prisma generate
   ```

5. Run the local development server:
   ```bash
   npm run dev
   ```
   Open **`http://localhost:3000`** in your browser to view the application.

---

### 📋 Environment Variables Template (`client/.env`)

Ensure the following variables are defined in your `client/.env` file:

```env
# MongoDB Connection string
DATABASE_URL="mongodb://localhost:27017/aceview"

# Clerk Authentication Keys
NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY=your_clerk_publishable_key
CLERK_SECRET_KEY=your_clerk_secret_key

# UploadThing Token
UPLOADTHING_TOKEN=your_uploadthing_token
```

---

## 🤝 Future Enhancements
- Fully enable Vapi AI conversational assistant integration for live voice-based mock interviews.
- Integrate automated scoring systems based on candidate responses.
- Store conversation logs and results in MongoDB via Prisma.
