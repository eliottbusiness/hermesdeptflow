# 🤖 SDR IA LinkedIn — Spécifications Complètes
### Produit Hermes Agent × BeReach API
**Version 2.0 — Avril 2026**

---

## 📌 Vue d'ensemble du produit

Un agent SDR autonome qui tourne 24h/24 sur Hermes, utilise l'API BeReach pour agir sur LinkedIn, qualifie des prospects contre un ICP défini, et livre chaque matin un pipeline de prospects scorés dans un CRM Google Sheets — le tout configurable par client via un onboarding guidé.

**Modèle commercial :** Tu vends ce produit à des clients B2B. Chaque client a son propre profil Hermes isolé, sa propre clé BeReach, son propre ICP et sa propre offre. Tu gères tout depuis ta Google VM.

---

## 🏗️ Architecture globale

```
[Cron quotidien 6h00]
        ↓
[SKILL : icp-search]
→ BeReach API : recherche prospects selon ICP
→ Filtre activité LinkedIn -45 jours
        ↓
[SKILL : prospect-qualifier]
→ Check ICP (critères obligatoires)
→ Check activité -45 jours
→ Analyse signaux d'intention IA
→ Décision : REJETÉ / 🟡 WARM / 🔴 HOT
        ↓
[SKILL : crm-updater]
→ Ajout dans Google Sheets (qualifiés uniquement)
→ Statut initial : WARM ou HOT selon qualification
        ↓
[SKILL : connection-sender]
→ BeReach API : envoi demande de connexion sans note
→ Mise à jour statut → "DEMANDE_ENVOYÉE"
        ↓
[Rapport Telegram/Discord livré au client]
```

---

## 📦 Besoins infrastructure

### 1. Google VM (Cloud)
- **Déjà disponible** — pas besoin de VPS externe
- **Requis :** Hermes installé, Python 3.11+, accès internet permanent
- **Avantage clé :** Authentification Google native → Google Drive & Sheets API sans friction, OAuth déjà géré par l'environnement GCP
- **Recommandé :** Laisser tourner l'instance en permanence (e2-micro est gratuit sur GCP Free Tier)

### 2. Hermes Agent
- **Version :** v0.10.0+ (Tool Gateway)
- **Installation :**
  ```bash
  curl -fsSL https://raw.githubusercontent.com/NousResearch/hermes-agent/main/scripts/install.sh | bash
  ```
- **Profils :** 1 profil Hermes par client (isolation complète mémoire/skills/cron)
- **Modèle recommandé :** Qwen3 Coder 480B via OpenRouter (gratuit, 262K contexte) + fallback Ollama local

### 3. BeReach API
- **Documentation :** `api.berea.ch` / `berea.ch/agentic`
- **Endpoints utilisés :**

| Endpoint | Usage | Méthode |
|---|---|---|
| `POST /search/linkedin/people` | Recherche prospects par ICP | Search |
| `POST /collect/linkedin/profile` | Récupérer données profil complet | Scraping |
| `POST /collect/linkedin/posts` | Posts récents du prospect (-45j) | Scraping |
| `POST /connect/linkedin/profile` | Envoyer demande connexion | Action |
| `POST /visit/linkedin/profile` | Visiter profil (signal warmup) | Action |

- **Limites à respecter (anti-ban) :**
  - Max **80-100 demandes de connexion/semaine** (≈ 15/jour max)
  - Max **80 visites de profil/jour** (compte standard) ou 500/jour (Sales Navigator)
  - Jitter obligatoire : délai aléatoire 3-8 secondes entre chaque action
  - Ne jamais maximiser tous les quotas simultanément

### 4. Google Sheets CRM
- **1 fichier Google Sheets par client**
- **Accès via :** Google Workspace MCP (bundled dans Hermes) ou Google Sheets API v4
- **Credentials :** Service Account JSON par client OU OAuth2 partagé

