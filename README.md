# AI Teaching Assistant

A RAG-powered AI teacher with a **unified multi-format ingestion pipeline**. Upload PDFs, audio, video, images, paste YouTube links, or website URLs — everything gets transcribed/extracted, chunked, embedded, and stored for intelligent retrieval-augmented generation with Google Gemini.

## Features

- **Multi-format ingestion** — PDF, DOCX, TXT, MD, MP3, WAV, MP4, AVI, PNG, JPG, and more
- **YouTube ingestion** — Paste a YouTube URL to pull and index the transcript
- **Website scraping** — Paste any URL to extract and index its readable content
- **Audio/video transcription** — Automatic transcription via SpeechRecognition
- **Image OCR** — Extract text from images using Tesseract
- **Chat with context** — Ask questions and get Gemini-powered answers grounded in your material
- **Smart teaching modes** — ELI5, Beginner, Intermediate, Advanced explanations
- **Quiz generation** — Auto-generate MCQs from your material to test understanding
- **Topic filtering** — Organize material by topic and scope queries accordingly
- **Source attribution** — See which documents were used to answer each question

## Architecture

```
                ┌───────────────────────┐
                │    Any Input Source    │
                │ (file/URL/YouTube)    │
                └───────────┬───────────┘
                            ▼
                ┌───────────────────────┐
                │   Format Detector     │
                └───────────┬───────────┘
                            ▼
  ┌──────────┬──────────┬──────────┬──────────┬──────────┐
  │  Audio   │  Video   │ YouTube  │  Image   │ Website  │
  │ Speech   │ffmpeg+   │Transcript│  OCR     │ Scraper  │
  │ Recog.   │ Speech R │  API     │Tesseract │   BS4    │
  └────┬─────┴────┬─────┴────┬─────┴────┬─────┴────┬─────┘
       └──────────┴──────────┴──────────┴──────────┘
                            ▼
                   Clean Unified Text
                            ▼
                     Chunk (400 words)
                            ▼
                  Embed (Gemini embeddings)
                            ▼
                   Store in FAISS Vector DB
                            ▼
              RAG → Gemini → Student Answer
```

### Tech Stack

| Layer | Tools |
|-------|-------|
| Frontend | React 19, Vite, CSS Modules, Lucide icons |
| Backend | FastAPI, Pydantic v2, Python 3.11+ |
| LLM | Google Gemini (gemini-2.0-flash default) |
| Embeddings | Google Gemini text-embedding-004 |
| Vector Store | FAISS (local, file-based) |
| Transcription | SpeechRecognition (Google free) + ffmpeg |
| YouTube | youtube-transcript-api |
| OCR | pytesseract + Pillow |
| Scraping | BeautifulSoup4 + requests |
| Documents | pdfplumber, python-docx |

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+
- A Google Gemini API key (free at https://aistudio.google.com/apikey)
- ffmpeg (for video processing): `brew install ffmpeg`
- Tesseract (for image OCR): `brew install tesseract`

### 1. Clone and configure

```bash
cp .env.example .env
# Edit .env and add your GEMINI_API_KEY
```

### 2. Start the backend

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### 3. Start the frontend

```bash
cd frontend
npm install
npm run dev
```

Open **http://localhost:3000** in your browser.

### 4. Use the app

1. Go to the **Ingest** tab
2. Paste a YouTube link or website URL and click **Ingest**
3. Or drag-and-drop any supported file (PDF, audio, video, image, etc.)
4. Switch to **Chat** and ask questions about the material
5. Try **Quiz** to generate practice questions

## Supported Input Formats

| Category | Extensions / Sources |
|----------|---------------------|
| Text | `.pdf`, `.txt`, `.md`, `.docx` |
| Audio | `.mp3`, `.wav`, `.m4a`, `.ogg`, `.flac` |
| Video | `.mp4`, `.mkv`, `.avi`, `.mov`, `.webm` |
| Image | `.png`, `.jpg`, `.jpeg`, `.bmp`, `.tiff`, `.webp` |
| URL | YouTube video links, any website URL |

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/chat/` | Ask a question (RAG) |
| POST | `/api/upload/` | Upload and ingest a file (any format) |
| POST | `/api/ingest/url` | Ingest from a YouTube or website URL |
| POST | `/api/quiz/` | Generate quiz questions |
| GET | `/api/topics/` | List all indexed topics |
| GET | `/api/health` | Health check + stats |

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `GEMINI_API_KEY` | — | Required. Your Google Gemini API key |
| `CHAT_MODEL` | `gemini-2.0-flash` | Chat completion model |
| `EMBEDDING_MODEL` | `models/text-embedding-004` | Embedding model |
| `CHUNK_SIZE` | `400` | Words per chunk |
| `CHUNK_OVERLAP` | `80` | Overlap words between chunks |
| `TOP_K` | `5` | Number of context chunks retrieved |

## Project Structure

```
AI-Teaching-Assistant/
├── backend/
│   ├── app/
│   │   ├── core/              # Configuration
│   │   ├── models/            # Pydantic schemas
│   │   ├── routers/           # API endpoints
│   │   │   ├── chat.py             # RAG chat
│   │   │   ├── upload.py           # File upload
│   │   │   ├── ingest.py           # URL ingestion
│   │   │   ├── quiz.py             # Quiz generation
│   │   │   └── topics.py           # Topic listing
│   │   └── services/          # Business logic
│   │       ├── chunker.py          # Text chunking
│   │       ├── embeddings.py       # Gemini embeddings
│   │       ├── ingestion.py        # Unified ingestion pipeline
│   │       ├── llm.py              # Gemini integration
│   │       ├── vector_store.py     # FAISS vector DB
│   │       └── processors/         # Format-specific extractors
│   │           ├── transcribe.py        # Audio/video → SpeechRecognition
│   │           ├── youtube.py           # YouTube transcript
│   │           ├── ocr.py              # Image → Tesseract
│   │           ├── scraper.py          # Website → BeautifulSoup
│   │           └── docx_reader.py      # DOCX extraction
│   ├── uploads/               # Uploaded files
│   ├── data/                  # FAISS index storage
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/        # React UI components
│   │   ├── services/          # API client
│   │   └── styles/            # Global CSS
│   └── package.json
├── .env.example
└── README.md
```
