# SDR IA LinkedIn Hermes x BeReach

Repo pret a mettre dans GitHub pour deployer un agent SDR LinkedIn multi-clients avec Hermes Agent, BeReach, Google Sheets, Telegram/Discord et scoring IA.

## Ce qui est inclus

- Pipeline Python executable en CLI: `sdr-ai run`.
- Client BeReach robuste avec retry, erreur explicite, URL de base configurable.
- Qualification sequentielle: ICP -> activite LinkedIn -45j -> intention.
- Scoring IA optionnel via OpenRouter, avec heuristiques de secours.
- CRM Google Sheets avec colonnes standard, deduplication par URL LinkedIn, mise a jour statut connexion.
- Quotas anti-ban: limites jour/semaine, visites, pauses, jitter et blocage a 90% de quota semaine.
- Notifications Telegram/Discord.
- Skills Hermes installables.
- Onboarding client et templates ICP/OFFRE.
- Tests unitaires et GitHub Actions.
- Dockerfile et scripts d'installation.

## Installation rapide sur Google VM

```bash
git clone <ton-repo> sdr-ia-linkedin-hermes
cd sdr-ia-linkedin-hermes
scripts/install.sh
source .venv/bin/activate
cp .env.example .env
```

Installe Hermes si necessaire:

```bash
scripts/install_hermes.sh
hermes setup
```

## Creer un client

```bash
source .venv/bin/activate
scripts/bootstrap_client.sh "Acme SaaS"
```

Puis edite `configs/clients/acme-saas.yaml` avec:

- `bereach.api_key`
- `google.service_account_file`
- `delivery.telegram_chat_id` ou `delivery.discord_webhook_url`
- ICP et OFFRE exacts
- `bereach.dry_run: false` quand tu veux vraiment envoyer

## Initialiser le CRM

```bash
sdr-ai setup-crm --config configs/clients/acme-saas.yaml
```

Le CLI cree/initialise le Google Sheet et met a jour `spreadsheet_id` dans la config.

## Installer les skills Hermes et le cron

```bash
sdr-ai install-hermes --config configs/clients/acme-saas.yaml --create-cron
```

Le cron par defaut est `0 6 * * 1-5`: tous les jours de semaine a 06:00.

## Lancer un run manuel

Mode test sans envoyer les connexions:

```bash
sdr-ai run --config configs/clients/acme-saas.yaml --limit 10 --no-send
```

Mode complet:

```bash
sdr-ai run --config configs/clients/acme-saas.yaml --limit 50
```

## Variables d'environnement

Voir `.env.example`.

La config YAML peut contenir `${BEREACH_API_KEY}`, `${OPENROUTER_API_KEY}`, `${GOOGLE_APPLICATION_CREDENTIALS}`, etc. Le loader les remplace automatiquement.

## Architecture

```text
src/sdr_ai/
  bereach.py       Client API BeReach
  scoring.py       ICP, activite, intention, WARM/HOT/REJETE
  llm.py           Analyse intention OpenRouter optionnelle
  crm.py           Google Sheets + CSV local dry-run
  quota.py         Quotas jour/semaine et fenetre horaire
  notifications.py Telegram/Discord/reporting
  pipeline.py      Orchestration quotidienne
  onboarding.py    Creation config/MEMORY
  hermes_install.py Installation skills/profil Hermes
  cli.py           Commande sdr-ai
hermes/skills/     Skills Hermes au format dossier/SKILL.md
configs/           Exemple config client
scripts/           Install, Hermes, bootstrap client
runs/              Logs JSON locaux par run
```

## Colonnes CRM

Le CRM contient exactement les colonnes suivantes:

`id | date_ajout | prenom | nom | titre | entreprise | url_linkedin | localisation | secteur | taille_entreprise | statut_qualification | nb_signaux_activite | nb_signaux_intention | priorite_interne | signaux_detectes | dernier_post | statut | date_connexion_envoyee | date_connexion_acceptee | notes | source_run`

## Notes d'exploitation

- Commence avec `daily_connection_limit: 5` pendant les premiers jours si le compte LinkedIn est froid.
- Active `dry_run: true` pendant la configuration client.
- Le code bloque les envois hors heures ouvrables et le week-end si configure.
- `REJETE` n'est pas ajoute dans l'onglet PROSPECTS.
- `LocalCSVCRM` est utilise automatiquement en dry-run pour tester sans Google Sheets.

## Qualite

```bash
python -m compileall -q src tests
pytest -q
ruff check src tests
```

Le pipeline degrade proprement si le LLM est indisponible: les heuristiques continuent de scorer les signaux d'intention.

## Points a verifier avec tes vrais comptes

1. La forme exacte de certains payloads BeReach peut evoluer: `bereach.py` normalise plusieurs noms de champs (`profileUrl`, `linkedinUrl`, `headline`, `company.size`, etc.).
2. Le domaine BeReach est configurable: `https://api.bereach.ai` par defaut, modifiable vers `https://api.berea.ch` si ton compte l'exige.
3. Les actions LinkedIn doivent respecter les conditions de BeReach/LinkedIn et les quotas de securite.
