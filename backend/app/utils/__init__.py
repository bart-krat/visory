"""Shared utilities for the Visory backend."""

# Category ordering for task scheduling (Health -> Work -> Personal)
CATEGORY_ORDER = {"health": 0, "work": 1, "personal": 2}


def clean_json_response(response: str) -> str:
    """Extract and clean JSON from an LLM response.

    Handles markdown code blocks (```json ... ```) that LLMs often wrap JSON in.

    Args:
        response: Raw LLM response that may contain JSON.

    Returns:
        Cleaned string ready for json.loads().
    """
    content = response.strip()
    if content.startswith("```"):
        content = content.split("```")[1]
        if content.startswith("json"):
            content = content[4:]
    return content.strip()


def time_window_minutes(start_time: str, end_time: str) -> int:
    """Calculate total minutes between two HH:MM time strings.

    Args:
        start_time: Start time in "HH:MM" format.
        end_time: End time in "HH:MM" format.

    Returns:
        Total minutes between start and end.
    """
    start_h, start_m = map(int, start_time.split(":"))
    end_h, end_m = map(int, end_time.split(":"))
    return (end_h * 60 + end_m) - (start_h * 60 + start_m)
