import os
from typing import Optional, List, Dict, Any
import httpx
from pydantic import BaseModel, Field, ConfigDict, field_validator
from mcp.server.fastmcp import FastMCP

# Configuration
API_BASE_URL = os.getenv("TEACHING_API_URL")
REQUEST_TIMEOUT = 30.0

# Initialize MCP server
mcp = FastMCP("ai_teaching_assistant_mcp")


def _handle_api_error(e: Exception, context: str = "") -> str:
    """Format API errors with actionable messages."""
    error_msg = f"Error communicating with AI Teaching Assistant"
    if context:
        error_msg += f" ({context})"

    if isinstance(e, httpx.HTTPStatusError):
        if e.response.status_code == 404:
            return f"{error_msg}: Resource not found (404). Please check parameters."
        elif e.response.status_code == 400:
            try:
                detail = e.response.json().get("detail", "Bad request")
                return f"{error_msg}: {detail}"
            except:
                return f"{error_msg}: Bad request (400)"
        elif e.response.status_code == 422:
            return f"{error_msg}: Invalid input data (422)"
        elif e.response.status_code == 500:
            return f"{error_msg}: Server error (500). Please try again later."
        return f"{error_msg}: HTTP {e.response.status_code}"
    elif isinstance(e, httpx.TimeoutException):
        return f"{error_msg}: Request timed out after {REQUEST_TIMEOUT}s. Server may be offline."
    elif isinstance(e, httpx.ConnectError):
        return f"{error_msg}: Cannot connect to server at {API_BASE_URL}. Is it running?"
    
    return f"{error_msg}: {type(e).__name__}: {str(e)}"


# ============================================================================
# INPUT MODELS
# ============================================================================


class ChatInput(BaseModel):
    """Input for RAG chat queries."""
    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        extra="forbid"
    )

    question: str = Field(
        ...,
        description="Your question about the ingested material",
        min_length=1,
        max_length=2000
    )
    mode: str = Field(
        default="intermediate",
        description="Teaching mode: 'eli5' (explain like I'm 5), 'beginner', 'intermediate', or 'advanced'",
        pattern="^(eli5|beginner|intermediate|advanced)$"
    )
    topic: Optional[str] = Field(
        default=None,
        description="Optional: Filter answers to specific topic (e.g., 'biology', 'chapter-2')",
        max_length=200
    )

    @field_validator("mode")
    @classmethod
    def validate_mode(cls, v: str) -> str:
        valid_modes = ["eli5", "beginner", "intermediate", "advanced"]
        if v not in valid_modes:
            raise ValueError(f"Mode must be one of: {', '.join(valid_modes)}")
        return v


class IngestionInput(BaseModel):
    """Input for URL-based ingestion."""
    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        extra="forbid"
    )

    url: str = Field(
        ...,
        description="URL to ingest (YouTube, website, or direct media link)",
        min_length=10,
        max_length=2000
    )
    topic: Optional[str] = Field(
        default=None,
        description="Optional topic label for organizing ingested material",
        max_length=200
    )
    description: Optional[str] = Field(
        default=None,
        description="Optional human-readable description of the content",
        max_length=500
    )

    @field_validator("url")
    @classmethod
    def validate_url(cls, v: str) -> str:
        if not v.startswith(("http://", "https://", "ftp://")):
            raise ValueError("URL must start with http://, https://, or ftp://")
        return v


class QuizInput(BaseModel):
    """Input for quiz generation."""
    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        extra="forbid"
    )

    topic: str = Field(
        ...,
        description="Topic to generate quiz questions about (e.g., 'biology', 'chapter-2')",
        min_length=1,
        max_length=200
    )
    num_questions: int = Field(
        default=5,
        description="Number of quiz questions to generate",
        ge=1,
        le=20
    )
    difficulty: str = Field(
        default="intermediate",
        description="Question difficulty: 'beginner', 'intermediate', or 'advanced'",
        pattern="^(beginner|intermediate|advanced)$"
    )

    @field_validator("difficulty")
    @classmethod
    def validate_difficulty(cls, v: str) -> str:
        valid_difficulties = ["beginner", "intermediate", "advanced"]
        if v not in valid_difficulties:
            raise ValueError(f"Difficulty must be one of: {', '.join(valid_difficulties)}")
        return v


class HealthCheckResponse(BaseModel):
    """Health check response."""
    status: str
    total_chunks: int
    topics: List[str]
    timestamp: str


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================


