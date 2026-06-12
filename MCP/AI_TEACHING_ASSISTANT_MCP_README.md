# AI Teaching Assistant MCP Server

## Overview

This is a **Model Context Protocol (MCP) server** for your AI-Teaching-Assistant project. It enables Claude (or any MCP-compatible client) to directly interact with your RAG-powered teaching system.

The MCP server bridges Claude and your backend, providing seamless integration for:
- 🎓 Intelligent chatting with RAG context
- 📚 Multi-format content ingestion (YouTube, websites, files)
- 🧪 Automatic quiz generation
- 🏷️ Topic management and filtering
- 📊 System health monitoring

## Architecture

```
┌─────────────────────────────────────┐
│      Claude Desktop / claude.ai      │
└──────────────┬──────────────────────┘
               │ MCP Protocol (stdio/HTTP)
               ▼
┌─────────────────────────────────────┐
│  ai_teaching_assistant_mcp.py       │
│                                      │
│  • Chat Tool                         │
│  • Ingestion Tool                    │
│  • Quiz Generation Tool              │
│  • Topic Management Tool             │
│  • Health Check Tool                 │
└──────────────┬──────────────────────┘
               │ HTTP Requests
               ▼
┌─────────────────────────────────────┐
│    FastAPI Backend (port 8000)       │
│                                      │
│  • RAG Chat Endpoint                 │
│  • URL Ingestion                     │
│  • Quiz Generation                   │
│  • FAISS Vector Store                │
│  • Gemini Integration                │
└─────────────────────────────────────┘
```

## Features

### 1. Intelligent Chat with Context

Ask questions about ingested material with RAG-powered responses grounded in your documents.

```python
# Tool: teaching_assistant_chat
question="What is photosynthesis?"
teaching_level="beginner"  # eli5, beginner, intermediate, advanced
topic_filter="biology"     # Optional: filter to specific topic
include_sources=True       # Include source attribution
```

**Returns:**
- Contextually relevant answer
- Source document citations with relevance scores
- Teaching level-appropriate explanations

### 2. Multi-Format Content Ingestion

Ingest content from virtually any source:

```python
# Tool: teaching_ingest_url
url="https://youtube.com/watch?v=..."  # YouTube video
topic="machine-learning"               # Optional topic label
description="ML basics tutorial"       # Optional description
```

**Supported formats:**
- YouTube videos (auto-transcript extraction)
- Websites (HTML scraping)
- Audio files (.mp3, .wav, .m4a, .ogg, .flac)
- Video files (.mp4, .mkv, .avi, .mov, .webm)
- Image files (.png, .jpg, .jpeg, .webp, .bmp, .tiff)
- Documents (.pdf, .txt, .md, .docx)

### 3. Quiz Generation

Auto-generate quiz questions from ingested material:

```python
# Tool: teaching_generate_quiz
num_questions=10           # 1-20 questions
difficulty="medium"       # easy, medium, hard
topic_filter="chapter-2" # Optional: specific topic
```

**Returns:**
- Multiple-choice format questions
- Difficulty-appropriate content
- Ready-to-use assessment format

### 4. Topic Organization

See all indexed topics and filter queries by topic:

```python
# Tool: teaching_list_topics
# Returns: All topics that have been indexed
# Use with topic_filter in other tools
```

### 5. System Health Monitoring

Check system status and statistics:

```python
# Tool: teaching_health_check
# Returns:
# - System status (ok/error)
# - Total indexed chunks
# - Available topics
# - Processing statistics
```

## Installation

### Step 1: Install Dependencies

```bash
# From your project root
cd backend
pip install -r requirements.txt

# Add MCP dependencies
pip install httpx "mcp>=0.1.0"
```

### Step 2: Configure Claude Desktop

Edit `~/.config/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "ai_teaching_assistant": {
      "command": "python",
      "args": [
        "/path/to/AI-Teaching-Assistant/backend/ai_teaching_assistant_mcp.py"
      ],
      "env": {
        "TEACHING_API_URL": "http://localhost:8000/api"
      }
    }
  }
}
```

Replace `/path/to/` with the actual absolute path.

### Step 3: Start Services

**Terminal 1: Backend**
```bash
cd backend
python -m uvicorn app.main:app --reload --port 8000
```

**Terminal 2: Restart Claude Desktop**
```bash
# Close: ⌘Q
# Reopen Claude Desktop
```

