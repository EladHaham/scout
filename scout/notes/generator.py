from __future__ import annotations

import json
import os

from scout.domain.ports import NoteGenerator
from scout.utils.errors import ScoutError

_SYSTEM_PROMPT = """\
You are a code indexing assistant. Given function, class, interface, type, or config \
definitions in any language (Python, TypeScript, JavaScript, JSON, TOML), return a JSON array \
of notes. One note per symbol. No explanation, no markdown.

Each note must follow this exact shape:
{"symbol": "<name>", "file": "<file>", "purpose": "<description>", "tags": ["<2-4 lowercase domain tags>"], "related_symbols": ["<direct dependency names only>"]}

Rules:
- symbol: must exactly match the input symbol name
- file: must exactly match the input file path
- purpose: 1-2 sentences, max 40 words. Describe specifically WHAT data it reads/writes/transforms, WHAT operations it performs, and include key domain nouns. Be concrete — mention field names, HTTP methods, database operations if visible. Make it distinct from other symbols in the same domain. Do NOT say "handles" or "manages" — say exactly what it does.
  Good: "Batch-creates N weekly delivery records in DynamoDB with shared recurringGroupId, validates date and required fields, returns all created items"
  Bad: "Handles creating deliveries for a farmer" (too vague, no specifics)
  Good: "Deletes future recurring delivery records in DynamoDB for a farmer, filtered by recurringGroupId and target date, excluding completed deliveries"
  Bad: "Deletes future deliveries" (missing key details)
- tags: domain concepts only (e.g. cache, auth, delivery, email, routing) not language keywords
- related_symbols: function/class/component names this directly calls or depends on, no file paths
- omit related_symbols if none
- for JSON/TOML config files: describe what the config controls, tags should reflect the tooling
- return ONLY a valid JSON array starting with [ and ending with ], nothing else, no markdown
- all field values must be in English only — no other languages, or other non-ASCII characters in purpose, tags, or related_symbols\
"""


_HEAD_LINES = 10
_TAIL_LINES = 10
_MAX_LINES = _HEAD_LINES + _TAIL_LINES


def _trim_body(body: str) -> str:
    lines = body.splitlines()
    if len(lines) <= _MAX_LINES:
        return body
    omitted = len(lines) - _MAX_LINES
    head = lines[:_HEAD_LINES]
    tail = lines[-_TAIL_LINES:]
    return "\n".join(head) + f"\n... ({omitted} lines omitted) ...\n" + "\n".join(tail)


def _format_symbols_for_prompt(symbols: list[dict]) -> str:
    parts = []
    for s in symbols:
        parts.append(
            f"[{s['symbol_type']}] {s['symbol']} (file: {s['file']})\n"
            f"{s['signature']}\n"
            f"{_trim_body(s['body'])}\n"
            f"---"
        )
    return "\n".join(parts)


def _parse_response(raw: str) -> list[dict]:
    text = raw.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        text = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
    return json.loads(text)


class OpenAINoteGenerator(NoteGenerator):
    """
    NoteGenerator backed by OpenAI's API.
    Expects OPENAI_API_KEY env var to be set.
    Defaults to gpt-4o-mini — fast and cheap for structured indexing.
    """

    def __init__(self, model: str = "gpt-4o-mini", batch_size: int = 5) -> None:
        self.model = model
        self.batch_size = batch_size

    def _client(self):
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise ScoutError(
                "openai package is required. Run: pip install openai"
            ) from exc

        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise ScoutError("OPENAI_API_KEY environment variable is not set.")

        return OpenAI(api_key=api_key)

    def generate(self, symbols: list[dict]) -> list[dict]:
        if not symbols:
            return []

        client = self._client()
        results: list[dict] = []

        for i in range(0, len(symbols), self.batch_size):
            batch = symbols[i : i + self.batch_size]
            batch_num = i // self.batch_size + 1
            total_batches = (len(symbols) + self.batch_size - 1) // self.batch_size
            print(f"  batch {batch_num}/{total_batches} ({len(batch)} symbols)...", flush=True)
            results.extend(self._call_api(client, batch))

        return results

    def _call_api(self, client, symbols: list[dict]) -> list[dict]:
        user_content = _format_symbols_for_prompt(symbols)

        try:
            response = client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": _SYSTEM_PROMPT},
                    {"role": "user", "content": user_content},
                ],
                temperature=0.1,
                timeout=120,
            )
        except Exception as exc:
            raise ScoutError(f"OpenAI API call failed: {exc}") from exc

        raw = response.choices[0].message.content or ""

        try:
            parsed = _parse_response(raw)
        except (json.JSONDecodeError, ValueError) as exc:
            raise ScoutError(
                f"OpenAI returned invalid JSON.\nRaw response:\n{raw}"
            ) from exc

        if isinstance(parsed, dict):
            for v in parsed.values():
                if isinstance(v, list):
                    return v
            raise ScoutError(f"Unexpected JSON shape from OpenAI: {parsed}")

        return parsed