### 5. Notification client
- **Canal :** Telegram bot (1 bot par client) OU Discord webhook
- **Livraison :** rapport quotidien matin avec stats du jour

---

## 👤 Système de profils multi-clients

### Création d'un nouveau client

Hermes supporte les profils isolés nativement :

```bash
# Créer un nouveau profil client
hermes profile create client-nom-entreprise --clone

# Passer sur ce profil
hermes profile use client-nom-entreprise

# Vérifier
hermes profile list
```

Chaque profil a son propre :
- `~/.hermes/profiles/client-nom/config.yaml` → clés API
- `~/.hermes/profiles/client-nom/MEMORY.md` → ICP + contexte client
- `~/.hermes/profiles/client-nom/skills/` → skills spécifiques
- `~/.hermes/profiles/client-nom/cron/` → jobs planifiés isolés

---

## 🤝 Skill : Onboarding Client (à créer)

**Fichier :** `~/.hermes/skills/client-onboarding.md`

Ce skill est déclenché quand tu dis à Hermes :
> *"Crée un nouveau profil SDR pour [NomClient]"*

### Flux d'onboarding

Hermes pose les questions suivantes dans l'ordre et configure tout automatiquement :

```
Questions posées par Hermes :

1. "Quel est le nom de l'entreprise cliente ?"
   → Crée le profil Hermes : hermes profile create [slug]

2. "Colle ta clé API BeReach du client."
   → Écrit dans config.yaml : bereach_api_key: "brc_xxx"

3. "Quel est le canal de livraison ? (telegram/discord/email)"
   → Configure la gateway de livraison

4. "Colle le token Telegram bot (ou webhook Discord)."
   → Configure deliver dans le cron

5. [AUTOMATIQUE — pas de question]
   → Lance le skill crm-setup
   → Crée le dossier "Client-CRM" dans Google Drive si inexistant
   → Crée le fichier "[NomClient] - CRM PROSPECTION" dans ce dossier
   → Initialise toutes les colonnes et onglets
   → Sauvegarde l'URL dans config.yaml : crm_sheet_url: "..."

6. "Voici le template ICP à remplir. Complète chaque champ."
   → Voir template ICP ci-dessous — uniquement les champs utiles à BeReach
   → Sauvegarde dans MEMORY.md section [ICP]

7. "Voici le template OFFRE à remplir. Complète chaque champ."
   → Voir template OFFRE ci-dessous
   → Sauvegarde dans MEMORY.md section [OFFRE]

8. "Combien de demandes de connexion par jour ? (recommandé : 10-15)"
   → Configure : daily_connection_limit: 12

9. "À quelle heure lancer la prospection quotidienne ? (ex: 07:00)"
   → Configure le cron

→ Confirmation : "Profil [NomClient] créé. CRM Google Sheets créé dans 
   le dossier Client-CRM. Premier run demain à [heure]."
```

---

### 📄 Template ICP — Champs utiles à BeReach uniquement

Le document ICP doit contenir **exactement** ces champs — ce sont les seuls que BeReach peut utiliser dans ses filtres de recherche et que le scorer peut vérifier sur un profil :

