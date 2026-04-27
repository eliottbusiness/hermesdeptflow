---
name: prospect-qualifier
description: Qualifie les prospects selon ICP, activite 45 jours et intention.
version: 1.0.0
platforms: [linux, macos]
metadata:
  hermes:
    tags: [scoring, qualification, llm]
    category: sales
    requires_toolsets: [terminal]
---
# Prospect Qualifier

## Procedure
Appliquer le pipeline strict:
1. ICP check binaire: titre, seniorite, taille, localisation. Secteur = indice souple.
2. Activite LinkedIn 45 jours via BeReach posts. Zero signal = REJETE.
3. Intention: heuristique + LLM optionnel contre OFFRE.
4. Statut final: REJETE, WARM ou HOT.
5. Priorite interne = nb_signaux_intention * 3 + nb_signaux_activite.

## Verification
- Aucun prospect REJETE n'est envoye au CRM PROSPECTS.
- Un HOT a au moins un signal d'intention.