async def _make_request(
    method: str,
    endpoint: str,
    json_data: Optional[Dict[str, Any]] = None,
    params: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    """Make async HTTP request to the backend API."""
    url = f"{API_BASE_URL}{endpoint}"
    
    async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
        try:
            response = await client.request(method, url, json=json_data, params=params)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            raise e


def _format_chat_response(data: Dict[str, Any]) -> str:
    """Format chat response as readable text."""
    answer = data.get("answer", "No answer generated")
    
    output = f"## Answer\n\n{answer}\n"
    
    if data.get("sources"):
        output += "\n## Sources Used\n\n"
        for i, source in enumerate(data["sources"], 1):
            source_name = source.get("source", "Unknown source")
            topic = source.get("topic", "")
            score = source.get("score", 0)
            topic_label = f", Topic: {topic}" if topic else ""
            output += f"{i}. **{source_name}** (Score: {score:.3f}{topic_label})\n"
    
    return output


def _format_quiz_response(data: Dict[str, Any]) -> str:
    """Format quiz response as readable questions."""
    questions = data.get("questions", [])
    
    if not questions:
        return "No quiz questions could be generated. Try ingesting more material."
    
    output = f"## Quiz ({len(questions)} Questions)\n\n"
    
    for i, q in enumerate(questions, 1):
        output += f"### Question {i}\n\n**{q.get('question', 'No question')}**\n\n"
        
        options = q.get("options", [])
        for j, opt in enumerate(options, 1):
            output += f"{chr(64+j)}) {opt}\n"
        
        output += "\n"
    
    output += "*Note: Answers and explanations will be shown after you submit your responses.*\n"
    
    return output


# ============================================================================
# MCP TOOLS
# ============================================================================


@mcp.tool(
    name="teaching_assistant_chat",
    annotations={
        "title": "Chat with Teaching Assistant",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False
    }
)
async def teaching_assistant_chat(params: ChatInput) -> str:
    """Chat with the RAG-powered AI teacher about ingested material.
    
    This tool queries the teaching assistant with your question and retrieves
    relevant answers grounded in the ingested documents. Supports different
    teaching levels for explanations.
    
    Args:
        params (ChatInput): Chat parameters including question, teaching level,
            optional topic filter, and source inclusion preference
    
    Returns:
        str: Formatted response with answer and source attribution
    """
    try:
        payload = {
            "question": params.question,
            "mode": params.mode,
        }
        if params.topic:
            payload["topic"] = params.topic
        
        response = await _make_request("POST", "/chat/", json_data=payload)
        return _format_chat_response(response)
    
    except Exception as e:
        return _handle_api_error(e, "chat")


@mcp.tool(
    name="teaching_ingest_url",
    annotations={
        "title": "Ingest Content from URL",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": True
    }
)
async def teaching_ingest_url(params: IngestionInput) -> str:
    """Ingest content from URLs (YouTube videos, websites, or media files).
    
    Supports:
    - YouTube videos (automatically extracts transcripts)
    - Websites (extracts readable text)
    - Direct media links (audio/video files for transcription)
    
    The content is automatically processed, chunked, embedded, and stored
    in the vector database for future queries.
    
    Args:
        params (IngestionInput): URL and optional topic/description
    
    Returns:
        str: Confirmation of ingestion with processing details
    """
    try:
        payload = {
            "url": params.url,
        }
        if params.topic:
            payload["topic"] = params.topic
        
        response = await _make_request("POST", "/ingest/url", json_data=payload)
        
        output = "**Content Successfully Ingested**\n\n"
        output += f"**Source**: {response.get('source', 'Unknown')}\n"
        output += f"**Source Type**: {response.get('source_type', 'Unknown')}\n"
        output += f"**Chunks Created**: {response.get('chunks_created', 0)}\n"
        
        output += "\nYou can now ask questions about this material using the chat tool."
        
        return output
    
    except Exception as e:
        return _handle_api_error(e, "ingestion")


@mcp.tool(
    name="teaching_generate_quiz",
    annotations={
        "title": "Generate Quiz Questions",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": False
    }
)
async def teaching_generate_quiz(params: QuizInput) -> str:
    """Generate multiple-choice quiz questions from ingested material.
    
    Automatically creates questions based on the content you've ingested.
    Useful for testing understanding and reinforcing learning.
    
    Args:
        params (QuizInput): Number of questions, optional topic filter, and difficulty
    
    Returns:
        str: Formatted quiz questions with multiple choice options
    """
    try:
        payload = {
            "topic": params.topic,
            "num_questions": params.num_questions,
            "difficulty": params.difficulty,
        }
        
        response = await _make_request("POST", "/quiz/", json_data=payload)
        return _format_quiz_response(response)
    
    except Exception as e:
        return _handle_api_error(e, "quiz generation")


@mcp.tool(
    name="teaching_list_topics",
    annotations={
        "title": "List Available Topics",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False
    }
)
async def teaching_list_topics() -> str:
    """List all topics in the ingested material.
    
    Useful for understanding what content has been ingested and for filtering
    queries and quizzes to specific topics.
    
    Returns:
        str: Formatted list of topics with description
    """
    try:
        response = await _make_request("GET", "/topics/")
        
        topics = response.get("topics", [])
        
        if not topics:
            return "No topics have been indexed yet. Ingest some material first!"
        
        output = f"## Available Topics ({len(topics)})\n\n"
        for topic in topics:
            output += f"- **{topic}**\n"
        
        output += "\nYou can use these topics with the `topic_filter` parameter in chat or quiz generation."
        
        return output
    
    except Exception as e:
        return _handle_api_error(e, "listing topics")


@mcp.tool(
    name="teaching_health_check",
    annotations={
        "title": "Check System Health",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False
    }
)
async def teaching_health_check() -> str:
    """Check the health and status of the AI Teaching Assistant.
    
    Returns system statistics including total indexed chunks and available topics.
    
    Returns:
        str: Health status and system statistics
    """
    try:
        response = await _make_request("GET", "/health")
        
        output = "## System Health Status\n\n"
        output += f"**Status**: {response.get('status', 'Unknown').upper()}\n"
        output += f"**Total Indexed Chunks**: {response.get('total_chunks', 0)}\n"
        output += f"**Topics Available**: {len(response.get('topics', []))}\n"
        
        if response.get("topics"):
            output += "\n**Topics**:\n"
            for topic in response["topics"]:
                output += f"- {topic}\n"
        
        return output
    
    except Exception as e:
        return _handle_api_error(e, "health check")


if __name__ == "__main__":
    mcp.run()
# unused — should trip ruff
