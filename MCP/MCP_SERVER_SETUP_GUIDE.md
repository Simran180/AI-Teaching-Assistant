# AI Teaching Assistant MCP Server Setup Guide

## Overview

This MCP (Model Context Protocol) server provides Claude with direct integration to your AI-Teaching-Assistant backend. It enables Claude to:

- **Chat** with the RAG system using different teaching levels
- **Ingest** content from URLs (YouTube, websites, media files)
- **Generate** quiz questions from ingested material
- **Manage** topics and view system status

## Prerequisites

- Python 3.11 or higher
- Your AI-Teaching-Assistant backend running on `http://localhost:8000`
- The MCP server code installed locally

## Installation

### Step 1: Copy the MCP Server File

Copy `ai_teaching_assistant_mcp.py` to your AI-Teaching-Assistant project:

```bash
# From the project root
cp ai_teaching_assistant_mcp.py backend/
```

### Step 2: Install Dependencies

The MCP server uses `httpx` for async HTTP requests. Install it:

```bash
# In the backend directory
pip install httpx "mcp>=0.1.0"
```

Or add to your `requirements.txt`:
```
httpx>=0.24.0
mcp>=0.1.0
pydantic>=2.0.0
```

Then run:
```bash
pip install -r requirements.txt
```

### Step 3: Configure Claude Desktop

Edit your Claude Desktop configuration file at:

**macOS**: `~/.config/Claude/claude_desktop_config.json`

Add the filesystem entry (if not already present) and add the MCP server:

```json
{
  "mcpServers": {
    "filesystem": {
      "command": "npx",
      "args": [
        "-y",
        "@modelcontextprotocol/server-filesystem",
        "/Users/your_username/Documents",
        "/Users/your_username/Desktop",
        "/Users/your_username/Downloads"
      ]
    },
    "ai_teaching_assistant": {
      "command": "python",
      "args": [
        "/path/to/your/project/backend/ai_teaching_assistant_mcp.py"
      ],
      "env": {
        "TEACHING_API_URL": "http://localhost:8000/api"
      }
    }
  }
}
```

**Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "ai_teaching_assistant": {
      "command": "python",
      "args": [
        "C:\\path\\to\\project\\backend\\ai_teaching_assistant_mcp.py"
      ],
      "env": {
        "TEACHING_API_URL": "http://localhost:8000/api"
      }
    }
  }
}
```

### Step 4: Update Path in Config

Replace `/path/to/your/project/` with the actual absolute path to your AI-Teaching-Assistant project.

Example for macOS:
```
/Users/sainis3/Documents/Simran/AI-Teaching-Assistant/backend/ai_teaching_assistant_mcp.py
```

## Running the System

### Terminal 1: Start the Backend

```bash
cd backend
python -m uvicorn app.main:app --reload --port 8000
```

### Terminal 2: Restart Claude Desktop

Close and reopen Claude Desktop (⌘Q and click to reopen on macOS)

### Terminal 3: Use Claude

In Claude Desktop, you can now use the MCP server:

```
I've ingested some material. Can you:
1. Ask me a question about quantum mechanics
2. Generate a 5-question quiz on the basics
3. Show me what topics are available
```

## Available Tools

### 1. **teaching_assistant_chat**

Chat with the RAG system about ingested material.

**Parameters:**
- `question` (required): Your question about the material
- `teaching_level`: Choose from `eli5`, `beginner`, `intermediate`, `advanced` (default: intermediate)
- `topic_filter` (optional): Filter to specific topic
- `include_sources` (optional): Include source documents (default: true)

**Example:**
```
Ask the teaching assistant: "Explain photosynthesis at an ELI5 level"
```

### 2. **teaching_ingest_url**

Ingest content from URLs.

**Parameters:**
- `url` (required): YouTube link, website URL, or media file URL
- `topic` (optional): Topic label for organization
- `description` (optional): Human-readable description

**Example:**
```
Ingest a YouTube video: https://youtube.com/watch?v=...
Topic: Biology
```

### 3. **teaching_generate_quiz**

Generate multiple-choice quiz questions.

**Parameters:**
- `num_questions`: Number of questions (1-20, default: 5)
- `topic_filter` (optional): Generate from specific topic
- `difficulty`: Choose from `easy`, `medium`, `hard` (default: intermediate)

**Example:**
```
Generate 10 hard questions about chapter 3
```

### 4. **teaching_list_topics**

List all topics in the indexed material.

**No parameters needed**

### 5. **teaching_health_check**

Check system health and statistics.

**No parameters needed**

## Environment Variables

Set these in `claude_desktop_config.json` or your shell:

| Variable | Default | Description |
|----------|---------|-------------|
| `TEACHING_API_URL` | `http://localhost:8000/api` | Backend API base URL |

