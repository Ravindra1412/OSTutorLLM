"""
app/ai/services/response_formatter.py

The Response Formatter (Section 1/12). The LLM is instructed (via the
developer prompt) to respond in Markdown, but a response formatter
still has two real jobs even so:
  1. Sanitize: strip any raw HTML/script content the model might
     produce (defense in depth — never trust generated content to be
     safe to render as-is), using `bleach` to allow only a safe
     Markdown-adjacent tag subset.
  2. Validate/repair structure: fix an unbalanced code fence (a common
     LLM failure mode) rather than shipping broken Markdown to the
     frontend's renderer (Part 3.2's tutor_chat.js `renderMarkdownLite`).

Headings/lists/tables/code blocks are native Markdown syntax the model
already produces directly (Section 12) — this formatter's job is
safety and structural validity, not re-implementing a Markdown parser
the frontend (or a future `markdown` library pass) already handles.
"""

import re

import bleach

_ALLOWED_TAGS = ["p", "br", "strong", "em", "code", "pre", "ul", "ol", "li", "a", "h1", "h2", "h3", "table", "thead", "tbody", "tr", "th", "td"]
_ALLOWED_ATTRS = {"a": ["href", "title"]}


def sanitize(text: str) -> str:
    """Strips any disallowed HTML the model may have produced, leaving
    Markdown syntax (which is plain text, not HTML) untouched."""
    return bleach.clean(text, tags=_ALLOWED_TAGS, attributes=_ALLOWED_ATTRS, strip=True)


def fix_unbalanced_code_fences(text: str) -> str:
    """If the model's response has an odd number of ``` fences (cut off
    mid-code-block, a known LLM failure mode especially under a low
    max_tokens budget), append a closing fence so the frontend renderer
    never breaks the rest of the page's layout."""
    fence_count = len(re.findall(r"```", text))
    if fence_count % 2 == 1:
        return text.rstrip() + "\n```"
    return text


def add_tip_warning_markup(text: str) -> str:
    """Section 12 — Tips/Warnings. Converts a simple `[TIP]`/`[WARNING]`
    marker (which the prompt templates can instruct the model to use)
    into a Markdown blockquote with a labeled prefix, giving the
    frontend a consistent, styleable convention without needing custom
    HTML from the model."""
    text = re.sub(r"^\[TIP\]\s*(.+)$", r"> 💡 **Tip:** \1", text, flags=re.MULTILINE)
    text = re.sub(r"^\[WARNING\]\s*(.+)$", r"> ⚠️ **Warning:** \1", text, flags=re.MULTILINE)
    return text


def format_response(raw_text: str) -> str:
    """The full formatting pipeline, applied to every tutor response
    before it is persisted/returned."""
    text = sanitize(raw_text)
    text = fix_unbalanced_code_fences(text)
    text = add_tip_warning_markup(text)
    return text.strip()
