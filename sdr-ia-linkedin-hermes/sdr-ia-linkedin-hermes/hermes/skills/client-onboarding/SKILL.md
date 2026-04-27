---
name: client-onboarding
description: Cree et configure un nouveau profil client SDR LinkedIn Hermes.
version: 1.0.0
platforms: [linux, macos]
metadata:
  hermes:
    tags: [sdr, onboarding, crm, hermes-profile]
    category: sales
    requires_toolsets: [terminal]
---
# Client Onboarding SDR IA

## When to Use
Quand l'utilisateur dit: nouveau client, creer profil, onboarding client, setup client SDR.

## Procedure
Poser les questions une par une:
1. Nom de l'entreprise cliente.
2. Cle API BeReach du client.
3. Canal de livraison: telegram, discord ou none.
4. Token/chat Telegram ou webhook Discord.
5. ICP complet selon le template du repo.
6. Offre complete selon le template du repo.
7. Limite de demandes de connexion par jour, recommande 10-12.
8. Heure de prospection quotidienne, format HH:MM.

Ensuite executer depuis le repo:
1. `sdr-ai init-client --name "<NomClient>" --out configs/clients/<slug>.yaml --bereach-api-key "<key>" --delivery <channel>`
2. Editer `configs/clients/<slug>.yaml` pour inserer ICP/OFFRE exacts.
3. `sdr-ai setup-crm --config configs/clients/<slug>.yaml`
4. `sdr-ai install-hermes --config configs/clients/<slug>.yaml --create-cron`

## Verification
- Le profil Hermes existe.
- `MEMORY.md` contient ICP + OFFRE.
- Le Google Sheet contient les onglets PROSPECTS et REJETES.
- Le cron Hermes est liste avec `hermes -p <slug> cron list`.
