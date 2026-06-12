# AI Teaching Assistant MCP Server - Quick Reference

## Installation Checklist

- [ ] Copy `ai_teaching_assistant_mcp.py` to `backend/` folder
- [ ] Install dependencies: `pip install httpx "mcp>=0.1.0"`
- [ ] Edit `~/.config/Claude/claude_desktop_config.json`
- [ ] Update the path in the config to absolute path
- [ ] Start backend: `python -m uvicorn app.main:app --reload --port 8000`
- [ ] Restart Claude Desktop (⌘Q and reopen)
- [ ] Test with: "Check the health of the teaching assistant"

## claude_desktop_config.json Template

```json
{
  "mcpServers": {
    "ai_teaching_assistant": {
      "command": "python",
      "args": [
        "/Users/YOUR_USERNAME/Documents/Simran/AI-Teaching-Assistant/backend/ai_teaching_assistant_mcp.py"
      ],
      "env": {
        "TEACHING_API_URL": "http://localhost:8000/api"
      }
    }
  }
}
```

**Replace:** `/Users/YOUR_USERNAME/Documents/Simran/` with your actual path

## Available Tools in Claude

### 1️⃣ teaching_assistant_chat
```
Ask questions about your ingested material

Claude: "Explain photosynthesis in ELI5 style"

Parameters:
- question: Your question
- teaching_level: eli5 | beginner | intermediate | advanced
- topic_filter: (optional) Specific topic
- include_sources: true | false
```

### 2️⃣ teaching_ingest_url
```
Add content from YouTube, websites, or media files

Claude: "Ingest this video: https://youtube.com/watch?v=..."

Parameters:
- url: The URL to ingest
- topic: (optional) Topic label
- description: (optional) What is this about?
```

### 3️⃣ teaching_generate_quiz
```
Create quiz questions from your material

Claude: "Generate 10 hard questions about biology"

Parameters:
- num_questions: 1-20 (default: 5)
- difficulty: easy | medium | hard
- topic_filter: (optional) Specific topic
```

### 4️⃣ teaching_list_topics
```
See all topics you've indexed

Claude: "What topics have I indexed?"

No parameters needed
```

### 5️⃣ teaching_health_check
```
Check system status and statistics

Claude: "Is the teaching assistant system running?"

No parameters needed
```

## Usage Flows

### 📚 Learning from Material

```
1. "Ingest this YouTube video: [URL]"
   → Tool: teaching_ingest_url
   
2. "Summarize what I just ingested"
   → Tool: teaching_assistant_chat
   
3. "Explain the main concept at a beginner level"
   → Tool: teaching_assistant_chat (teaching_level: beginner)
   
4. "Generate a 5-question quiz to test my understanding"
   → Tool: teaching_generate_quiz
```

### 🎯 Creating Study Materials

```
1. "Ingest these materials..." [add 3-5 URLs/files]
   → Multiple calls to teaching_ingest_url
   
2. "What topics do I have?"
   → Tool: teaching_list_topics
   
3. "Generate 5 easy questions, 5 medium, 5 hard on topic X"
   → Multiple calls to teaching_generate_quiz
   
4. "Create an advanced explanation of each topic"
   → Multiple calls to teaching_assistant_chat
```

### 🧪 Assessment & Testing

```
1. "Generate a 10-question hard quiz"
   → Tool: teaching_generate_quiz
   
2. "Here are my answers: A, C, B, D, A..."
   → Claude evaluates (no tool needed)
   
3. "Explain why D is the correct answer for question 4"
   → Tool: teaching_assistant_chat
```

## Common Prompts

### Get Started
```
"Check if the teaching assistant system is running"
"What topics have I indexed so far?"
"Show me system statistics"
```

### Ingest Content
```
"Ingest this YouTube video: [URL]"
"Add this website to my material: [URL]"
"Ingest the video with topic 'machine-learning'"
```

### Learn
```
"Explain [concept] in simple terms"
"Explain [concept] at an advanced level"
"Give examples of how [concept] works"
"Explain [concept] from the material about [topic]"
```

### Quiz Yourself
```
"Generate 5 quiz questions on this topic"
"Create 10 hard questions to really test my knowledge"
"Quiz me on the first chapter"
"Generate medium-difficulty questions on biology"
```

### Get Help
```
"Which topics are covered in my material?"
"What's the most important concept I should understand?"
"Create a study guide for topic X"
"Generate increasingly difficult questions on Y"
```

## Troubleshooting

### Problem: "I don't see the teaching assistant tool"

**Check:**
1. Is `claude_desktop_config.json` valid JSON?
   ```bash
   cat ~/.config/Claude/claude_desktop_config.json | jq .
   ```

2. Is the path correct?
   ```bash
   ls -la /path/to/ai_teaching_assistant_mcp.py
   ```

