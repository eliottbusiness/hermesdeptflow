from __future__ import annotations

import time
from typing import Any

import httpx

from .config import BeReachConfig
from .models import ActivitySignal, ICP, Prospect
from .utils import parse_datetime


class BeReachError(RuntimeError):
    pass


class BeReachClient:
    def __init__(self, config: BeReachConfig, client: httpx.Client | None = None) -> None:
        self.config = config
        self.client = client or httpx.Client(timeout=config.timeout_seconds)

    def close(self) -> None:
        self.client.close()

    def _post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        if self.config.dry_run:
            return _dry_response(path, payload)
        if not self.config.api_key:
            raise BeReachError("BEREACH_API_KEY manquant")
        url = f"{self.config.base_url}{path}"
        headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        attempts = self.config.max_retries + 1
        last_error = ""
        for idx in range(attempts):
            try:
                resp = self.client.post(url, headers=headers, json=payload)
            except httpx.HTTPError as exc:
                last_error = str(exc)
                if idx < attempts - 1:
                    time.sleep(2**idx)
                    continue
                raise BeReachError(f"Erreur reseau BeReach: {exc}") from exc

            if resp.status_code < 400:
                try:
                    data = resp.json()
                except ValueError as exc:
                    raise BeReachError(f"Reponse BeReach non JSON: {resp.text[:300]}") from exc
                if isinstance(data, dict):
                    return data
                return {"data": data}

            retry_after = resp.headers.get("retry-after")
            body = resp.text[:500]
            last_error = f"HTTP {resp.status_code}: {body}"
            if resp.status_code in {429, 500, 502, 503, 504} and idx < attempts - 1:
                wait = float(retry_after) if retry_after and retry_after.isdigit() else 2**idx
                time.sleep(wait)
                continue
            raise BeReachError(f"Erreur BeReach {last_error}")
        raise BeReachError(f"Erreur BeReach apres retries: {last_error}")

    def search_people(self, icp: ICP, limit: int = 50) -> list[Prospect]:
        payload: dict[str, Any] = {
            "keywords": " OR ".join(icp.titres_cibles),
            "filters": {
                "industry": icp.secteurs_activite,
                "companySize": icp.taille_entreprise,
                "location": icp.localisation,
                "seniority": icp.seniorite,
            },
            "limit": limit,
        }
        data = self._post("/search/linkedin/people", payload)
        raw_people = _extract_list(data, ["people", "results", "data", "items"])
        return [normalize_prospect(item) for item in raw_people]

    def collect_profile(self, linkedin_url: str) -> Prospect:
        data = self._post("/collect/linkedin/profile", {"profileUrl": linkedin_url})
        raw = data.get("profile") or data.get("data") or data
        return normalize_prospect(raw)

    def collect_posts(self, linkedin_url: str, days: int = 45) -> list[ActivitySignal]:
        data = self._post("/collect/linkedin/posts", {"profileUrl": linkedin_url, "days": days})
        raw_posts = _extract_list(data, ["posts", "activities", "results", "data", "items"])
        signals: list[ActivitySignal] = []
        for item in raw_posts:
            kind = str(item.get("kind") or item.get("type") or item.get("activityType") or "post").lower()
            text = str(item.get("text") or item.get("content") or item.get("comment") or "")
            created = parse_datetime(
                item.get("createdAt") or item.get("created_at") or item.get("date") or item.get("publishedAt")
            )
            signals.append(
                ActivitySignal(
                    kind=kind,
                    text=text,
                    created_at=created,
                    url=str(item.get("url") or item.get("postUrl") or ""),
                    raw=item,
                )
            )
        return signals

    def visit_profile(self, linkedin_url: str) -> dict[str, Any]:
        return self._post("/visit/linkedin/profile", {"profileUrl": linkedin_url})

    def connect_profile(self, linkedin_url: str) -> dict[str, Any]:
        return self._post("/connect/linkedin/profile", {"profileUrl": linkedin_url, "message": ""})


