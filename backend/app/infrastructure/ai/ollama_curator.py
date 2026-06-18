"""OllamaCurator — ranks candidates with a local LLM via Ollama (free, offline).

Uses Ollama's structured-output `format` (a JSON schema) so the model returns
parseable picks. Reachable at OLLAMA_HOST; model is OLLAMA_MODEL.
"""
from __future__ import annotations

import json
import logging

import requests

from ...config import OLLAMA_HOST, OLLAMA_MODEL
from ...domain.discovery.entities import Candidate, Recommendation, TasteProfile
from ._shared import PICKS_SCHEMA, SYSTEM, build_user_prompt, picks_to_recommendations

log = logging.getLogger("infra.ai")


class OllamaCurator:
    backend_name = "ollama"

    def __init__(self) -> None:
        self._host = OLLAMA_HOST.rstrip("/")
        self._model = OLLAMA_MODEL

    def curate(
        self, profile: TasteProfile, candidates: list[Candidate], limit: int
    ) -> list[Recommendation]:
        body = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": SYSTEM},
                {"role": "user", "content": build_user_prompt(profile, candidates, limit)},
            ],
            "format": PICKS_SCHEMA,
            "stream": False,
            "options": {"temperature": 0.7},
        }
        try:
            resp = requests.post(f"{self._host}/api/chat", json=body, timeout=120)
        except requests.exceptions.RequestException as e:
            raise RuntimeError(
                f"Can't reach Ollama at {self._host}. Is it running? (`ollama serve`)"
            ) from e

        if resp.status_code == 404:
            raise RuntimeError(
                f"Ollama model '{self._model}' not found. Pull it first: `ollama pull {self._model}`"
            )
        if not resp.ok:
            raise RuntimeError(f"Ollama error {resp.status_code}: {resp.text[:200]}")

        content = (resp.json().get("message") or {}).get("content", "")
        try:
            picks = json.loads(content).get("picks", [])
        except json.JSONDecodeError:
            log.warning("Ollama returned non-JSON content: %s", content[:200])
            raise RuntimeError("Ollama returned an unparseable response. Try a larger model.")
        return picks_to_recommendations(picks, candidates)
