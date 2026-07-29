# Notes de session — Moteur de simulation de match

Ce document résume, en français et de façon pédagogique, ce qui a été
conçu et codé jusqu'ici. C'est un aide-mémoire pour toi, pas une spec
technique — pour le détail précis destiné au code, voir les `CLAUDE.md`
listés en bas de ce fichier.

**Où on en est** : le moteur de simulation de match (backend uniquement,
pas d'API, pas de frontend, pas de base de données) est fonctionnel et
testé. On peut simuler un match complet entre deux équipes avec des stats
personnalisées, en direct dans le terminal.

---

## 1. Le concept du jeu

Un simulateur de saison de foot + gestion d'équipe, open source. La pièce
centrale (celle sur laquelle on travaille) est un **moteur de simulation de
match texte** — pas un terrain visuel, mais un fil d'événements avec du
suspense ("il entre dans la surface... il tire... BUT !" ou "raté !"),
dans l'esprit des vieux jeux de gestion texte (Hattrick, Football Manager
version texte).

### Les trois piliers d'un résultat

Tout résultat de match doit s'expliquer par trois forces qui interagissent,
volontairement équilibrées pour qu'aucune n'écrase les autres :

1. **La qualité des joueurs** — leurs attributs individuels.
2. **La tactique** — doit avoir un effet structurel réel, pas juste
   cosmétique. Peut être changée **en plein match** avec effet immédiat.
3. **La chance** — aucun duel n'est jamais garanti, plus des moments rares
   d'éclair de génie.

---

## 2. Structure du projet

```
Global-Soccer-Manager/
├── CLAUDE.md                       # vision du projet, conventions générales
├── README.md                       # roadmap complète (10 phases), doc publique
├── docs/
│   └── MATCH_ENGINE_NOTES.md       # ce fichier
├── backend/
│   ├── CLAUDE.md                   # conventions backend (couches, style de code)
│   ├── pyproject.toml
│   ├── conftest.py                 # rend `app` importable pour pytest
│   ├── app/
│   │   ├── domain/                 # modèles de données purs
│   │   │   ├── player.py           # Player, PlayerAttributes, Position
│   │   │   ├── team.py             # Team
│   │   │   ├── tactic.py           # Tactic + tous les dials (enums)
│   │   │   └── match_context.py    # Weather, MatchContext
│   │   ├── engine/                 # le moteur de simulation
│   │   │   ├── CLAUDE.md           # LE doc de référence technique du moteur
│   │   │   ├── phase.py            # enum Phase (build_up/midfield/final_third/shot)
│   │   │   ├── events.py           # EventType, MatchEvent
│   │   │   ├── summary.py          # final_score() — petit utilitaire
│   │   │   ├── probability.py      # ProbabilityModel — LA formule de duel
│   │   │   ├── fatigue.py          # FatigueModel
│   │   │   ├── tactical_matchup.py # TacticalMatchup — confrontation des tactiques
│   │   │   ├── brilliance.py       # BrillianceCheck — éclair de génie
│   │   │   ├── home_advantage.py   # HomeAdvantage
│   │   │   ├── weather_modifiers.py# WeatherModifiers
│   │   │   ├── foul.py             # FoulCheck — faute ou tacle propre ?
│   │   │   ├── card.py             # CardCheck — jaune/rouge
│   │   │   ├── injury.py           # InjuryCheck — blessure
│   │   │   ├── match_situation.py  # MatchSituation (domicile/météo/arbitre, groupés)
│   │   │   ├── auto_substitution.py# AutoSubstitution — remplacements auto (blessure/fatigue)
│   │   │   ├── possession_chain.py # PossessionChainEngine — assemble tout
│   │   │   ├── match.py            # Match — objet stateful, pilotable en direct
│   │   │   ├── match_simulator.py  # MatchSimulator — wrapper "simule d'un coup"
│   │   │   └── rating/
│   │   │       ├── CLAUDE.md       # doc de référence de la couche rating
│   │   │       ├── tables.py       # poids par phase/attribut — EN DONNÉES
│   │   │       ├── calculator.py   # PhaseRatingCalculator
│   │   │       └── selector.py     # ProtagonistSelector
│   │   ├── commentary/
│   │   │   ├── CLAUDE.md           # doc de référence de la couche commentaire
│   │   │   ├── templates.py        # banques de textes — EN DONNÉES
│   │   │   └── generator.py        # CommentaryGenerator
│   │   └── delivery/CLAUDE.md      # doc (pas encore codé — API/WebSocket)
│   ├── scripts/
│   │   ├── _teams.py               # make_player()/build_team() partagés
│   │   ├── simulate_demo.py        # un scénario simple, non-interactif
│   │   └── menu.py                 # MENU INTERACTIF — 6 scénarios, narré en direct
│   └── tests/                      # 52 tests, tous verts
└── frontend/CLAUDE.md              # pas commencé
```

