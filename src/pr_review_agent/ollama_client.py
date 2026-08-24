from __future__ import annotations

import json
from typing import Any

import requests


def maybe_enrich_with_ollama(summary: dict[str, Any]) -> dict[str, Any]:
    try:
        response = requests.post(
            "http://localhost:11434/api/generate",
            json={
                "model": "llama3.1:8b",
                "prompt": (
                    "Summarize this pull request in a concise professional way. "
                    f"PR summary: {summary['summary']}\n"
                    f"Risk signals: {summary['security']['risk_signals']}\n"
                    f"Review areas: {summary['review_areas']}\n"
                    f"Libraries: {summary['important_libraries']}"
                ),
                "stream": False,
            },
            timeout=5,
        )
        if response.status_code != 200:
            summary["llm_note"] = "Ollama is not available or model is not installed."
            return summary
        payload = response.json()
        summary["llm_enrichment"] = payload.get("response", "Local enhancement unavailable.")
        summary["llm_note"] = "Enhanced using local Ollama model."
    except Exception:
        summary["llm_note"] = "Ollama not reachable; local AI enhancement skipped."
    return summary
