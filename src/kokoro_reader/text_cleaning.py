"""Convert pasted, formatted text into safe text for speech synthesis."""

from __future__ import annotations

import html
import re
import unicodedata

# Keep the human-readable label, but do not make Kokoro spell the destination.
MARKDOWN_IMAGE = re.compile(r"!\[([^]]*)]\([^)]*\)")
MARKDOWN_LINK = re.compile(r"\[([^]]+)]\([^)]*\)")
MARKDOWN_REFERENCE = re.compile(r"\[([^]]+)]\[[^]]*]")
REFERENCE_DEFINITION = re.compile(r"(?m)^\s*\[[^]]+]:\s*\S+.*$")
HTML_TAG = re.compile(r"<[^>]+>")
URL = re.compile(r"\b(?:https?://|www\.)\S+", re.IGNORECASE)
LIST_PREFIX = re.compile(r"(?m)^[ \t]*(?:#{1,6}|>|[-+*]|\d+[.)])[ \t]+")
TABLE_DIVIDER = re.compile(r"(?m)^[ \t]*\|?(?:[ \t]*:?-{3,}:?[ \t]*\|)+[ \t]*$")

PUNCTUATION_TRANSLATION = str.maketrans(
    {
        "“": '"',
        "”": '"',
        "„": '"',
        "‘": "'",
        "’": "'",
        "‚": "'",
        "–": "-",
        "—": "-",
        "―": "-",
        "…": "...",
        "•": " ",
        "·": " ",
        "|": ", ",
    }
)

# These marks help the voice sound natural. Other punctuation and all symbols
# are changed to spaces, rather than deleted, to prevent neighboring words from
# being accidentally joined.
SPEAKABLE_PUNCTUATION = frozenset(".,!?;:'\"-()")


def remove_heading_lines(text: str) -> str:
    """Remove complete lines that begin with a Markdown heading marker."""
    return "".join(
        line for line in text.splitlines(keepends=True) if not line.startswith("#")
    )


def _filter_characters(text: str) -> str:
    result: list[str] = []
    for character in text:
        if character in "\n\t " or character in SPEAKABLE_PUNCTUATION:
            result.append(character)
            continue

        category = unicodedata.category(character)
        if category[0] in {"L", "N"} or category.startswith("M"):
            result.append(character)
        else:
            # Covers emoji (So), Markdown punctuation, private-use glyphs,
            # Unicode controls/formatting, and mathematical/currency symbols.
            result.append(" ")
    return "".join(result)


def clean_for_speech(text: str) -> str:
    """Remove formatting and non-speech glyphs while retaining readable prose."""
    text = html.unescape(text)
    text = REFERENCE_DEFINITION.sub("", text)
    text = MARKDOWN_IMAGE.sub(r"\1", text)
    text = MARKDOWN_LINK.sub(r"\1", text)
    text = MARKDOWN_REFERENCE.sub(r"\1", text)
    text = HTML_TAG.sub(" ", text)
    text = URL.sub(" ", text)
    text = TABLE_DIVIDER.sub("", text)
    text = LIST_PREFIX.sub("", text)
    text = text.translate(PUNCTUATION_TRANSLATION)
    text = unicodedata.normalize("NFC", text)
    text = _filter_characters(text)

    # Preserve paragraph pauses, but normalize formatting whitespace.
    paragraphs = []
    for paragraph in re.split(r"\n\s*\n", text):
        paragraph = re.sub(r"[ \t\r\f\v]+", " ", paragraph)
        paragraph = re.sub(r"\n+", " ", paragraph).strip()
        paragraph = re.sub(r"\s+([.,!?;:])", r"\1", paragraph)
        paragraph = re.sub(r"\(\s+", "(", paragraph)
        paragraph = re.sub(r"\s+\)", ")", paragraph)
        if paragraph:
            paragraphs.append(paragraph)
    return "\n\n".join(paragraphs)