---

## 3. Le modèle de données

**`PlayerAttributes`** (échelle 1-99) : pace, dribbling, passing, vision,
shooting, tackling, marking, strength, positioning, aggression, composure,
stamina, **flair** (pilote l'éclair de génie), + 3 attributs gardien
(reflexes, handling, gk_positioning).

**`Team`** : `starting_xi` (11 joueurs obligatoires), `bench`, `tactic`.

**`Tactic`** : mentality (defensive/balanced/attacking), tempo
(slow/normal/fast), pressing (low/medium/high), width (narrow/normal/wide),
defensive_line (deep/normal/high), marking_scheme (zonal/man_to_man).
⚠️ `width` et `marking_scheme` existent dans le modèle mais **ne sont pas
encore branchés mécaniquement** dans le moteur (seuls mentality, pressing,
defensive_line ont un effet réel pour l'instant).

**`MatchContext`** : juste `weather` (clear/rain/wind) pour l'instant.

---

## 4. Comment un duel se résout (le cœur du moteur)

Chaque confrontation (progression de balle, tir...) suit le même pipeline,
dans `possession_chain.py` :

1. **Note d'équipe** (`PhaseRatingCalculator.rate`) : moyenne pondérée des
   attributs des joueurs éligibles pour cette phase, poids définis dans
   `rating/tables.py` (données, pas de code en dur).
2. **Note individuelle** du protagoniste sélectionné (`ProtagonistSelector`,
   choix pondéré aléatoire — favorise les joueurs avec bonne vision/
   positionnement).
3. **Mélange** : `effective = 0.7 × note_équipe + 0.3 × note_individuelle`
   (constante `BLEND` dans `rating/tables.py`). C'est ce qui fait qu'un
   joueur individuellement excellent tire la performance de l'équipe vers
   le haut sans l'écraser complètement.
4. **Éclair de génie** (`BrillianceCheck`) : check indépendant et rare
   (1% à 6% de chance selon le `flair` du protagoniste attaquant) qui, s'il
   se déclenche, multiplie sa note individuelle ×1.8 pour ce duel précis
   uniquement. Émet un événement `MOMENT_OF_BRILLIANCE`.
5. **Modificateurs de contexte**, appliqués en multiplicateurs :
   - `TacticalMatchup` : confrontation des tactiques des deux équipes
     (ex : pressing haut pénalise la relance adverse ; ligne défensive
     haute favorise l'attaquant rapide en phase finale).
   - `HomeAdvantage` : bonus ×1.05 pour l'équipe à domicile (toujours la
     première équipe passée à `Match`).
   - `WeatherModifiers` : pluie pénalise les phases de progression (×0.92),
     vent pénalise le tir (×0.90).
6. **Fatigue** (`FatigueModel`) : chaque joueur perd de la forme à chaque
   phase jouée (plus vite si tempo/pressing élevés) ; la forme réduit la
   note effective jusqu'à un plancher de 0.7 (jamais 0 — un joueur fatigué
   est moins bon, pas inutile).
7. **Résolution finale** (`ProbabilityModel`) : la formule logistique
   classique, avec un plancher/plafond de probabilité :

   ```
   p = 1 / (1 + e^-((note_attaque - note_défense) / SPREAD))
   p = clamp(p, P_MIN, P_MAX)
   résultat = rng.random() < p
   ```

### Constantes actuelles (calibrées empiriquement, pas inventées)

| Constante | Valeur | Fichier |
|---|---|---|
| `SPREAD` | 60.0 | `probability.py` |
| `P_MIN` / `P_MAX` | 0.20 / 0.80 | `probability.py` |
| `BLEND` | 0.7 (équipe) / 0.3 (individuel) | `rating/tables.py` |
| `MINUTES_PER_CHAIN` | 2 (→ 45 séquences/match) | `match.py` |
| `BONUS_MULTIPLIER` (éclair de génie) | ×1.8 | `brilliance.py` |
| Chance d'éclair de génie | 1% (flair=1) à 6% (flair=99) | `brilliance.py` |
| `HOME_BONUS` | ×1.05 | `home_advantage.py` |
| Pénalité pluie | ×0.92 (phases de progression) | `weather_modifiers.py` |
| Pénalité vent | ×0.90 (tir uniquement) | `weather_modifiers.py` |
| Fatigue — plancher | ×0.7 | `fatigue.py` |

**⚠️ Découverte importante** : une chaîne de possession exige de gagner
*plusieurs duels séquentiels* (3 phases + le tir). Des probabilités par
duel raisonnables se **combinent multiplicativement** et peuvent écraser
l'outsider au niveau du match complet même si chaque duel individuel reste
"équitable". Les valeurs ci-dessus ont été retunées après avoir constaté
qu'un écart de seulement 15 points donnait 93% de victoires et moins de 1%
de chances à l'outsider. Résultat actuel avec les valeurs tunées : équipes
égales ≈ 33/33/34 (victoire/nul/défaite), écart réaliste (15 pts) ≈
57/28/15, écart extrême (40 pts) ≈ 91/8/1. Total de buts par match proche
de 2,5-3 pour des équipes de niveau proche.

---

## 5. La machine à états (une "chaîne de possession")

```
RESTART → BUILD_UP → MIDFIELD → FINAL_THIRD → SHOT → GOAL / SAVE / BLOCK / OFF_TARGET
             |            |            |
          turnover     turnover     turnover  →  l'autre équipe récupère la balle
```

Chaque flèche "succès" est un duel résolu via le pipeline du §4. Un
turnover à n'importe quelle phase arrête la chaîne — **sauf si c'est une
faute** (§6 ci-dessous), auquel cas l'équipe qui attaquait garde le ballon.
**Pas encore implémenté** : hors-jeu, corners/coups francs comme séquences
à part entière (ils sont dans la roadmap).

---

## 6. Fautes, cartons, blessures

Ne se déclenche que quand l'attaquant **perd** un duel de progression
(BUILD_UP/MIDFIELD/FINAL_THIRD) — jamais sur le tir (un penalty est un
mécanisme à part, pas encore fait).

1. **`FoulCheck`** : 25% des duels perdus sont en fait une faute (pas un
   tacle propre). Sévérité = agressivité du tacleur − dribble du porteur de
   balle, plancher à 0, multipliée par zone (FINAL_THIRD plus sévère que
   BUILD_UP — arrêter une attaque avancée est plus "cynique").
2. **Conséquence mécanique clé** : une faute = coup franc, **pas un
   turnover** — l'équipe qui attaquait garde la balle pour la séquence
   suivante (`ChainResult.possession_retained`). C'est ce qui rend une
   faute vraiment différente d'un tacle propre, pas juste un habillage
   textuel différent.
3. **`CardCheck`** : `danger = sévérité × sévérité_arbitre`. La sévérité de
   l'arbitre est tirée une seule fois par match (0.7 à 1.3, dans
   `Match.__init__`) — certains matchs sont sifflés sévèrement, d'autres
   laissent beaucoup jouer, ça fait partie du pilier chance. Un 2e carton
   jaune pour le même joueur devient automatiquement un rouge.
