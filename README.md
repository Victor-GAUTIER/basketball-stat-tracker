# Basketball Stat Tracker

Logiciel de scouting vidéo pour matchs de basketball : chargement d'une
vidéo, préparation du match (équipes + effectifs), enregistrement horodaté
des événements de jeu (tirs, rebonds, pertes de balle, fautes...), et export
des données.

## Installation

```bash
# (optionnel mais recommandé) créer un environnement virtuel
python -m venv .venv
source .venv/bin/activate  # sous Windows : .venv\Scripts\activate

# installer les dépendances
pip install -r requirements.txt
```

## Lancement

```bash
python main.py
```

La base de données SQLite (`basketball_stats.db`) est créée automatiquement
à la racine du projet au premier lancement.

## Utilisation

1. **Écran de lancement (LaunchWindow)** : au démarrage, choisissez soit
   **+ Nouveau match**, soit un match déjà enregistré dans la liste (double-clic
   ou bouton "Ouvrir la sélection") pour reprendre son analyse là où vous
   l'aviez laissée. Tous les matchs, équipes et joueurs sont conservés d'une
   session à l'autre dans `basketball_stats.db`.
2. **Préparation du match (SetupWindow)** : renseignez le nom du match, la
   date et sélectionnez le fichier vidéo. Pour chaque équipe, vous pouvez soit
   choisir **une équipe déjà enregistrée** dans le menu déroulant (son nom et
   son effectif sont alors préremplis automatiquement), soit saisir une
   nouvelle équipe et ajouter les joueurs (nom + numéro) via le bouton
   "Ajouter un joueur". Cliquez sur **Commencer l'analyse**.
3. **Analyse vidéo (AnalysisWindow)** : à gauche, le lecteur vidéo avec un
   bouton unique lecture/pause, ±5s et une barre de progression cliquable
   (un clic n'importe où sur la barre déplace immédiatement la lecture à cet
   endroit). À droite, les deux effectifs, le sélecteur de quart-temps, les
   boutons d'événements, et la liste des **derniers événements enregistrés**
   (les plus récents en tête) pour vérifier rapidement sa saisie. Workflow :
   cliquez sur un joueur puis sur un événement — il est enregistré avec le
   timestamp vidéo courant.
4. **Statistiques (StatsWindow)** : le bouton "Voir les statistiques" ouvre
   une fenêtre séparée avec le tableau complet des statistiques cumulées par
   joueur, qui se rafraîchit automatiquement à chaque nouvel événement.
5. **Export** : le bouton "Exporter en CSV" génère un fichier CSV listant
   tous les événements du match (timestamp, quart-temps, joueur, type
   d'événement, coordonnées x/y si renseignées).

### Raccourcis clavier (dans la fenêtre d'analyse)

| Touche              | Action              |
|---------------------|---------------------|
| Espace               | Lecture / Pause     |
| ← (flèche gauche)   | Recule de 5s        |
| → (flèche droite)   | Avance de 5s        |
| Ctrl+Z               | Annule le dernier événement |
| Ctrl+E                | Exporter en CSV     |
| Ctrl+I                 | Ouvrir les statistiques |
| 2 / Maj+2            | 2PTS+ / 2PTS-        |
| 3 / Maj+3            | 3PTS+ / 3PTS-        |
| 1 / Maj+1            | LF+ / LF-            |
| O / D                 | Rebond offensif / défensif |
| A / T / S / B / F   | Passe décisive / perte de balle / interception / contre / faute |

Ces raccourcis sont pour l'instant fixes (codés dans `event_panel.py` et
`video_panel.py`) ; les rendre configurables par l'utilisateur est une
évolution naturelle listée plus bas.

## Architecture

```text
basketball-stat-tracker/
├── main.py                        # point d'entrée
├── controller/
│   ├── setup_controller.py        # logique de création d'un match
│   └── analysis_controller.py     # logique d'enregistrement des événements
├── data/
│   ├── database.py                # couche d'accès SQLite (CRUD)
│   └── models.py                  # dataclasses Team / Player / Game / Event
├── ui/
│   ├── launch_window.py           # écran d'accueil : nouveau match / reprise
│   ├── setup/
│   │   ├── setup_window.py        # fenêtre de préparation du match
│   │   ├── team_editor.py         # composition d'une équipe (+ rechargement d'une équipe existante)
│   │   └── player_editor.py       # boîte de dialogue d'ajout de joueur
│   └── analysis/
│       ├── analysis_window.py     # fenêtre principale d'analyse (+ raccourcis clavier)
│       ├── video_panel.py         # lecteur vidéo (lecture/pause unique, barre cliquable)
│       ├── player_panel.py        # listes des deux effectifs
│       ├── event_panel.py         # boutons d'événements + raccourcis
│       ├── recent_events_panel.py # liste des derniers événements enregistrés
│       ├── stats_panel.py         # tableau de statistiques (widget réutilisable)
│       └── stats_window.py        # fenêtre séparée des statistiques complètes
├── export/
│   └── csv_export.py              # export CSV des événements
└── assets/                        # ressources statiques (icônes, etc.)
```

Le projet suit une architecture MVC :

- **Model** (`data/`) : schéma SQLite et dataclasses.
- **View** (`ui/`) : widgets PySide6, aucune logique métier.
- **Controller** (`controller/`) : fait le pont entre la vue et la base de
  données, contient toute la logique métier.

## Schéma de base de données

```
teams(id, name)
players(id, team_id, name, number)
games(id, name, date, video_path)
game_teams(game_id, team_id, is_home)
game_players(game_id, player_id)
events(id, game_id, player_id, timestamp, quarter, event_type, x, y)
```

Ce schéma permet à un même joueur de participer à plusieurs matchs, avec des
effectifs différents d'un match à l'autre, et autorise le calcul de
statistiques par joueur, par équipe ou par match/saison.

## Évolutions prévues (architecture déjà prête pour)

- Rendre les raccourcis clavier configurables par l'utilisateur (actuellement
  fixes, définis dans `EVENT_TYPES` et `VideoPanel`).
- Score en direct et gestion des quarts-temps (le champ `quarter` existe déjà
  en base et un sélecteur est présent dans l'UI).
- Gestion des remplacements et des 5 joueurs sur le terrain.
- Terrain interactif pour placer les tirs (les colonnes `x`/`y` de la table
  `events` sont déjà prévues à cet effet).
- Cartes de tirs (shot charts) à partir des coordonnées `x`/`y`.
- Tracking automatique par IA (le `video_panel.py` isole déjà l'accès à la
  vidéo, facilitant un futur module de traitement d'image).
- Exports Excel et PDF (à ajouter dans `export/`, à côté de `csv_export.py`).

## Prérequis techniques

- Python 3.12
- PySide6 (Qt Widgets + QtMultimedia pour la lecture vidéo)
- SQLite (inclus dans la bibliothèque standard Python)

## Notes

- Le module vidéo utilise `QtMultimedia`/`QtMultimediaWidgets`. Sur certains
  systèmes Linux, l'installation de backends multimédia (GStreamer/FFmpeg)
  peut être nécessaire pour la lecture de certains formats vidéo. Sous
  Windows et macOS, PySide6 embarque les backends nécessaires.
