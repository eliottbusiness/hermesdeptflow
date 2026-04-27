from __future__ import annotations

from typing import Protocol

import httpx

from .config import ClientConfig
from .models import RunReport


class Notifier(Protocol):
    def send(self, message: str) -> None: ...


class NullNotifier:
    def send(self, message: str) -> None:
        print(message)


class TelegramNotifier:
    def __init__(self, bot_token: str, chat_id: str, client: httpx.Client | None = None) -> None:
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.client = client or httpx.Client(timeout=20)

    def send(self, message: str) -> None:
        if not self.bot_token or not self.chat_id:
            raise ValueError("Telegram bot_token/chat_id manquant")
        self.client.post(
            f"https://api.telegram.org/bot{self.bot_token}/sendMessage",
            json={"chat_id": self.chat_id, "text": message, "parse_mode": "Markdown"},
        ).raise_for_status()


class DiscordNotifier:
    def __init__(self, webhook_url: str, client: httpx.Client | None = None) -> None:
        self.webhook_url = webhook_url
        self.client = client or httpx.Client(timeout=20)

    def send(self, message: str) -> None:
        if not self.webhook_url:
            raise ValueError("Discord webhook_url manquant")
        self.client.post(self.webhook_url, json={"content": message}).raise_for_status()


def notifier_from_config(config: ClientConfig) -> Notifier:
    channel = config.delivery.channel.lower()
    if channel == "telegram":
        return TelegramNotifier(config.delivery.telegram_bot_token, config.delivery.telegram_chat_id)
    if channel == "discord":
        return DiscordNotifier(config.delivery.discord_webhook_url)
    return NullNotifier()


def format_daily_report(report: RunReport, client_name: str) -> str:
    rate = round(report.qualification_rate() * 100, 1)
    quota_left = max(report.weekly_connection_limit - report.weekly_connection_used, 0)
    lines = [
        f"🤖 SDR IA — {client_name}",
        f"🔎 Trouves: {report.found_count} | Qualifies: {report.qualified_count} ({rate}%)",
        f"🟡 WARM: {report.warm_count} | 🔴 HOT: {report.hot_count} | Rejetes: {report.rejected_count}",
        f"📥 Ajoutes CRM: {report.added_to_crm} | Doublons: {report.deduplicated}",
        f"🤝 Connexions envoyees: {report.connections_sent}",
        f"🧯 Quota semaine restant: {quota_left}/{report.weekly_connection_limit}",
    ]
    if report.top_prospects:
        lines.append("🏆 Top prospects:")
        for item in report.top_prospects[:3]:
            p = item.prospect
            lines.append(f"- {p.full_name or p.linkedin_url} — {p.title} — score {item.priorite_interne}")
    if report.errors:
        lines.append(f"⚠️ Erreurs: {len(report.errors)} — voir logs")
    if report.weekly_connection_limit and report.weekly_connection_used / report.weekly_connection_limit >= 0.9:
        lines.append("🚨 Quota semaine >90%: envois bloques/ralentis.")
    elif report.weekly_connection_limit and report.weekly_connection_used / report.weekly_connection_limit >= 0.7:
        lines.append("⚠️ Quota semaine >70%: vigilance.")
    return "\n".join(lines[:15])