```
=== ICP CLIENT ===

# FILTRES DE RECHERCHE BEREACH (obligatoires)
# Ces champs alimentent directement search/linkedin/people

TITRES_CIBLES:
  - [ex: "Directeur Commercial", "Head of Sales", "VP Sales"]
  → Utilisé dans : keywords + title filter BeReach

SENIORITE:
  - [C-Level / VP / Director / Manager / Senior / Entry]
  → Utilisé dans : seniority filter BeReach

SECTEURS_ACTIVITE:
  - [ex: "SaaS B2B", "Logiciels entreprise", "FinTech"]
  → Utilisé dans : industry filter BeReach

TAILLE_ENTREPRISE:
  - [1-10 / 11-50 / 51-200 / 201-500 / 501-1000 / 1000+]
  → Utilisé dans : companySize filter BeReach

LOCALISATION:
  - [ex: "France", "Paris", "Europe"]
  → Utilisé dans : location filter BeReach

# CRITÈRES DE SCORING IA (vérifiés par Hermes sur le profil récupéré)

TECHNOLOGIES_STACK:
  - [ex: "Salesforce", "HubSpot"] — laisser vide si non pertinent
  → Vérifié dans : expérience / compétences du profil

ANNEES_EXPERIENCE_MIN: [ex: 5]
  → Vérifié dans : ancienneté du profil LinkedIn

SIGNAUX_INTENTION_CLES:
  - [ex: "parle de recrutement commercial", "mentionne scaling équipe"]
  - [ex: "poste sur la prospection B2B", "commente des outils sales"]
  → Analysé dans : posts -45 jours via collect/linkedin/posts

# EXCLUSIONS
TITRES_A_EXCLURE:
  - [ex: "Freelance", "Étudiant", "Consultant indépendant"]
SECTEURS_A_EXCLURE:
  - [ex: "Recrutement", "MLM", "Immobilier"]
```

---

### 📄 Template OFFRE — Champs utiles pour la personnalisation

L'OFFRE est utilisée par le scorer pour détecter les signaux d'intention dans les posts du prospect :

```
=== OFFRE CLIENT ===

NOM_OFFRE: [ex: "SDR IA LinkedIn"]

PROBLEME_RESOLU:
  - [ex: "Manque de prospects qualifiés réguliers"]
  - [ex: "Temps perdu sur la prospection manuelle LinkedIn"]
  → Utilisé pour : détecter si le prospect parle de ces douleurs dans ses posts

BENEFICE_PRINCIPAL: [ex: "15 prospects qualifiés/jour sans effort manuel"]

MOTS_CLES_INTENTION:
  - [ex: "prospection", "cold outreach", "pipeline", "leads B2B"]
  → Utilisé pour : scorer les posts LinkedIn du prospect

CONCURRENTS_OU_ALTERNATIVES:
  - [ex: "Lemlist", "LaGrowthMachine", "Waalaxy", "PhantomBuster"]
  → Signal fort : si le prospect cherche un concurrent = intention élevée
```

---

### Skill : `crm-setup.md`
**Rôle :** Crée automatiquement le Google Sheet CRM dans Google Drive lors de l'onboarding.

```yaml
name: crm-setup
triggers: [créer crm, setup crm, initialiser google sheet]
prompt: |
  Utilise le MCP Google Workspace pour :
  1. Vérifier si le dossier "Client-CRM" existe dans Google Drive
     - Si non : le créer
  2. Créer un nouveau Google Sheets nommé "[NomClient] - CRM PROSPECTION"
     dans le dossier "Client-CRM"
  3. Initialiser l'onglet "PROSPECTS" avec les colonnes :
     id | date_ajout | prenom | nom | titre | entreprise | url_linkedin |
     localisation | secteur | taille_entreprise | score_icp | score_activite |
     score_intention | score_total | signaux_detectes | dernier_post |
     statut | date_connexion_envoyee | date_connexion_acceptee | notes | source_run
  4. Ligne 1 : gras, fond bleu foncé, texte blanc
  5. Créer un second onglet "REJETÉS" avec les mêmes colonnes
  6. Retourner l'URL du fichier créé
  7. Sauvegarder dans config.yaml : crm_sheet_url: "[url]"
```

---

### Template SKILL.md onboarding

```yaml
name: client-onboarding
description: Crée et configure un nouveau profil client SDR LinkedIn
triggers: [nouveau client, créer profil, onboarding client, setup client]
prompt: |
  Tu es en train de configurer un nouveau profil SDR LinkedIn pour un client.
  Pose les questions dans l'ordre suivant, une par une.
  Attends la réponse avant de passer à la suivante.
  À la fin, crée le profil Hermes, écris toutes les configs, 
  et confirme avec un récapitulatif complet.
  
  Variables à collecter : nom_client, bereach_api_key, canal_livraison,
  token_canal, crm_sheet_url, icp_document, offre_document, 
  daily_limit, heure_cron
  
  Actions à exécuter après collecte :
  1. hermes profile create [slug_client] --clone
  2. Écrire config.yaml avec toutes les clés
  3. Écrire MEMORY.md avec ICP et OFFRE
  4. Créer le cron job avec hermes cron create
  5. Confirmer par message récap sur le canal configuré
```

