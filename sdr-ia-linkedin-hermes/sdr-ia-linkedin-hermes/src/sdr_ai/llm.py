from __future__ import annotations

import json
from typing import Any

import httpx

from .config import LLMConfig
from .models import ActivitySignal, Offer, Prospect


class LLMIntentAnalyzer:
    def __init__(self, config: LLMConfig, client: httpx.Client | None = None) -> None:
        self.config = config
        self.client = client or httpx.Client(timeout=45)

    def close(self) -> None:
        self.client.close()

    def analyze(self, prospect: Prospect, offer: Offer, posts: list[ActivitySignal]) -> tuple[int, list[str], str]:
        if not self.config.enabled or self.config.provider == "none" or not self.config.api_key:
            return 0, [], "LLM desactive ou cle manquante"
        prompt = _build_prompt(prospect, offer, posts)
        payload = {
            "model": self.config.model,
            "temperature": self.config.temperature,
            "response_format": {"type": "json_object"},
            "messages": [
                {
                    "role": "system",
                    "content": "Tu es un analyste SDR B2B. Reponds uniquement en JSON valide.",
                },
                {"role": "user", "content": prompt},
            ],
        }
        headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://local.sdr-ai",
            "X-Title": "SDR IA LinkedIn Hermes",
        }
        url = f"{self.config.base_url.rstrip('/')}/chat/completions"
        response = self.client.post(url, headers=headers, json=payload)
        response.raise_for_status()
        data = response.json()
        content = data["choices"][0]["message"]["content"]
        parsed: dict[str, Any] = json.loads(content)
        signals = [str(x) for x in parsed.get("signals", [])]
        score = int(parsed.get("intent_count", len(signals)))
        explanation = str(parsed.get("explanation", ""))
        return max(score, 0), signals, explanation


def _build_prompt(prospect: Prospect, offer: Offer, posts: list[ActivitySignal]) -> str:
    post_payload = [
        {"kind": p.kind, "date": p.created_at.isoformat() if p.created_at else None, "text": p.text[:1200]}
        for p in posts[:20]
    ]
    return json.dumps(
        {
            "task": "Detecter les signaux d'intention LinkedIn pour qualifier un prospect WARM en HOT.",
            "prospect": {
                "name": prospect.full_name,
                "title": prospect.title,
                "company": prospect.company,
                "industry": prospect.industry,
            },
            "offer": offer.model_dump(mode="json"),
            "signals_to_find": [
                "douleur que l'offre resout",
                "recherche active d'un prestataire ou d'une solution",
                "mention ou engagement envers un concurrent direct",
                "changement de poste recent",
                "croissance ou scaling d'equipe",
                "interet marche lie a l'offre",
            ],
            "posts": post_payload,
            "output_schema": {
                "intent_count": "integer >= 0",
                "signals": ["phrases courtes, factuelles, citees depuis les posts"],
                "explanation": "max 280 caracteres",
            },
        },
        ensure_ascii=False,
    )
