"""
Claude Vision image analysis for traffic camera images.

Analyzes camera images for road conditions: snow, vehicles, animals.
"""

from __future__ import annotations

import base64
from pathlib import Path

import anthropic
from rich.console import Console

from models import AnalysisResult

console = Console()

ANALYSIS_PROMPT = """Analyze this traffic camera image and answer the following questions:

1. Is there snow visible on the road? (yes/no)
2. Are there any cars visible? (yes/no)
3. Are there any trucks visible? (yes/no)
4. Are there any animals visible? (yes/no)

Also provide a brief description of the overall road conditions.

Respond in this exact format:
SNOW: yes/no
CARS: yes/no
TRUCKS: yes/no
ANIMALS: yes/no
NOTES: <brief description>"""


def detect_media_type(data: bytes) -> str:
    """Detect image media type from magic bytes."""
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return "image/png"
    elif data[:2] == b"\xff\xd8":
        return "image/jpeg"
    elif data[:4] == b"GIF8":
        return "image/gif"
    elif data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    return "image/jpeg"


def analyze_image_bytes(
    client: anthropic.Anthropic, image_data: bytes
) -> AnalysisResult:
    """Analyze raw image bytes using Claude Vision."""
    encoded = base64.standard_b64encode(image_data).decode("utf-8")
    media_type = detect_media_type(image_data)

    try:
        message = client.messages.create(
            model="claude-3-5-haiku-20241022",
            max_tokens=300,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": media_type,
                                "data": encoded,
                            },
                        },
                        {"type": "text", "text": ANALYSIS_PROMPT},
                    ],
                }
            ],
        )

        return parse_analysis_response(message.content[0].text)

    except anthropic.APIError as e:
        console.print(f"[red]Claude API error:[/red] {e}")
        return AnalysisResult(notes=f"Analysis failed: {e}")


def analyze_image_file(client: anthropic.Anthropic, image_path: Path) -> AnalysisResult:
    """Analyze a local image file using Claude Vision."""
    return analyze_image_bytes(client, image_path.read_bytes())


def parse_analysis_response(text: str) -> AnalysisResult:
    """Parse Claude's analysis response into structured data."""
    result: dict = {
        "has_snow": None,
        "has_car": None,
        "has_truck": None,
        "has_animal": None,
        "notes": "",
    }

    for line in text.strip().split("\n"):
        lower = line.lower()
        if lower.startswith("snow:"):
            result["has_snow"] = "yes" in lower
        elif lower.startswith("cars:"):
            result["has_car"] = "yes" in lower
        elif lower.startswith("trucks:"):
            result["has_truck"] = "yes" in lower
        elif lower.startswith("animals:"):
            result["has_animal"] = "yes" in lower
        elif lower.startswith("notes:"):
            result["notes"] = line.split(":", 1)[1].strip()

    return AnalysisResult(**result)
