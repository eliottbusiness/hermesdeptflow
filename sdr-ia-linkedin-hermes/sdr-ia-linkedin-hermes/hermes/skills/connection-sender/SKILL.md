---
name: connection-sender
description: Envoie des demandes de connexion BeReach aux prospects qualifies en respectant quotas et jitter.
version: 1.0.0
platforms: [linux, macos]
metadata:
  hermes:
    tags: [linkedin, bereach, anti-ban, quota]
    category: sales
    requires_toolsets: [terminal]
---
# Connection Sender

## Procedure
1. Trier WARM/HOT par priorite decroissante.
2. Verifier quota jour/semaine avant chaque action.
3. Visiter le profil via BeReach.
4. Attendre jitter 3-8 secondes.
5. Envoyer la connexion sans note.
6. Mettre a jour le statut CRM `DEMANDE_ENVOYEE`.
7. Attendre 5-10 secondes avant le prospect suivant.
8. Stopper si quota semaine >90%.

## Verification
- Aucun envoi hors heures ouvrables si active.
- Le compteur quota local est mis a jour.