---

## 📋 Structure Google Sheets CRM

### Colonnes obligatoires

| Colonne | Type | Description |
|---|---|---|
| `id` | String | ID unique (timestamp + hash) |
| `date_ajout` | Date | Date d'entrée dans le CRM |
| `prenom` | String | Prénom LinkedIn |
| `nom` | String | Nom LinkedIn |
| `titre` | String | Titre actuel |
| `entreprise` | String | Entreprise actuelle |
| `url_linkedin` | URL | Lien profil LinkedIn |
| `localisation` | String | Ville / Pays |
| `secteur` | String | Secteur d'activité |
| `taille_entreprise` | String | ex: 11-50, 51-200 |
| `statut_qualification` | Enum | WARM / HOT |
| `nb_signaux_activite` | Integer | Nombre de signaux activité détectés |
| `nb_signaux_intention` | Integer | Nombre de signaux intention détectés |
| `priorite_interne` | Integer | Score de priorité d'envoi (invisible client) |
| `signaux_detectes` | Text | Liste des signaux trouvés |
| `dernier_post` | Date | Date du dernier post LinkedIn |
| `statut` | Enum | Voir statuts ci-dessous |
| `date_connexion_envoyee` | Date | Date envoi demande |
| `date_connexion_acceptee` | Date | Date acceptation |
| `notes` | Text | Notes manuelles |
| `source_run` | Date | Date du run qui a trouvé ce prospect |

### Statuts du pipeline

```
🟡 WARM              → ICP ✅ + Actif ✅ — demande connexion envoyée
🔴 HOT               → WARM + signal d'intention — priorité haute
DEMANDE_ENVOYÉE      → Demande de connexion BeReach envoyée
CONNECTÉ             → Connexion acceptée
RELANCE_1            → Premier message post-connexion
RÉPONDU              → A répondu
RDV_PRIS             → Rendez-vous planifié
DISQUALIFIÉ          → Sorti manuellement
REJETÉ               → Non-ICP ou fantôme (jamais dans le CRM)
```

---

## 🎯 Système de qualification

Le système est **séquentiel et binaire** : un prospect doit valider chaque étape avant de passer à la suivante. Pas de compensation entre critères — un mauvais ICP ne peut pas être rattrapé par une forte intention.

```
[ÉTAPE 1] ─── ICP CHECK ───────────────────────────────────────
     ↓ NON-ICP → REJETÉ (jamais dans le CRM)
     ↓ ICP OK  →

[ÉTAPE 2] ─── SIGNAUX D'ACTIVITÉ (-45 jours) ──────────────────
     ↓ Fantôme (0 signal) → REJETÉ
     ↓ Actif   →

               STATUT : 🟡 WARM
               (entre dans le CRM + demande connexion envoyée)
     ↓

[ÉTAPE 3] ─── SIGNAUX D'INTENTION ─────────────────────────────
     ↓ Aucun signal  → reste WARM
     ↓ 1+ signal fort →

               STATUT : 🔴 HOT
               (priorité d'envoi, futur : message personnalisé)
```

---

### Étape 1 — ICP Check (critères non négociables)

Hermes compare le profil LinkedIn récupéré via BeReach avec le document ICP.
**Tous les critères obligatoires doivent être validés** pour passer à l'étape 2.

| Critère | Obligatoire | Source LinkedIn |
|---|---|---|
| Titre correspond aux titres ICP | ✅ Oui | `profile.title` |
| Séniorité correspond | ✅ Oui | `profile.title` + ancienneté |
| Taille entreprise correspond | ✅ Oui | `profile.company.size` |
| Localisation correspond | ✅ Oui | `profile.location` |
| Secteur correspond | ⚠️ Souple | Voir note ci-dessous |

