# AI Teaching Assistant

A RAG-powered AI teacher with a **unified multi-format ingestion pipeline**. Upload PDFs, audio, video, images, paste YouTube links, or website URLs — everything gets transcribed/extracted, chunked, embedded, and stored for intelligent retrieval-augmented generation with Google Gemini.

- **App:** _add your Vercel URL here_
- **API:** _add your Render URL here_


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

```mermaid
flowchart TD
    A[Any Input Source<br/>file / URL / YouTube] --> B[Format Detector]
    B --> C1[Audio<br/>SpeechRecognition]
    B --> C2[Video<br/>ffmpeg + SpeechRecognition]
    B --> C3[YouTube<br/>youtube-transcript-api]
    B --> C4[Image<br/>Tesseract OCR]
    B --> C5[Website<br/>BeautifulSoup4]
    B --> C6[Document<br/>pdfplumber / docx]
    C1 --> D[Clean Unified Text]
    C2 --> D
    C3 --> D
    C4 --> D
    C5 --> D
    C6 --> D
    D --> E[Chunker<br/>400 words, 80 overlap]
    E --> F[Gemini Embeddings<br/>text-embedding-004]
    F --> G[(FAISS Vector Store<br/>local index file)]
    H[User Question] --> I[Embed Query]
    I --> G
    G -- top-K chunks --> J[Build RAG Prompt]
    J --> K[Gemini 2.0 Flash]
    K --> L[Answer + Source Attribution]
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

## Benchmarks & Evaluation

This project ships with a reproducible eval harness in [`backend/evals/`](backend/evals/README.md) that measures retrieval quality on a curated golden set.

To reproduce:

```bash
cd backend
python -m evals.run_eval --baseline           # retrieval metrics, no LLM call
python -m evals.run_eval --sweep-chunks       # chunk-size ablation
python -m evals.run_eval --sweep-topk         # top-K ablation
python -m evals.run_eval --baseline --end-to-end   # full RAG including Gemini
```

### Baseline (top_k=5, chunk=400, overlap=80)

Measured on the curated 15-question golden set in [`backend/evals/datasets/`](backend/evals/datasets/). Re-run `python -m evals.run_eval --baseline` to reproduce.

| Metric | Value |
|--------|-------|
| Recall@5 (source) | 0.667 |
| MRR (source)      | 0.478 |
| Precision@5       | 0.333 |
| Retrieval P95     | 721 ms |
| Chunks indexed    | 6 (3 docs) |

### Chunk-size ablation

| chunk_size | overlap | chunks indexed | recall@5 | MRR | P95 ms |
|-----------:|--------:|---------------:|---------:|----:|-------:|
| 200 | 40  | 9 | 0.333 | 0.333 | 629 |
| 400 | 80  | 6 | 0.667 | 0.478 | 721 |
| 800 | 160 | 3 | 1.000 | 1.000 | 550 |

### Top-K ablation (chunk=400)

| top_k | recall@k | MRR | precision@k | P95 ms |
|------:|---------:|----:|------------:|-------:|
| 1  | 0.333 | 0.333 | 0.333 | 656 |
| 3  | 0.667 | 0.478 | 0.333 | 570 |
| 5  | 0.667 | 0.478 | 0.333 | 614 |
| 10 | 0.667 | 0.478 | 0.333 | 545 |

**Result:** Tuned `TOP_K` from 5 → 3 (same recall, smaller and less noisy LLM context).
Kept `CHUNK_SIZE=400` — the chunk=800 "win" is a corpus-size artifact, not a real tuning improvement.

### What we measure and why

See [`backend/evals/README.md`](backend/evals/README.md) for the metric definitions, the golden set, and the honest caveats.

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
| `RATE_LIMIT_CHAT` | `5/minute` | Per-IP rate limit on `POST /api/chat/` |
| `RATE_LIMIT_QUIZ` | `2/minute` | Per-IP rate limit on `POST /api/quiz/` |
| `RATE_LIMIT_UPLOAD` | `5/minute` | Per-IP rate limit on `POST /api/upload/` |
| `RATE_LIMIT_INGEST` | `15/minute` | Per-IP rate limit on `POST /api/ingest/url` |

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
│   ├── evals/                 # RAG evaluation harness (golden set, metrics, runner)
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