3. Did you restart Claude after config changes?
   ```bash
   # Close: ⌘Q
   # Reopen Claude
   ```

### Problem: "Cannot connect to server"

**Check:**
1. Is backend running?
   ```bash
   curl http://localhost:8000/api/health
   ```

2. Is it on the right port?
   ```bash
   lsof -i :8000  # Should show uvicorn
   ```

3. Are you on the right network? (localhost only)

### Problem: Ingestion fails

**Check:**
1. Is it a valid URL?
   ```bash
   curl -I "https://youtube.com/watch?v=..."
   ```

2. Does the backend support this format?
   - YouTube: ✅
   - Websites: ✅
   - MP3/WAV: ✅
   - MP4: ✅
   - PDF: ✅

### Problem: Quiz generation is slow

**Normal:** Takes 5-10 seconds for complex questions

**If too slow:**
- Reduce num_questions
- Check backend CPU usage
- Try with fewer chunks in database

## Configuration Files

### claude_desktop_config.json Location

**macOS:**
```
~/.config/Claude/claude_desktop_config.json
```

**Windows:**
```
%APPDATA%\Claude\claude_desktop_config.json
```

**Linux:**
```
~/.config/Claude/claude_desktop_config.json
```

### Environment Variables

In the `"env"` section of config:

```json
{
  "env": {
    "TEACHING_API_URL": "http://localhost:8000/api"
  }
}
```

Change this if your backend runs on different port/host.

## Backend Commands

### Start Backend
```bash
cd backend
python -m uvicorn app.main:app --reload --port 8000
```

### Check Backend Health
```bash
curl http://localhost:8000/api/health
```

### View API Docs
```
http://localhost:3000/docs  # When running
```

## File Locations

| File | Where | Purpose |
|------|-------|---------|
| `ai_teaching_assistant_mcp.py` | `backend/` | Main MCP server |
| `claude_desktop_config.json` | `~/.config/Claude/` | MCP configuration |
| `MCP_SERVER_SETUP_GUIDE.md` | Project root | Detailed setup |
| `AI_TEACHING_ASSISTANT_MCP_README.md` | Project root | Full documentation |

## API Endpoints Used

The MCP server calls these backend endpoints:

| Endpoint | Method | Used By |
|----------|--------|---------|
| `/api/chat/` | POST | teaching_assistant_chat |
| `/api/ingest/url` | POST | teaching_ingest_url |
| `/api/quiz/` | POST | teaching_generate_quiz |
| `/api/topics/` | GET | teaching_list_topics |
| `/api/health` | GET | teaching_health_check |

## Response Times (Typical)

| Operation | Time |
|-----------|------|
| Chat query | 1-3 sec |
| URL ingestion | 5-30 sec |
| Quiz generation | 5-10 sec |
| Topic listing | <1 sec |
| Health check | <1 sec |

## Example Configuration

### For Local Development (Default)

```json
{
  "command": "python",
  "args": ["/path/to/backend/ai_teaching_assistant_mcp.py"],
  "env": {
    "TEACHING_API_URL": "http://localhost:8000/api"
  }
}
```

### For Remote Backend

```json
{
  "command": "python",
  "args": ["/path/to/backend/ai_teaching_assistant_mcp.py"],
  "env": {
    "TEACHING_API_URL": "https://your-api.example.com/api"
  }
}
```

### With Custom Timeout

Edit `ai_teaching_assistant_mcp.py`:
```python
REQUEST_TIMEOUT = 60.0  # Increase from 30 seconds
```

Then restart Claude.

## Tips & Tricks

### 💡 Pro Tips

1. **Filter by topic for focused learning:**
   ```
   "Explain [concept] using only the [topic] material"
   ```

2. **Generate progressive difficulty:**
   ```
   "Generate 5 easy, 5 medium, 5 hard questions"
   ```

3. **Get source attribution:**
   ```
   "Answer my question and tell me which source answered it"
   ```

4. **Batch ingest:**
   ```
   "Ingest these 3 videos: [URL1] [URL2] [URL3]"
   ```

5. **Study guide creation:**
   ```
   "Create a study guide with summaries and quizzes"
   ```

### ⚡ Performance Tips

- Generate quiz with 5-10 questions for fast responses
- Use topic_filter to scope large databases
- Ingest in batches, not individually
- Clear completed sessions (refresh index if huge)

## Need Help?

1. **Setup issues?** → Read `MCP_SERVER_SETUP_GUIDE.md`
2. **How do I use it?** → Read `AI_TEACHING_ASSISTANT_MCP_README.md`
3. **Code problems?** → Check Python errors in Claude Desktop logs
4. **Backend issues?** → Check `http://localhost:8000/docs`

---

**Version:** 1.0.0  
**Created:** May 2026  
**Status:** Ready to use ✅
