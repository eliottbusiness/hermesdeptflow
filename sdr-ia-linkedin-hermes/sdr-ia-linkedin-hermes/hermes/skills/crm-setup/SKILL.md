---
name: crm-setup
description: Cree ou initialise le Google Sheets CRM d'un client SDR IA.
version: 1.0.0
platforms: [linux, macos]
metadata:
  hermes:
    tags: [google-sheets, crm, setup]
    category: sales
    requires_toolsets: [terminal]
---
# CRM Setup

## Procedure
Executer:
`sdr-ai setup-crm --config configs/clients/<slug>.yaml`

Le CLI doit:
1. Creer/ouvrir le fichier `<NomClient> - CRM PROSPECTION`.
2. Initialiser les onglets `PROSPECTS` et `REJETES`.
3. Ecrire les colonnes obligatoires.
4. Sauvegarder `spreadsheet_id` dans la config.

## Verification
- La ligne 1 contient les colonnes CRM.
- Le fichier config contient `google.spreadsheet_id`.
