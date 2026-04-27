---
name: daily-report
description: Genere et livre le rapport quotidien SDR IA.
version: 1.0.0
platforms: [linux, macos]
metadata:
  hermes:
    tags: [reporting, telegram, discord]
    category: sales
---
# Daily Report

## Procedure
Utiliser `sdr_ai.notifications.format_daily_report`.
Inclure:
- prospects trouves;
- WARM/HOT/rejetes;
- taux de qualification;
- ajouts CRM et doublons;
- connexions envoyees;
- quota restant semaine;
- top 3 prospects.

## Verification
- Max 15 lignes.
- Alertes quota a 70% et 90%.
