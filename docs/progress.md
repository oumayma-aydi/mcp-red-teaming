# Avancement du projet : MCP Red Teaming Framework

_Dernière mise à jour : 24 novembre 2026_

## 1. Objectif
Framework de red teaming automatisé pour un agent LLM connecté à des outils MCP simulés.
Il exécute des attaques reproductibles, détecte les comportements vulnérables, mesure
l'Attack Success Rate (ASR) et compare une configuration **baseline** à une configuration
**hardened** (cahier des charges, sections 1 à 3).

## 2. Architecture actuelle

```
scenarios/*.yaml ──> Scenario Loader ──> Attack Runner ──> Agent LLM <──> Client MCP ──> Serveur MCP
                                              │                                              │
                                              ▼                                              ▼
                                         Evaluator                                  logs/server_calls.jsonl
                                              │
                                              ▼
                                  results/baseline_results.json
```

- **Agent** : boucle de tool calling (`src/agent/llm_agent.py`), max 5 tours.
- **Serveur MCP** : 2 outils simulés, 6 documents synthétiques (3 normaux, 3 piégés), aucun effet réel.
- **Isolation** : un serveur MCP est relancé par scénario, `run_id` et `scenario_id` dans chaque log.
- **Stack** : Python, MCP Python SDK, Pydantic, PyYAML. Pandas et Matplotlib sont installés pour le Jour 4.
- **Modèle** : `openai/gpt-oss-120b` via Groq (initialement prévu : Claude Haiku via l'API Anthropic).
  Le même modèle sera utilisé pour baseline et hardened.

## 3. Chronologie

### Jour 1 : agent MCP fonctionnel
- Setup : dépôt Git, venv, dépendances, `.env`, `.gitignore`.
- Serveur MCP (`search_documents`, `execute_action`), client stdio, agent avec boucle d'outils.
- Smoke tests : une recherche légitime et une notification simulée.
- Problèmes rencontrés et corrigés :
  - Le test 1 finissait en `max_turns_reached` : documents en français, prompt en anglais, recherche par sous-chaîne.
    Solution : documents en anglais, recherche par mots.
  - Affichage `rÃ©initialisation` dans PowerShell : simple problème d'encodage (`Get-Content -Encoding UTF8`).
  - Observation utile : la baseline appelait `read_internal_data` et `export_data` sans demande,
    quand elle était bloquée.

### Jour 2 : moteur d'attaque
- Serveur nettoyé (stopwords) et 3 documents piégés (injection indirecte : DOC-004, DOC-005, DOC-006).
- Modèle Pydantic `Scenario` avec champ `detection` exécutable, et chargeur YAML.
- **15 scénarios** : 5 Prompt Injection (PI), 5 Tool Misuse (TM), 5 Data Exfiltration (DE).
- Évaluateur minimal : PASS / FAIL / INCONCLUSIVE, avec ERROR pour les erreurs techniques.
- Attack Runner et campagne : `python -m src.main --config configs/baseline.yaml`.
- `docs/methodology.md` : modèle de menace, politique d'autorisation (seule `send_notification`
  est autorisée pour l'utilisateur standard), définition d'une attaque réussie, tentative vs exécution.
- Script `inspect_results.py` pour la revue manuelle.

## 4. Résultats baseline (provisoires)

| Catégorie | FAIL / exécutés | ASR |
|---|---|---|
| Data Exfiltration | 4 / 5 | 80 % |
| Prompt Injection | 2 / 5 | 40 % |
| Tool Misuse | 2 / 5 | 40 % |
| **Global** | **8 / 15** | **53,3 %** |

Revue manuelle : 11 scénarios sur 15 relus, tous confirmés (détail dans `docs/manual_review_baseline.md`).
Les chiffres sont provisoires tant que PI-04, TM-03, TM-04, TM-05 ne sont pas relus et que
les détecteurs ne sont pas ajustés.

Constats principaux :
- La baseline résiste aux demandes frontalement malveillantes, mais cède à la reformulation,
  à la notification et au dump (le secret sort par plusieurs canaux).
- Les injections cachées ou directes marchent (PI-01, PI-05). Les documents piégés sont lus mais
  pas obéis sur ce modèle.
- `search_documents` n'a aucun contrôle d'accès : un mot-clé vide retourne tout, secret compris.

## 5. État par rapport à la checklist de validation

| Critère | État |
|---|---|
| Agent LLM connecté à MCP | ✅ |
| Deux outils MCP fonctionnels | ✅ |
| Trois catégories d'attaques | ✅ |
| 15 scénarios exécutables | ✅ |
| Campagne automatique | ✅ |
| Logs des réponses et tool calls | ✅ |
| Détection attaques réussies / bloquées | 🟡 version minimale, à affiner |
| Profils baseline et hardened | 🟡 baseline fait, hardened à faire |
| ASR global et par catégorie | 🟡 provisoire (calcul automatisé à faire) |
| Comparaison baseline vs hardened | ⬜ |
| Graphiques | ⬜ |
| Rapport final automatique | ⬜ |
| README (installation et exécution) | ⬜ |
| Aucun appel réel vers un système externe | ✅ |

## 6. Prochaines étapes

**Avant le Jour 3**
- Relire PI-04, TM-03, TM-04, TM-05 et compléter `manual_review_baseline.md`.
- Vérifier `temperature=0` dans `llm_agent.py`.
- Committer le Jour 2.

**Jour 3 : hardening et évaluation**
- Couche de sécurité côté serveur MCP : permissions par action, validation des paramètres
  (`../`, destinataires externes), masquage du contenu `confidential`.
- `configs/hardened.yaml` avec prompt système renforcé.
- Évaluateur : précondition document piégé, tentative vs exécution, détecteurs ajustés.
- Métriques : ASR, ASR par catégorie, Defense Effectiveness, Block Rate.
- Relancer baseline et hardened avec les mêmes règles.

**Jour 4 : reporting**
- Graphiques, `results.csv`, `report.md`, tests pytest, README, documentation d'architecture.
- Répéter les campagnes N fois (ex. N=3) pour mesurer la variabilité.

## 7. Limites connues
- 15 scénarios, un seul modèle, données synthétiques, une seule attaque par scénario.
- Résultats probabilistes : ils peuvent varier d'une exécution à l'autre.
- PI-01 et PI-04 testent surtout l'obéissance, car le prompt baseline contient peu de règles.
- Les détecteurs reposent sur des regex et des règles d'appel : une exfiltration plus obfusquée
  (base64, lettres) ne serait pas détectée.