4. **`InjuryCheck`** : risque indépendant et rare, sur la victime de la
   faute (le porteur de balle fauté) ou sur le tacleur lui-même en cas de
   tacle propre mais engagé (une blessure sur un geste 100% légal, ça
   arrive aussi en vrai).
5. **Carton rouge ou blessure** → le joueur passe `available = False` (pas
   une suppression physique de la liste des 11 !). Pourquoi : supprimer
   vraiment de la liste aurait cassé les tests statistiques qui réutilisent
   les mêmes objets `Team`/`Player` sur des centaines de matchs — exact
   même type de bug que celui déjà rencontré avec `fitness`. `available`
   est remis à `True` à chaque nouveau `Match`, comme `fitness` et
   `yellow_cards`.

⚠️ Détail piégeux si tu relis les événements bruts : pour `FOUL`/`CARD`,
`team_id` désigne l'équipe **qui a commis la faute/le carton** — alors que
pour `POSSESSION_PROGRESS`/`TURNOVER`, `team_id` désigne l'équipe qui
**attaquait**. Deux conventions différentes selon le type d'événement, pas
un bug.

---

## 7. Commentaire narratif

`app/commentary/` transforme un `MatchEvent` brut en phrase — c'est ce qui
répond à la toute première demande du projet ("il tire... BUT !" plutôt
qu'un JSON illisible). Volontairement séparé du moteur : le moteur ne
formate jamais de texte, le commentaire ne décide jamais d'un résultat.

- **`templates.py`** : des banques de phrases par type d'événement (données,
  pas de code). Une phrase est choisie au hasard dans la banque à chaque
  fois pour éviter la répétition.