### Step 4: Verify Setup

In Claude, you should see the teaching assistant tools available. Try:
```
Check the health of the teaching assistant system
```

## Tool Reference

### teaching_assistant_chat

**Purpose:** Query the RAG system about ingested material

**Input Schema:**
```json
{
  "question": "string (required)",
  "teaching_level": "eli5 | beginner | intermediate | advanced (default: intermediate)",
  "topic_filter": "string (optional)",
  "include_sources": "boolean (default: true)"
}
```

**Output:** 
Formatted response with:
- Answer text
- Source attributions with relevance scores
- Teaching notes (if applicable)

**Example:**
```
Question: "Explain quantum entanglement"
Teaching Level: "advanced"
Topic Filter: "quantum-physics"
```

---

### teaching_ingest_url

**Purpose:** Ingest content from URLs (YouTube, websites, media files)

**Input Schema:**
```json
{
  "url": "string (required, http/https/ftp)",
  "topic": "string (optional)",
  "description": "string (optional)"
}
```

**Output:**
- Content type detected
- Number of chunks created
- Tokens processed
- Source document reference

**Example:**
```
URL: "https://youtube.com/watch?v=dQw4w9WgXcQ"
Topic: "music-theory"
Description: "Introduction to basic chord progressions"
```

---

### teaching_generate_quiz

**Purpose:** Generate multiple-choice quiz questions

**Input Schema:**
```json
{
  "num_questions": "integer 1-20 (default: 5)",
  "difficulty": "easy | medium | hard (default: medium)",
  "topic_filter": "string (optional)"
}
```

**Output:**
- Multiple-choice format questions
- A, B, C, D options
- Ready to present to students

**Example:**
```
Num Questions: 10
Difficulty: "hard"
Topic Filter: "cell-biology"
```

---

### teaching_list_topics

**Purpose:** List all indexed topics

**Input Schema:** (none)

**Output:**
- List of all topics
- Count of topics
- Usage guidance

**Example:**
```
Returns: ["biology", "physics", "chapter-1", "video-lectures", ...]
```

---

### teaching_health_check

**Purpose:** Check system health and statistics

**Input Schema:** (none)

**Output:**
- System status
- Total chunks indexed
- Available topics list
- Timestamp

## Configuration

### Environment Variables

| Variable | Default | Purpose |
|----------|---------|---------|
| `TEACHING_API_URL` | `http://localhost:8000/api` | Backend API endpoint |

Set in `claude_desktop_config.json` `env` section.

### Customization

**Change request timeout:**
```python
# In ai_teaching_assistant_mcp.py
REQUEST_TIMEOUT = 60.0  # Increase from 30s
```

**Change API URL:**
```json
{
  "env": {
    "TEACHING_API_URL": "https://your-api.com/api"
  }
}
```

**Add authentication:**
Modify the `_make_request` function to include headers:
```python
headers = {
    "Authorization": f"Bearer {api_key}"
}
```

## Usage Examples

### Example 1: Learn from a YouTube Video

```
User: "Please ingest this video: https://youtube.com/watch?v=..."
AI: [Uses teaching_ingest_url tool]
AI: "✅ Content Successfully Ingested
    Content Type: YouTube Video
    Chunks Created: 24
    Tokens Processed: 5,432"

User: "Now explain the main concept at an ELI5 level"
AI: [Uses teaching_assistant_chat tool]
AI: "The main concept is... [simplified explanation]
    Sources: Video transcript (Relevance: 98%)"
```

### Example 2: Test Understanding with a Quiz

```
User: "Generate 5 medium-difficulty quiz questions about the video"
AI: [Uses teaching_generate_quiz tool]
AI: "Quiz (5 Questions)
    Question 1: What is...?
    A) Option 1
    B) Option 2
    C) Option 3
    D) Option 4
    ..."

User: "I think the answer to Q1 is C"
AI: "That's correct! [Explanation]"
```

### Example 3: Organize Multiple Topics

```
User: "What topics have I indexed?"
AI: [Uses teaching_list_topics tool]
AI: "Available Topics (8)
    - machine-learning
    - neural-networks
    - python-basics
    - data-science
    - chapter-1
    - chapter-2
    - video-lectures
    - research-papers"

User: "Generate a quiz only about neural-networks"
AI: [Uses teaching_generate_quiz with topic_filter]
```

