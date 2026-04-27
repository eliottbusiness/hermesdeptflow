---
name: crm-updater
description: Ajoute les prospects qualifies au Google Sheets CRM avec deduplication LinkedIn URL.
version: 1.0.0
platforms: [linux, macos]
metadata:
  hermes:
    tags: [google-sheets, crm]
    category: sales
    requires_toolsets: [terminal]
---
# CRM Updater

## Procedure
Utiliser `GoogleSheetsCRM.append_results`.
Pour chaque WARM/HOT:
- dedupliquer par `url_linkedin`;
- ajouter une ligne complete;
- statut initial `NOUVEAU`;
- conserver `statut_qualification` WARM/HOT.

## Verification
- Le nombre ajoutes/doublons est logge.
- Les colonnes correspondent a `sdr_ai.models.CRM_COLUMNS`.
