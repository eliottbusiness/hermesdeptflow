# QA Report

Date: 2026-04-27

## Controles effectues dans le sandbox

- Structure repo creee et verifiee.
- Compilation syntaxique Python:
  - Commande: `/usr/bin/python3 -m compileall -q src tests`
  - Resultat: OK
- Verification manuelle des chemins critiques:
  - CLI: `sdr_ai.cli`
  - Pipeline: `sdr_ai.pipeline`
  - BeReach client: `sdr_ai.bereach`
  - CRM Sheets: `sdr_ai.crm`
  - Scoring: `sdr_ai.scoring`
  - Quotas: `sdr_ai.quota`

## Tests inclus dans le repo

- `tests/test_scoring.py`: WARM/HOT/REJETE et priorite.
- `tests/test_bereach_normalization.py`: normalisation payload BeReach.
- `tests/test_quota.py`: blocage quota jour.

## A executer dans le repo cible

```bash
scripts/install.sh
source .venv/bin/activate
pytest -q
ruff check src tests
```

## Limites de validation

Les appels externes reels n'ont pas ete executes dans le sandbox car ils requierent:

- une cle BeReach active;
- un service account Google avec Drive/Sheets;
- un token Telegram ou webhook Discord;
- optionnellement une cle OpenRouter.

Le code inclut un mode `dry_run` et un CRM CSV local pour valider le pipeline sans toucher aux comptes externes.
