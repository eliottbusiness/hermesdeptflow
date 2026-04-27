---
name: icp-search
description: Recherche les prospects LinkedIn via BeReach selon l'ICP du profil actif.
version: 1.0.0
platforms: [linux, macos]
metadata:
  hermes:
    tags: [linkedin, bereach, prospecting]
    category: sales
    requires_toolsets: [terminal]
---
# ICP Search

## Procedure
Utiliser `sdr_ai.bereach.BeReachClient.search_people(icp, limit=50)` via le CLI principal.
La requete doit contenir:
- keywords: titres ICP.
- filters.industry: secteurs ICP.
- filters.companySize: tailles entreprise.
- filters.location: localisations.
- filters.seniority: seniorites.

## Verification
- Les resultats sont normalises en objets Prospect.
- Chaque prospect enrichissable a une URL LinkedIn.