> **⚠️ Note importante sur les secteurs LinkedIn**
> Le champ secteur est auto-déclaré et très souvent mal renseigné (ex: "Technology, Information and Internet" regroupe indifféremment une startup de 3 personnes et une ESN de 5000 collaborateurs). **Ne pas en faire un critère éliminatoire dur.** Hermes doit croiser titre + taille entreprise + mots-clés du profil pour inférer le secteur réel. Le secteur LinkedIn sert d'indice de confirmation, jamais de filtre bloquant.

---

### Étape 2 — Signaux d'activité (-45 jours)

Évalués via BeReach `collect/linkedin/posts` sur les 45 derniers jours.
**Au moins 1 signal parmi les suivants** pour valider :

| Signal | Poids |
|---|---|
| A publié au moins 1 post | Fort |
| A commenté au moins 1 post | Fort |
| A liké des posts | Faible (signal minimum) |
| Profil mis à jour récemment | Faible |

Un profil **sans aucune activité sur 45 jours** = REJETÉ automatiquement.
Raison : probabilité de réponse trop faible, nuit au taux d'acceptation global du compte client.

---

### Étape 3 — Signaux d'intention

Analysés par Hermes via LLM sur le contenu des posts récupérés.
**Au moins 1 signal suffit** pour passer de WARM à HOT.

| Signal d'intention | Force |
|---|---|
| Post sur une douleur que l'offre résout | 🔴 Très fort |
| Recherche active d'un prestataire / solution | 🔴 Très fort |
| Commente ou like des posts de concurrents directs | 🔴 Très fort |
| Changement de poste récent (< 90 jours) | 🟠 Fort |
| Mentionne une croissance ou scaling de son équipe | 🟠 Fort |
| Like de contenu lié au marché de l'offre | 🟡 Moyen |

---

### Score interne de priorité (invisible pour le client)

Uniquement utilisé par Hermes pour **ordonner l'envoi** quand plusieurs WARM/HOT sont en attente le même jour. Ne change pas le statut.

```
Priorité = (nb_signaux_intention × 3) + (nb_signaux_activite × 1)
```

Les HOT avec le plus de signaux sont traités en premier dans la journée.

---

### Tableau récap des statuts

| Statut | Condition | Action Hermes |
|---|---|---|
| **REJETÉ** | Non-ICP ou 0 activité -45j | Jamais dans le CRM |
| **🟡 WARM** | ICP ✅ + Actif ✅ | Entrée CRM + demande connexion |
| **🔴 HOT** | WARM + 1 signal d'intention | Entrée CRM + connexion priorité haute |

## ⚙️ Skills Hermes à créer

### 1. `icp-search.md`
**Rôle :** Recherche les prospects sur LinkedIn via BeReach selon l'ICP du profil actif.

```yaml
name: icp-search
triggers: [recherche prospects, find prospects, daily search]
prompt: |
  Lis le document ICP dans MEMORY.md.
  Construis une requête BeReach search/linkedin/people avec :
  - keywords: basés sur les titres ICP
  - filters: secteur, taille entreprise, localisation
  Limite à 50 résultats par run.
  Pour chaque résultat, récupère le profil complet via collect/linkedin/profile.
  Retourne une liste structurée JSON.
```

**Appel API BeReach :**
```bash
curl -X POST https://api.berea.ch/search/linkedin/people \
  -H "Authorization: Bearer {bereach_api_key}" \
  -H "Content-Type: application/json" \
  -d '{
    "keywords": "{icp_titres}",
    "filters": {
      "industry": "{icp_secteur}",
      "companySize": "{icp_taille}",
      "location": "{icp_localisation}"
    },
    "limit": 50
  }'
```

