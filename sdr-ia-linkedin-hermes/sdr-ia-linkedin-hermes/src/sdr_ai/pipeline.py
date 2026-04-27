from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Protocol
from uuid import uuid4

from .bereach import BeReachClient
from .config import ClientConfig
from .crm import GoogleSheetsCRM, LocalCSVCRM
from .llm import LLMIntentAnalyzer
from .models import QualificationStatus, RunReport, ScoringResult
from .notifications import Notifier, format_daily_report, notifier_from_config
from .quota import QuotaManager, working_window_ok
from .scoring import ProspectScorer
from .utils import sleep_jitter


class CRMWriter(Protocol):
    def append_results(self, results: list[ScoringResult]) -> tuple[int, int]: ...
    def update_connection_sent(self, linkedin_url: str) -> bool: ...


class SDRPipeline:
    def __init__(
        self,
        config: ClientConfig,
        bereach: BeReachClient | None = None,
        crm: CRMWriter | None = None,
        notifier: Notifier | None = None,
        quota: QuotaManager | None = None,
    ) -> None:
        self.config = config
        self.bereach = bereach or BeReachClient(config.bereach)
        self.llm = LLMIntentAnalyzer(config.llm) if config.llm.enabled else None
        self.scorer = ProspectScorer(config, llm=self.llm)
        self.crm = crm or (
            LocalCSVCRM(config) if config.bereach.dry_run else GoogleSheetsCRM(config)
        )
        self.notifier = notifier or notifier_from_config(config)
        self.quota = quota or QuotaManager(config)

    def run_daily(self, limit: int = 50, send_connections: bool = True) -> RunReport:
        report = RunReport(
            run_id=str(uuid4()),
            started_at=datetime.now(tz=UTC),
            weekly_connection_limit=self.config.bereach.weekly_connection_limit,
        )
        try:
            prospects = self.bereach.search_people(self.config.icp, limit=limit)
            report.found_count = len(prospects)
        except Exception as exc:  # noqa: BLE001
            report.errors.append(f"search_people: {exc}")
            prospects = []

        scored: list[ScoringResult] = []
        for prospect in prospects:
            try:
                enriched = self.bereach.collect_profile(prospect.linkedin_url) if prospect.linkedin_url else prospect
                activities = self.bereach.collect_posts(enriched.linkedin_url, days=45) if enriched.linkedin_url else []
                scored.append(self.scorer.score(enriched, activities))
            except Exception as exc:  # noqa: BLE001
                report.errors.append(f"score {prospect.linkedin_url or prospect.full_name}: {exc}")

        self._hydrate_counts(report, scored)

        try:
            added, dedup = self.crm.append_results(scored)
            report.added_to_crm = added
            report.deduplicated = dedup
        except Exception as exc:  # noqa: BLE001
            report.errors.append(f"crm append: {exc}")

        if send_connections:
            sent, errors = self.send_connections(scored)
            report.connections_sent = sent
            report.connection_errors = errors

        report.weekly_connection_used = self.quota.state.weekly_connections
        report.ended_at = datetime.now(tz=UTC)
        self._write_run_log(report, scored)
        try:
            self.notifier.send(format_daily_report(report, self.config.client_name))
        except Exception as exc:  # noqa: BLE001
            report.errors.append(f"notification: {exc}")
        return report

    def send_connections(self, scored: list[ScoringResult]) -> tuple[int, int]:
        if not working_window_ok(self.config) and not self.config.bereach.dry_run:
            return 0, 0
        candidates = sorted(
            [s for s in scored if s.status in {QualificationStatus.HOT, QualificationStatus.WARM}],
            key=lambda s: s.priorite_interne,
            reverse=True,
        )
        sent = 0
        errors = 0
        for result in candidates:
            if not self.quota.can_connect():
                break
            if self.quota.weekly_usage_ratio() >= 0.9:
                break
            url = result.prospect.linkedin_url
            if not url:
                continue
            try:
                if self.quota.can_visit():
                    if not self.config.bereach.dry_run:
                        self.bereach.visit_profile(url)
                    self.quota.register_visit()
                    sleep_jitter(
                        self.config.bereach.jitter_min_seconds,
                        self.config.bereach.jitter_max_seconds,
                        dry_run=self.config.bereach.dry_run,
                    )
                if not self.config.bereach.dry_run:
                    self.bereach.connect_profile(url)
                self.quota.register_connection()
                self.crm.update_connection_sent(url)
                sent += 1
                sleep_jitter(
                    self.config.bereach.delay_between_connections_min_seconds,
                    self.config.bereach.delay_between_connections_max_seconds,
                    dry_run=self.config.bereach.dry_run,
                )
            except Exception:  # noqa: BLE001
                errors += 1
        return sent, errors

    @staticmethod
    def _hydrate_counts(report: RunReport, scored: list[ScoringResult]) -> None:
        report.qualified_count = sum(1 for s in scored if s.qualified)
        report.warm_count = sum(1 for s in scored if s.status == QualificationStatus.WARM)
        report.hot_count = sum(1 for s in scored if s.status == QualificationStatus.HOT)
        report.rejected_count = sum(1 for s in scored if s.status == QualificationStatus.REJECTED)
        report.top_prospects = sorted(
            [s for s in scored if s.qualified], key=lambda s: s.priorite_interne, reverse=True
        )[:3]

    def _write_run_log(self, report: RunReport, scored: list[ScoringResult]) -> None:
        out_dir = Path("runs") / self.config.slug
        out_dir.mkdir(parents=True, exist_ok=True)
        payload: dict[str, Any] = {
            "report": report.model_dump(mode="json"),
            "scored": [s.model_dump(mode="json") for s in scored],
        }
        (out_dir / f"{report.run_id}.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=2, default=str), encoding="utf-8"
        )