## Troubleshooting

### "Tool not found" or "Connection refused"

**Problem:** MCP server not running or not configured correctly

**Solution:**
1. Check config file syntax: `cat ~/.config/Claude/claude_desktop_config.json`
2. Verify path is correct: `ls -la /path/to/ai_teaching_assistant_mcp.py`
3. Restart Claude Desktop completely

### "Cannot connect to server at http://localhost:8000/api"

**Problem:** Backend API is not running

**Solution:**
1. Start backend in a terminal: `cd backend && python -m uvicorn app.main:app --reload --port 8000`
2. Test connection: `curl http://localhost:8000/api/health`
3. If using different port, update `TEACHING_API_URL` in config

### "ModuleNotFoundError: No module named 'mcp'"

**Problem:** MCP dependencies not installed

**Solution:**
```bash
pip install httpx "mcp>=0.1.0"
# Or in the backend directory:
pip install -r requirements.txt
```

### Slow responses or timeouts

**Problem:** Long-running operations timing out

**Solution:**
1. Increase timeout in the MCP server code: `REQUEST_TIMEOUT = 60.0`
2. Check backend logs for errors
3. Verify network connectivity

## Advanced Usage

### Streaming Responses (Future)

The MCP server can be extended to support streaming responses for long operations:

```python
@mcp.tool()
async def chat_streaming(params: ChatInput, ctx: Context) -> str:
    async with ctx.report_progress() as progress:
        await progress.update(0.25, "Retrieving context...")
        # ... API call
        await progress.update(0.75, "Generating response...")
        # ... processing
```

### Custom Prompt Instructions

Add to your Claude Desktop profile in Settings:

```
You have access to the AI Teaching Assistant MCP server.
When helping students:
- Use appropriate teaching levels based on their level
- Always cite sources
- Generate quizzes to test understanding
- Organize content by topics
```

### Batch Operations

The MCP server can handle multiple sequential operations:

1. Ingest multiple URLs
2. Generate quizzes on different topics
3. Chat about different subjects
4. All within a single Claude conversation

## Performance Notes

- **Chat responses:** 1-3 seconds (includes RAG retrieval)
- **URL ingestion:** 5-30 seconds (depends on content size)
- **Quiz generation:** 5-10 seconds (multiple LLM calls)
- **Health check:** <1 second

## Security Considerations

- MCP server only communicates with your backend
- No API keys are hardcoded in the server
- Add authentication headers if backend is exposed
- Keep Claude Desktop updated for security patches

## Development & Extension

### Adding New Tools

1. Create new Pydantic model for inputs
2. Define tool function with `@mcp.tool` decorator
3. Add error handling with `_handle_api_error`
4. Document in docstring

Example:
```python
@mcp.tool()
async def teaching_get_statistics(params: StatsInput) -> str:
    """Get detailed statistics about ingested material."""
    try:
        response = await _make_request("GET", "/stats/", params=params.model_dump())
        return format_stats(response)
    except Exception as e:
        return _handle_api_error(e, "statistics")
```

### Testing Locally

```bash
# Test with MCP Inspector
npx @modelcontextprotocol/inspector python /path/to/ai_teaching_assistant_mcp.py
```

## Project Structure

```
AI-Teaching-Assistant/
├── backend/
│   ├── ai_teaching_assistant_mcp.py  ← MCP Server
│   ├── app/
│   │   ├── main.py
│   │   ├── routers/
│   │   │   ├── chat.py
│   │   │   ├── ingest.py
│   │   │   ├── quiz.py
│   │   │   └── topics.py
│   │   └── services/
│   ├── requirements.txt
│   └── ...
├── frontend/
└── ...
```

## Links

- [MCP Protocol Documentation](https://modelcontextprotocol.io/)
- [Claude Desktop Setup](https://claude.ai/download)
- [Your Backend API Docs](http://localhost:8000/docs) (when running)

## Support

For issues:

1. Check Claude Desktop logs: `~/Library/Logs/Claude/claude.log`
2. Verify backend is running: `curl http://localhost:8000/api/health`
3. Test MCP server: `npx @modelcontextprotocol/inspector python ai_teaching_assistant_mcp.py`

---

**Created:** May 2026  
**Version:** 1.0.0  
**Compatibility:** Python 3.11+, Claude Desktop 2025+
