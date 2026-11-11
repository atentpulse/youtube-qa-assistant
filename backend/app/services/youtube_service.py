from urllib.parse import (
    parse_qs,
    urlparse,
)

import logging
import time
import requests

logger = logging.getLogger("ytgenius.youtube")

from youtube_transcript_api import (
    NoTranscriptFound,
    TranscriptsDisabled,
    YouTubeTranscriptApi,
)


class TranscriptFetchError(Exception):
    """Raised when a YouTube transcript cannot be fetched."""

    pass


def extract_video_id(
    url: str,
) -> str:

    parsed_url = urlparse(url)
    hostname = parsed_url.hostname

    if hostname == "youtu.be":

        video_id = (
            parsed_url.path
            .lstrip("/")
            .split("/")[0]
        )

        if video_id:
            return video_id

    if hostname in (
        "www.youtube.com",
        "youtube.com",
        "m.youtube.com",
    ):

        if parsed_url.path == "/watch":

            query_params = parse_qs(
                parsed_url.query
            )

            video_id = query_params.get("v")

            if video_id:
                return video_id[0]

        if parsed_url.path.startswith(
            "/shorts/"
        ):

            parts = parsed_url.path.split("/")

            if len(parts) >= 3 and parts[2]:
                return parts[2]

    raise ValueError(
        "Invalid or unsupported YouTube URL"
    )


def fetch_video_metadata(
    video_id: str,
) -> dict:

    url = (
        "https://www.youtube.com/oembed"
        f"?url=https://www.youtube.com/watch"
        f"?v={video_id}"
        "&format=json"
    )

    try:

        response = requests.get(
            url,
            timeout=10,
        )

        response.raise_for_status()

        data = response.json()

        return {
            "title": data.get("title") or "Unknown Title",
            "thumbnail_url": (
                f"https://i.ytimg.com/vi/"
                f"{video_id}/hqdefault.jpg"
            ),
        }

    except requests.RequestException as error:

        logger.warning(
            "Could not fetch video metadata: %s",
            error,
        )

        return {
            "title": "Unknown Title",
            "thumbnail_url": (
                f"https://i.ytimg.com/vi/"
                f"{video_id}/hqdefault.jpg"
            ),
        }


def fetch_transcript(
    video_id: str,
    languages: tuple[str, ...] | list[str] = ("en", "en-US", "en-GB"),
    retries: int = 3,
):
    """
    Fetches transcripts with robust multi-stage fallback:
    1. Manually created transcripts in preferred languages
    2. Automatically generated transcripts in preferred languages
    3. Any transcript in preferred languages
    4. Auto-translated to English or any available transcript track
    5. Fallback to direct fetch
    """
    last_error = None
    api = YouTubeTranscriptApi()

    for attempt in range(retries):
        try:
            if hasattr(api, "list"):
                try:
                    transcript_list = api.list(video_id)
                except Exception as list_exc:
                    if isinstance(list_exc, (TranscriptsDisabled, NoTranscriptFound)):
                        raise list_exc
                    return api.fetch(video_id, languages=languages)

                # 1. Try manual transcript in preferred languages
                try:
                    return transcript_list.find_manually_created_transcript(languages).fetch()
                except (NoTranscriptFound, AttributeError):
                    pass

                # 2. Try generated transcript in preferred languages
                try:
                    return transcript_list.find_generated_transcript(languages).fetch()
                except (NoTranscriptFound, AttributeError):
                    pass

                # 3. Try any transcript in preferred languages
                try:
                    return transcript_list.find_transcript(languages).fetch()
                except (NoTranscriptFound, AttributeError):
                    pass

                # 4. Fallback: try any available transcript track (translate to en if possible)
                available = list(transcript_list)
                if available:
                    for tr in available:
                        if getattr(tr, "is_translatable", False):
                            tl_list = getattr(tr, "translation_languages", [])
                            if any(isinstance(tl, dict) and tl.get("language_code") == "en" for tl in tl_list):
                                try:
                                    return tr.translate("en").fetch()
                                except Exception:
                                    pass
                    return available[0].fetch()

                raise NoTranscriptFound(video_id, list(languages), transcript_list)
            else:
                return api.fetch(video_id, languages=languages)

        except TranscriptsDisabled:
            raise TranscriptFetchError(
                "Transcript is disabled for this video."
            )
        except NoTranscriptFound:
            raise TranscriptFetchError(
                "No transcript was found for this video."
            )
        except Exception as error:
            last_error = error
            logger.warning(
                "Transcript attempt %d/%d failed: %s",
                attempt + 1,
                retries,
                error,
            )
            if attempt < retries - 1:
                time.sleep(2 * (attempt + 1))

    raise TranscriptFetchError(
        f"Could not fetch transcript: {last_error}"
    )


def format_transcript(
    transcript,
):
    segments = []

    for item in transcript:
        if isinstance(item, dict):
            text_val = item.get("text", "")
            start_val = item.get("start", 0.0)
            duration_val = item.get("duration", 0.0)
        else:
            text_val = getattr(item, "text", "")
            start_val = getattr(item, "start", 0.0)
            duration_val = getattr(item, "duration", 0.0)

        segments.append(
            {
                "text": (
                    str(text_val)
                    .replace("\n", " ")
                    .strip()
                ),
                "start": start_val or 0.0,
                "duration": duration_val or 0.0,
            }
        )

    return segments
