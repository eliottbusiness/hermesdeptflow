from __future__ import annotations

from pathlib import Path

from .config import BeReachConfig, ClientConfig, DeliveryConfig, GoogleConfig, HermesConfig, LLMConfig, save_config
from .models import ICP, Offer
from .utils import slugify


ICP_TEMPLATE = """=== ICP CLIENT ===

TITRES_CIBLES:
  - Directeur Commercial
  - Head of Sales
SENIORITE:
  - Director
  - VP
SECTEURS_ACTIVITE:
  - SaaS B2B
TAILLE_ENTREPRISE:
  - 11-50
  - 51-200
LOCALISATION:
  - France
TECHNOLOGIES_STACK:
  - HubSpot
ANNEES_EXPERIENCE_MIN: 5
SIGNAUX_INTENTION_CLES:
  - parle de prospection B2B
  - mentionne scaling equipe
TITRES_A_EXCLURE:
  - Freelance
  - Etudiant
SECTEURS_A_EXCLURE:
  - MLM
"""

OFFER_TEMPLATE = """=== OFFRE CLIENT ===

NOM_OFFRE: SDR IA LinkedIn
PROBLEME_RESOLU:
  - Manque de prospects qualifies reguliers
  - Temps perdu sur la prospection manuelle LinkedIn
BENEFICE_PRINCIPAL: 15 prospects qualifies par jour sans effort manuel
MOTS_CLES_INTENTION:
  - prospection
  - cold outreach
  - pipeline
  - leads B2B
CONCURRENTS_OU_ALTERNATIVES:
  - Lemlist
  - LaGrowthMachine
  - Waalaxy
  - PhantomBuster
"""


def create_client_config(
    client_name: str,
    output_path: str | Path,
    bereach_api_key: str = "${BEREACH_API_KEY}",
    delivery_channel: str = "telegram",
    telegram_chat_id: str = "",
    discord_webhook_url: str = "${DISCORD_WEBHOOK_URL}",
    google_service_account_file: str = "${GOOGLE_APPLICATION_CREDENTIALS}",
    dry_run: bool = True,
) -> ClientConfig:
    slug = slugify(client_name)
    cfg = ClientConfig(
        client_name=client_name,
        slug=slug,
        icp=ICP(
            titres_cibles=["Directeur Commercial", "Head of Sales"],
            seniorite=["Director", "VP"],
            secteurs_activite=["SaaS B2B"],
            taille_entreprise=["11-50", "51-200"],
            localisation=["France"],
            technologies_stack=["HubSpot"],
            annees_experience_min=5,
            signaux_intention_cles=["parle de prospection B2B", "mentionne scaling equipe"],
            titres_a_exclure=["Freelance", "Etudiant"],
            secteurs_a_exclure=["MLM"],
        ),
        offre=Offer(
            nom_offre="SDR IA LinkedIn",
            probleme_resolu=[
                "Manque de prospects qualifies reguliers",
                "Temps perdu sur la prospection manuelle LinkedIn",
            ],
            benefice_principal="15 prospects qualifies par jour sans effort manuel",
            mots_cles_intention=["prospection", "cold outreach", "pipeline", "leads B2B"],
            concurrents_ou_alternatives=["Lemlist", "LaGrowthMachine", "Waalaxy", "PhantomBuster"],
        ),
        bereach=BeReachConfig(api_key=bereach_api_key, dry_run=dry_run),
        google=GoogleConfig(service_account_file=google_service_account_file),
        delivery=DeliveryConfig(channel=delivery_channel, telegram_chat_id=telegram_chat_id, discord_webhook_url=discord_webhook_url),
        llm=LLMConfig(),
        hermes=HermesConfig(profile_slug=slug, delivery_target=delivery_channel),
    )
    save_config(cfg, output_path)
    return cfg


def write_memory_file(cfg: ClientConfig, path: str | Path) -> None:
    content = f"""# MEMORY - SDR IA - {cfg.client_name}

## ICP

```yaml
{cfg.icp.model_dump_json(indent=2)}
```

## OFFRE

```yaml
{cfg.offre.model_dump_json(indent=2)}
```

## REGLES SDR

- Qualification sequentielle: ICP puis activite 45 jours puis intention.
- REJETE n'entre jamais dans le CRM.
- WARM/HOT entrent dans le CRM puis sont envoyes selon priorite et quotas.
- Demande de connexion sans note.
"""
    file_path = Path(path).expanduser()
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(content, encoding="utf-8")