- **`POSSESSION_PROGRESS` a un traitement spécial** : la banque choisie
  dépend de l'attribut dominant du protagoniste (pace/dribbling/vision), et
  seulement si cet attribut dépasse 70/99 — sinon phrase générique. Un
  joueur rapide "explose" ou "part en pointe", un dribbleur "élimine",
  personne ne parle de vitesse pour un joueur moyen.
- **`CommentaryGenerator.describe(event, roster, rng)`** : `roster` est un
  dict `id joueur -> Player` (les `MatchEvent` ne contiennent que des ids,
  jamais les objets joueurs complets — le commentaire est ce qui les
  résout en noms).
- **Déterminisme** : narrer tout un match d'un coup (comme le fait
  `menu.py`) se fait *après* que le RNG interne du moteur a déjà servi pour
  toute la simulation — donc on utilise un second `random.Random(seed)`
  avec le **même seed**, ce qui donne un texte tout aussi reproductible
  sans réutiliser la même instance.

`scripts/menu.py` utilise maintenant vraiment ce système (avant, il avait
son propre formateur jetable en attendant que ce module existe).

---

## 8. Contrôle en direct : `Match` — la pièce la plus importante côté architecture

`Match` (dans `match.py`) est un objet *stateful*, pas une fonction qui
tourne d'un coup. Il expose :

- `play_next_chain()` — avance d'une séquence de possession.
- `change_tactic(team, tactic)` — change la tactique d'une équipe, effectif
  **immédiatement** à la séquence suivante.
- `substitute(team, joueur_sortant, joueur_entrant)` — remplace un joueur,
  effectif immédiatement aussi.

**Pourquoi ça marche sans plomberie compliquée** : le moteur lit toujours
`team.tactic` et `team.starting_xi` en direct sur l'objet `Team`, jamais
une copie figée au coup d'envoi. Donc modifier ces objets entre deux appels
à `play_next_chain()` suffit — c'est tout le mécanisme.

`MatchSimulator.simulate()` reste un simple raccourci qui fait tourner un
`Match` jusqu'au bout d'un coup, pour les cas où on ne veut rien changer en
cours de route (tests, scripts simples).

**Prouvé par test statistique** (`tests/engine/test_match.py`) : passer en
tactique offensive à la mi-temps augmente mesurablement les buts en 2e
mi-temps ; faire rentrer un buteur bien meilleur aussi. Pas juste accepté
en entrée et ignoré.

---

## 9. Remplacements automatiques

`AutoSubstitution` (`engine/auto_substitution.py`) tourne après chaque
séquence, pour les deux équipes. Deux déclencheurs, bien distincts de
`Match.substitute()` (le contrôle manuel du §8, sans limite ni gestion de
banc) :

1. **Blessure** : dès qu'un joueur est blessé, tente immédiatement de faire
   entrer un remplaçant du **même poste** depuis le banc.