### 2. `prospect-scorer.md`
**Rôle :** Score chaque prospect sur les 3 dimensions.

```yaml
name: prospect-qualifier
triggers: [qualifier prospect, check icp, score prospect]
prompt: |
  Pour chaque prospect de la liste, applique le pipeline séquentiel :

  ÉTAPE 1 — ICP CHECK (critères non négociables) :
  Compare titre, séniorité, taille entreprise, localisation avec MEMORY.md [ICP].
  Attention : le secteur LinkedIn est souvent mal renseigné — croiser avec
  titre + taille pour inférer. Si critères obligatoires non validés → REJETÉ.

  ÉTAPE 2 — ACTIVITÉ -45 JOURS :
  Appelle BeReach collect/linkedin/posts pour les 45 derniers jours.
  Si aucune activité détectée → REJETÉ.
  Sinon → compter les signaux (posts, commentaires, likes).

  ÉTAPE 3 — SIGNAUX D'INTENTION :
  Analyse LLM des posts récupérés vs document OFFRE dans MEMORY.md.
  Cherche : douleurs mentionnées, recherche de solutions, signaux concurrents,
  changement de poste, scaling équipe.
  Compter les signaux d'intention détectés.

  DÉCISION FINALE :
  - REJETÉ si étapes 1 ou 2 échouent
  - 🟡 WARM si ICP ✅ + Actif ✅ + 0 signal intention
  - 🔴 HOT si ICP ✅ + Actif ✅ + 1+ signal intention

  Calcule priorite_interne = (nb_signaux_intention × 3) + (nb_signaux_activite × 1)
  Retourne JSON avec statut, signaux détectés, priorité.
```

### 3. `crm-updater.md`
**Rôle :** Écrit les prospects qualifiés dans Google Sheets.

```yaml
name: crm-updater
triggers: [update crm, ajouter crm, save prospects]
prompt: |
  Pour chaque prospect statut 🟡 WARM ou 🔴 HOT :
  - Vérifie si l'URL LinkedIn existe déjà dans le Sheets (déduplique)
  - Si nouveau : ajoute une ligne avec tous les champs
  - Statut initial : "NOUVEAU"
  Utilise le skill google-workspace ou l'API Sheets v4.
  Log le nombre de prospects ajoutés / dédupliqués.
```

### 4. `connection-sender.md`
**Rôle :** Envoie les demandes de connexion aux prospects QUALIFIÉS.

```yaml
name: connection-sender
triggers: [envoyer connexions, send connections]
prompt: |
  Pour chaque prospect statut 🟡 WARM ou 🔴 HOT, par ordre de priorite_interne décroissant :
  1. Vérifie que le quota daily n'est pas dépassé ({daily_connection_limit})
  2. Visite d'abord le profil via BeReach visit/linkedin/profile (warmup)
  3. Attends 3-8 secondes (jitter aléatoire)
  4. Envoie demande de connexion SANS NOTE via connect/linkedin/profile
  5. Met à jour statut → "DEMANDE_ENVOYÉE" dans Sheets
  6. Attends 5-10 secondes entre chaque envoi
  Arrête si quota atteint.
```

**Appel API connexion :**
```bash
curl -X POST https://api.berea.ch/connect/linkedin/profile \
  -H "Authorization: Bearer {bereach_api_key}" \
  -d '{
    "profileUrl": "{linkedin_url}",
    "message": ""
  }'
```

### 5. `daily-report.md`
**Rôle :** Génère et envoie le rapport quotidien au client.

```yaml
name: daily-report
triggers: [rapport quotidien, daily report]
prompt: |
  Génère un rapport du run du jour :
  - Nombre de prospects trouvés
  - Nombre WARM / HOT / rejetés
  - Taux de qualification global
  - Nombre de demandes de connexion envoyées
  - Quota restant de la semaine
  - Top 3 prospects du jour avec score
  Envoie via le canal configuré (Telegram/Discord).
  Format : émojis + bullet points, max 15 lignes.
```

