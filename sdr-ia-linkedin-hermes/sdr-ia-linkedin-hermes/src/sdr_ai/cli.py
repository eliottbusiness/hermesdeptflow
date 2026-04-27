from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path
from typing import NoReturn

from .config import ClientConfig, load_config, save_config
from .crm import GoogleSheetsCRM
from .hermes_install import ensure_hermes_profile, install_client_profile_files, install_skills
from .onboarding import create_client_config
from .pipeline import SDRPipeline


def main() -> None:
    parser = argparse.ArgumentParser(prog="sdr-ai", description="SDR IA LinkedIn Hermes")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_init = sub.add_parser("init-client", help="Cree une config client template")
    p_init.add_argument("--name", required=True, help="Nom client")
    p_init.add_argument("--out", default="configs/clients/client.yaml")
    p_init.add_argument("--bereach-api-key", default="${BEREACH_API_KEY}")
    p_init.add_argument("--delivery", choices=["telegram", "discord", "none"], default="telegram")
    p_init.add_argument("--telegram-chat-id", default="")
    p_init.add_argument("--dry-run", action="store_true", default=False)

    p_crm = sub.add_parser("setup-crm", help="Cree/initialise Google Sheets CRM")
    p_crm.add_argument("--config", required=True)

    p_run = sub.add_parser("run", help="Lance le pipeline SDR quotidien")
    p_run.add_argument("--config", required=True)
    p_run.add_argument("--limit", type=int, default=50)
    p_run.add_argument("--no-send", action="store_true", help="Ne pas envoyer les connexions")

    p_skills = sub.add_parser("install-hermes", help="Installe les skills Hermes et fichiers profil")
    p_skills.add_argument("--config", required=False)
    p_skills.add_argument("--hermes-home", default="~/.hermes")
    p_skills.add_argument("--create-cron", action="store_true")

    p_cron = sub.add_parser("create-cron", help="Cree le cron Hermes pour un client")
    p_cron.add_argument("--config", required=True)

    args = parser.parse_args()
    if args.cmd == "init-client":
        cfg = create_client_config(
            client_name=args.name,
            output_path=args.out,
            bereach_api_key=args.bereach_api_key,
            delivery_channel=args.delivery,
            telegram_chat_id=args.telegram_chat_id,
            dry_run=args.dry_run,
        )
        print(f"Config creee: {args.out}")
        print(f"Slug client: {cfg.slug}")
        return

    if args.cmd == "setup-crm":
        cfg = load_config(args.config)
        crm = GoogleSheetsCRM(cfg)
        url = crm.setup()
        save_config(cfg, args.config)
        print(f"CRM pret: {url}")
        print("Config mise a jour avec spreadsheet_id si necessaire")
        return

    if args.cmd == "run":
        cfg = load_config(args.config)
        report = SDRPipeline(cfg).run_daily(limit=args.limit, send_connections=not args.no_send)
        print(json.dumps(report.model_dump(mode="json"), ensure_ascii=False, indent=2))
        return

    if args.cmd == "install-hermes":
        written = install_skills(args.hermes_home)
        print(f"Skills globaux installes: {len(written)}")
        if args.config:
            cfg = load_config(args.config)
            ensure_hermes_profile(cfg)
            profile_dir = install_client_profile_files(cfg, args.hermes_home)
            print(f"Profil Hermes alimente: {profile_dir}")
            if args.create_cron:
                _run_cron_create(cfg)
        return

    if args.cmd == "create-cron":
        cfg = load_config(args.config)
        _run_cron_create(cfg)
        return

    _die("Commande inconnue")


def _run_cron_create(cfg: ClientConfig) -> None:
    schedule = cfg.hermes.cron_schedule
    slug = cfg.hermes.profile_slug
    delivery = cfg.hermes.delivery_target
    prompt = (
        "Execute le pipeline SDR LinkedIn quotidien avec le skill sdr-ai-daily-run. "
        "Respecte les quotas, continue en cas d'erreur d'une etape et livre le rapport final."
    )
    cmd = [
        "hermes",
        "-p",
        slug,
        "cron",
        "create",
        schedule,
        prompt,
        "--skill",
        "sdr-ai-daily-run",
        "--name",
        f"SDR-Daily-{slug}",
        "--deliver",
        delivery,
    ]
    print("Commande Hermes:", " ".join(cmd))
    subprocess.run(cmd, check=True)


def _die(message: str) -> NoReturn:
    raise SystemExit(message)


if __name__ == "__main__":
    main()