2. **Fatigue** : quand la forme d'un titulaire passe sous 0.72 (calibré
   empiriquement — même le joueur le plus sollicité descend rarement sous
   ~0.53 sur 90 minutes avec le taux de fatigue actuel), le titulaire le
   plus fatigué est remplacé s'il y a un joueur du même poste disponible.
   Un seul joueur par vérification, pas toute l'équipe d'un coup.

**Règle importante** : un carton rouge ne déclenche **jamais** de
remplacement automatique (en vrai foot, on ne remplace pas un joueur
expulsé — l'équipe joue à 10). Prouvé par test.

Les deux respectent une limite de 5 remplacements par équipe
(`Team.substitutions_used`), gérée uniquement par `AutoSubstitution` (pas
par `Match.substitute()`, qui reste un outil bas niveau sans limite).

⚠️ Pour que ça marche, il fallait un vrai banc de touche dans les équipes
de test/démo (`_teams.py`, `factories.py` génèrent maintenant 5 remplaçants
par équipe) — sinon `AutoSubstitution` n'a jamais personne à faire entrer.

**Bug (encore) rencontré et corrigé** : remplacer un joueur modifie
vraiment `starting_xi`/`bench` — mais comme les tests statistiques
réutilisent les mêmes objets `Team` sur des centaines de matchs, un
remplacement fait dans un match "contaminait" le suivant (composition
d'équipe différente → résultats différents → tests de reproductibilité
cassés). Solution : `Team` capture maintenant une copie de sa composition
d'origine à la construction, que `Match` restaure au coup d'envoi de
**chaque** nouveau match — le même principe que la remise à zéro de
`fitness`, appliqué cette fois à la composition de l'équipe elle-même.

---

## 10. Comment tester toi-même

```bash
cd backend
python3 -m pytest -q              # les 52 tests (unitaires + statistiques)
python3 scripts/simulate_demo.py  # un scénario fixe, feed brut d'événements
python3 scripts/menu.py           # MENU INTERACTIF, 6 scénarios :
```

Scénarios du menu :
1. Équipes égales (60 vs 60)
2. Forte vs faible, tactiques opposées (80 vs 45)
3. Buteur star qui porte une équipe moyenne
4. Ligne défensive haute vs ailiers rapides
5. Même niveau, mais sous la pluie
6. **Contrôle en direct** : changement de tactique + remplacement à la
   mi-temps, pour voir l'effet immédiat

Pour créer ton propre scénario : copier une fonction `_scenario_...` dans
`menu.py`, ajuster `overall`, les `Tactic(...)`, ou remplacer un joueur
précis via `make_player(..., shooting=95, pace=90, ...)`.

---

## 11. Ce qui reste à faire (court terme)

- Étendre le commentaire "flavoré par attribut" (§7) à d'autres types
  d'événements que `POSSESSION_PROGRESS` (tir, faute...)
- Brancher `width` et `marking_scheme` dans `TacticalMatchup`
- Hors-jeu, corners/coups francs comme séquences à part entière (pour
  l'instant une faute redémarre juste une chaîne normale)
- Après ça : API/WebSocket (Phase 2), persistance (Phase 3), frontend
  (Phase 4)... voir la roadmap complète dans `README.md`

---

## 12. Où trouver le détail technique précis

Ce fichier est un résumé pour se rappeler la vue d'ensemble. Pour le détail
exact destiné à coder (formules complètes, tables de poids, taxonomie
d'événements) :

- [`CLAUDE.md`](../CLAUDE.md) — vision globale, conventions
- [`backend/CLAUDE.md`](../backend/CLAUDE.md) — conventions de code backend
- [`backend/app/engine/CLAUDE.md`](../backend/app/engine/CLAUDE.md) — **le doc de référence du moteur**
- [`backend/app/commentary/CLAUDE.md`](../backend/app/commentary/CLAUDE.md) — la couche commentaire
- [`backend/app/engine/rating/CLAUDE.md`](../backend/app/engine/rating/CLAUDE.md) — la couche stats → notes
- [`README.md`](../README.md) — roadmap complète (10 phases)