## Troubleshooting

### MCP Server Not Appearing

1. **Check the config file syntax:**
   ```bash
   cat ~/.config/Claude/claude_desktop_config.json
   ```
   Make sure it's valid JSON.

2. **Verify the path is correct:**
   ```bash
   ls -la /path/to/ai_teaching_assistant_mcp.py
   ```

3. **Check for errors in Claude Desktop logs:**
   - macOS: `~/Library/Logs/Claude/claude.log`
   - Check for Python import errors

### "Cannot connect to server" Error

1. **Make sure the backend is running:**
   ```bash
   curl http://localhost:8000/api/health
   ```

2. **Check the API URL in your config matches your actual backend URL**

3. **If using a different port, update `TEACHING_API_URL` in the config**

### Python Module Not Found

1. **Install dependencies:**
   ```bash
   pip install httpx "mcp>=0.1.0"
   ```

2. **Use the correct Python path:**
   ```bash
   which python3
   ```
   Use this path in `claude_desktop_config.json`

## Testing the Server

### Test via Command Line

```bash
# Test health check
python backend/ai_teaching_assistant_mcp.py <<EOF
{"jsonrpc": "2.0", "id": 1, "method": "tools/list"}
EOF
```

### Test with Claude Inspector

```bash
npx @modelcontextprotocol/inspector python /path/to/ai_teaching_assistant_mcp.py
```

## Advanced Configuration

### Using a Remote Backend

If your backend is hosted remotely:

```json
{
  "mcpServers": {
    "ai_teaching_assistant": {
      "command": "python",
      "args": ["..."],
      "env": {
        "TEACHING_API_URL": "https://your-backend.com/api"
      }
    }
  }
}
```

### Custom Timeout

Modify the MCP server code:

```python
REQUEST_TIMEOUT = 60.0  # Increase from 30 seconds
```

Then restart Claude Desktop.

## Performance Notes

- The server maintains async connections for fast response times
- Large quiz generation may take 5-10 seconds
- Source attribution is included by default but can be disabled

## Security

- The MCP server only makes HTTP requests to your configured backend URL
- No API keys are stored in the server code itself
- Add authentication to your backend if exposing it publicly

## Integration with Your Workflow

After setup, you can use Claude to:

1. **Learn from ingested material:**
   ```
   "Summarize the key concepts from the material I ingested"
   ```

2. **Test understanding:**
   ```
   "Generate a hard quiz on this topic and let me work through it"
   ```

3. **Get explanations:**
   ```
   "Explain this concept as if I'm 5, then as an advanced student"
   ```

4. **Organize content:**
   ```
   "What topics have I indexed? Show me the structure"
   ```

## Next Steps

1. ✅ Copy the MCP server file to your project
2. ✅ Install dependencies
3. ✅ Update `claude_desktop_config.json`
4. ✅ Start the backend
5. ✅ Restart Claude Desktop
6. ✅ Start asking questions!

For issues or feedback, check the Claude Desktop logs for detailed error messages.
