"""YouTube video transcript extraction."""
import logging
import os
import re

from youtube_transcript_api import (
    CouldNotRetrieveTranscript,
    RequestBlocked,
    YouTubeTranscriptApi,
)
from youtube_transcript_api.proxies import GenericProxyConfig

logger = logging.getLogger(__name__)


def _build_youtube_api() -> YouTubeTranscriptApi:
    """Use YOUTUBE_TRANSCRIPT_PROXY (HTTPS URL) on cloud hosts; YouTube often blocks datacenter IPs."""
    proxy_url = os.getenv("YOUTUBE_TRANSCRIPT_PROXY", "").strip()
    if not proxy_url:
        return YouTubeTranscriptApi()
    logger.info("YouTube transcript requests will use configured HTTPS proxy.")
    return YouTubeTranscriptApi(
        proxy_config=GenericProxyConfig(https_url=proxy_url),
    )


_api = _build_youtube_api()


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

    try:
        transcript_list = _api.list(video_id)
    except RequestBlocked as exc:
        raise ValueError(
            "YouTube is blocking requests from this server's IP (typical on Render, AWS, "
            "GCP, Azure). Options: (1) Set env YOUTUBE_TRANSCRIPT_PROXY to a residential "
            "HTTPS proxy URL — see "
            "https://github.com/jdepoix/youtube-transcript-api?tab=readme-ov-file#working-around-ip-bans-requestblocked-or-ipblocked-exception "
            "(2) Run ingestion locally where your home IP works "
            "(3) Paste the video transcript into a .txt file and upload instead."
        ) from exc
    except CouldNotRetrieveTranscript as exc:
        msg = str(exc).strip()
        if len(msg) > 800:
            msg = msg[:800] + "…"
        raise ValueError(msg) from exc

    available = []
    for t in transcript_list:
        available.append(t.language_code)

    if not available:
        raise ValueError(
            f"No transcripts available at all for video '{video_id}'."
        )

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

    try:
        transcript = _api.fetch(video_id, languages=languages_to_try)
    except RequestBlocked as exc:
        raise ValueError(
            "YouTube is blocking requests from this server's IP (typical on Render, AWS, "
            "GCP, Azure). Set YOUTUBE_TRANSCRIPT_PROXY to an HTTPS proxy URL, ingest locally, "
            "or upload a text file. See youtube-transcript-api README: working-around-ip-bans."
        ) from exc
    except CouldNotRetrieveTranscript as exc:
        msg = str(exc).strip()
        if len(msg) > 800:
            msg = msg[:800] + "…"
        raise ValueError(msg) from exc

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