---

## ⏰ Cron Job quotidien

Commande à lancer pour chaque client après onboarding :

```bash
hermes -p client-nom-entreprise cron create "0 6 * * 1-5" \
"Exécute le pipeline SDR LinkedIn quotidien :
1. Lance le skill icp-search pour trouver 50 nouveaux prospects
2. Lance prospect-scorer sur tous les prospects trouvés
3. Lance crm-updater pour ajouter les qualifiés dans Google Sheets
4. Lance connection-sender pour envoyer les demandes (respect quota)
5. Lance daily-report pour envoyer le résumé sur le canal configuré
En cas d'erreur sur une étape, log l'erreur et continue." \
--name "SDR-Daily-{NomClient}" \
--deliver telegram
```

**Explication du schedule `0 6 * * 1-5` :**
- Tous les jours de semaine (lun-ven) à 6h00
- Le week-end : aucun run (LinkedIn moins actif, préserve les quotas)

---

## 🔐 Sécurité & Anti-ban

### Règles absolues BeReach

| Limite | Valeur sûre | Valeur max absolue |
|---|---|---|
| Demandes connexion/semaine | 50-60 | 80-100 |
| Demandes connexion/jour | 10-12 | 15 |
| Visites profil/jour (standard) | 50 | 80 |
| Visites profil/jour (Sales Nav) | 300 | 500 |
| Délai entre actions | 5-10s | 3s minimum |

### Configuration anti-détection

```yaml
# Dans config.yaml du profil client
bereach:
  jitter_min_seconds: 3
  jitter_max_seconds: 8
  daily_connection_limit: 12
  daily_profile_visit_limit: 60
  working_hours_only: true  # Actions seulement 8h-18h
  weekend_pause: true       # Pas d'actions samedi/dimanche
```

### Warning si quota proche

Le skill `connection-sender` doit vérifier avant chaque run :
- Si quota semaine > 70% → alerte dans le rapport
- Si quota semaine > 90% → pause forcée, alerte immédiate au client

---

## 📊 Tableau de bord opérateur (toi)

Pour gérer tous tes clients depuis un point central :

### Commandes utiles

```bash
# Voir tous les profils clients actifs
hermes profile list

# Vérifier les crons de tous les clients
hermes -p client-xyz cron list

# Voir les logs d'un run spécifique
hermes -p client-xyz cron logs [id]

# Lancer manuellement un run pour un client
hermes -p client-xyz "Lance le pipeline SDR complet pour aujourd'hui"

# Voir les stats d'utilisation (coûts)
hermes -p client-xyz /usage
```

### Mission Control (optionnel)

Pour une vue fleet multi-clients avec dashboard visuel :
```bash
git clone https://github.com/builderz-labs/mission-control
```
→ Permet de voir tous les agents, les coûts, les statuts en temps réel.

---

## 💰 Structure de coûts estimée

### Par client / mois

| Poste | Coût estimé |
|---|---|
| Google VM (GCP e2-micro) | Gratuit (Free Tier) |
| BeReach API | 50€/mois |
| LLM (scoring IA) | ~5-15$/mois selon volume |
| Google Sheets API | Gratuit |
| Telegram Bot | Gratuit |
| **Total coût opérationnel** | **~55-65€/client/mois** |

### Pricing suggéré pour tes clients

| Tier | Volume | Prix |
|---|---|---|
| Starter | 10 connexions/jour | 297€/mois |
| Growth | 15 connexions/jour | 497€/mois |
| Scale | 15 conn. + suivi inbox | 797€/mois |

---

## 🗺️ Roadmap de développement

### Phase 1 — MVP (Semaine 1-2)
- [ ] Configurer Hermes sur la Google VM
- [ ] Créer le skill `client-onboarding`
- [ ] Créer le skill `icp-search` avec BeReach
- [ ] Créer le skill `prospect-qualifier` (logique WARM/HOT)
- [ ] Créer le skill `crm-updater` avec Google Sheets
- [ ] Créer le skill `connection-sender`
- [ ] Créer le skill `daily-report`
- [ ] Tester sur 1 client réel (toi-même)