def _extract_list(data: dict[str, Any], keys: list[str]) -> list[dict[str, Any]]:
    current: Any = data
    for key in keys:
        if isinstance(data.get(key), list):
            return [x for x in data[key] if isinstance(x, dict)]
        if isinstance(current, dict) and isinstance(current.get(key), list):
            return [x for x in current[key] if isinstance(x, dict)]
    if isinstance(data.get("data"), dict):
        nested = data["data"]
        for key in keys:
            if isinstance(nested.get(key), list):
                return [x for x in nested[key] if isinstance(x, dict)]
    return []


def normalize_prospect(item: dict[str, Any]) -> Prospect:
    profile = item.get("profile") if isinstance(item.get("profile"), dict) else item
    company = profile.get("company") if isinstance(profile.get("company"), dict) else {}
    name = str(profile.get("name") or profile.get("fullName") or "").strip()
    first = str(profile.get("firstName") or profile.get("first_name") or "")
    last = str(profile.get("lastName") or profile.get("last_name") or "")
    if not first and name:
        parts = name.split()
        first = parts[0]
        last = " ".join(parts[1:])
    return Prospect(
        first_name=first,
        last_name=last,
        title=str(profile.get("title") or profile.get("headline") or profile.get("jobTitle") or ""),
        company=str(
            profile.get("companyName")
            or profile.get("currentCompany")
            or company.get("name")
            or ""
        ),
        linkedin_url=str(
            profile.get("linkedinUrl")
            or profile.get("profileUrl")
            or profile.get("url")
            or item.get("url")
            or ""
        ),
        location=str(profile.get("location") or profile.get("geo") or ""),
        industry=str(profile.get("industry") or company.get("industry") or ""),
        company_size=str(profile.get("companySize") or company.get("size") or ""),
        raw=item,
    )


def _dry_response(path: str, payload: dict[str, Any]) -> dict[str, Any]:
    if path == "/search/linkedin/people":
        people = [
            {
                "fullName": "Camille Durand",
                "headline": "Head of Sales",
                "company": {"name": "Demo SaaS", "size": "51-200", "industry": "SaaS B2B"},
                "profileUrl": "https://www.linkedin.com/in/camille-durand-demo",
                "location": "Paris, France",
            },
            {
                "fullName": "Noah Martin",
                "headline": "Etudiant marketing",
                "company": {"name": "University", "size": "1000+", "industry": "Education"},
                "profileUrl": "https://www.linkedin.com/in/noah-martin-demo",
                "location": "Paris, France",
            },
        ]
        return {"people": people[: int(payload.get("limit", 50))]}
    if path == "/collect/linkedin/profile":
        url = str(payload.get("profileUrl", ""))
        if "noah" in url:
            return {
                "profile": {
                    "fullName": "Noah Martin",
                    "headline": "Etudiant marketing",
                    "company": {"name": "University", "size": "1000+", "industry": "Education"},
                    "profileUrl": url,
                    "location": "Paris, France",
                }
            }
        return {
            "profile": {
                "fullName": "Camille Durand",
                "headline": "Head of Sales",
                "company": {"name": "Demo SaaS", "size": "51-200", "industry": "SaaS B2B"},
                "profileUrl": url,
                "location": "Paris, France",
            }
        }
    if path == "/collect/linkedin/posts":
        url = str(payload.get("profileUrl", ""))
        if "noah" in url:
            return {"posts": []}
        return {
            "posts": [
                {
                    "type": "post",
                    "text": "On cherche a ameliorer notre pipeline et reduire la prospection manuelle.",
                    "date": "2026-04-20T09:00:00Z",
                },
                {
                    "type": "like",
                    "text": "Post Waalaxy sur cold outreach",
                    "date": "2026-04-18T11:00:00Z",
                },
            ]
        }
    if path in {"/visit/linkedin/profile", "/connect/linkedin/profile"}:
        return {"success": True, "dry_run": True}
    return {"success": True, "dry_run": True}
