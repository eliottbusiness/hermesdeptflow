---
name: sdr-ai-daily-run
description: Execute le pipeline quotidien SDR IA LinkedIn via le CLI Python du repo.
version: 1.0.0
platforms: [linux, macos]
metadata:
  hermes:
    tags: [sdr, linkedin, bereach, google-sheets, automation]
    category: sales
    requires_toolsets: [terminal]
---
# SDR IA Daily Run

## When to Use
- Lancer le run quotidien SDR LinkedIn pour un profil client.
- Executer recherche ICP, qualification, CRM, envoi de connexions et rapport.

## Procedure
1. Identifier le fichier config client: par convention `${SDR_AI_CONFIG}` ou `configs/clients/<slug>.yaml`.
2. Depuis le repo installe, executer:
   `sdr-ai run --config "$SDR_AI_CONFIG" --limit 50`
3. Sur erreur d'une etape, conserver les logs sous `runs/<client>/` et continuer les autres etapes si possible.
4. Le rapport final doit rester sous 15 lignes.

## Verification
- Verifier que le fichier `runs/<client>/<run_id>.json` existe.
- Verifier que le Google Sheet contient les nouveaux WARM/HOT.
- Verifier que les quotas ne depassent pas les limites configurees.
