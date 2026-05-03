"""YouTube video transcript extraction."""
import logging
import re

from youtube_transcript_api import YouTubeTranscriptApi

logger = logging.getLogger(__name__)
_api = YouTubeTranscriptApi()


def extract_video_id(url: str) -> str:
    """Parse a YouTube URL and return the video ID."""
    patterns = [
        r"(?:v=|/v/|youtu\.be/)([a-zA-Z0-9_-]{11})",
        r"(?:embed/)([a-zA-Z0-9_-]{11})",
        r"(?:shorts/)([a-zA-Z0-9_-]{11})",
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    raise ValueError(f"Could not extract video ID from URL: {url}")


def get_youtube_transcript(url: str) -> str:
    """Fetch the transcript for a YouTube video.
    Priority: English manual → English auto → any other language available.
    """
    video_id = extract_video_id(url)

    transcript_list = _api.list(video_id)

    # Build a priority-ordered list of language codes to try
    available = []
    for t in transcript_list:
        available.append(t.language_code)

    if not available:
        raise ValueError(
            f"No transcripts available at all for video '{video_id}'."
        )

    # Try English first, then fall back to whatever is available
    languages_to_try = []
    if "en" in available:
        languages_to_try.append("en")
    for lang in available:
        if lang not in languages_to_try:
            languages_to_try.append(lang)

    logger.info(
        "Video %s has transcripts in: %s. Trying: %s",
        video_id, available, languages_to_try[0],
    )

    transcript = _api.fetch(video_id, languages=languages_to_try)

    segments: list[str] = []
    for snippet in transcript:
        timestamp = _format_timestamp(snippet.start)
        segments.append(f"[{timestamp}] {snippet.text}")

    return "\n".join(segments)


def _format_timestamp(seconds: float) -> str:
    mins, secs = divmod(int(seconds), 60)
    hrs, mins = divmod(mins, 60)
    if hrs:
        return f"{hrs:02d}:{mins:02d}:{secs:02d}"
    return f"{mins:02d}:{secs:02d}"