### Phase 2 — Affinage qualification (Semaine 3-4)
- [ ] Enrichir le `prospect-qualifier` avec analyse LLM plus fine des posts
- [ ] Affiner les signaux d'intention selon les retours terrain
- [ ] Calibrer avec les premiers clients : valider WARM/HOT vs taux d'acceptation réels
- [ ] Créer un skill `feedback-loop` : le client peut marquer un prospect rejeté comme pertinent → Hermes apprend

### Phase 3 — Scale multi-clients (Mois 2)
- [ ] Installer Mission Control pour la vue fleet
- [ ] Automatiser la facturation (Stripe MCP)
- [ ] Dashboard client en lecture seule (Hermes WebUI)
- [ ] Skill de suivi post-connexion (message après acceptation)

### Phase 4 — Fonctionnalités avancées (Mois 3+)
- [ ] Détection des acceptations via BeReach inbox
- [ ] Envoi automatique du message post-connexion
- [ ] Suivi des relances (J+3, J+7 si pas de réponse)
- [ ] Reporting hebdomadaire avancé (taux d'acceptation, taux réponse)

---

## 📁 Structure de fichiers recommandée

```
~/.hermes/
├── profiles/
│   ├── client-acme/
│   │   ├── config.yaml          ← clé BeReach, Sheets, Telegram
│   │   ├── MEMORY.md            ← ICP + OFFRE du client
│   │   ├── skills/
│   │   │   ├── icp-search.md
│   │   │   ├── prospect-scorer.md
│   │   │   ├── crm-updater.md
│   │   │   ├── connection-sender.md
│   │   │   └── daily-report.md
│   │   └── cron/
│   │       └── sdr-daily.json
│   ├── client-beta/
│   │   └── ...
│   └── client-gamma/
│       └── ...
└── skills/
    └── client-onboarding.md    ← skill global, crée les profils
```

---

## ⚠️ Risques & points de vigilance

### LinkedIn
- **Risque de ban :** Respecter absolument les quotas BeReach. Commencer à 5-8 connexions/jour la 1ère semaine pour "chauffer" le compte.
- **Profil du client :** Le compte LinkedIn utilisé doit avoir un SSI (Social Selling Index) > 60 pour être plus safe. Checker sur `linkedin.com/sales/ssi`.
- **Changements d'algo :** LinkedIn met à jour ses détections régulièrement. Surveiller les changelogs BeReach mensuellement.

### Qualité du scoring
- Le scoring IA dépend de la qualité du document ICP fourni par le client. Plus l'ICP est précis, meilleur le scoring.
- Les premiers 10-15 jours sont une phase de calibration. Faire du feedback loop avec le client.

### Coûts LLM
- Le scoring IA de 50 prospects/jour = ~500K tokens/mois → ~3-5$ avec Qwen3 via OpenRouter.
- Utiliser le cache Hermes (`/compress`) pour réduire les tokens de contexte.

---

## 🔗 Ressources clés

| Ressource | Lien |
|---|---|
| BeReach API Docs | `api.berea.ch` |
| BeReach Endpoints complets | `berea.ch/agentic` |
| Hermes Agent | `github.com/NousResearch/hermes-agent` |
| Hermes Docs | `hermes-agent.nousresearch.com/docs` |
| Automation Templates Hermes | `hermes-agent.nousresearch.com/docs/guides/automation-templates` |
| Mission Control (fleet) | `github.com/builderz-labs/mission-control` |
| Hermes WebUI | `github.com/nesquena/hermes-webui` |
| Google Sheets API | `developers.google.com/sheets/api` |
| Awesome Hermes | `github.com/0xNyk/awesome-hermes-agent` |

---

*Document généré le 27 avril 2026 — à mettre à jour au fil des itérations produit.*
