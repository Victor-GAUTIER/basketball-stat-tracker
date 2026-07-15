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

1. **Préparation du match (SetupWindow)** : renseignez le nom du match, la
   date et sélectionnez le fichier vidéo. Pour chaque équipe, saisissez le
   nom et ajoutez les joueurs (nom + numéro) via le bouton "Ajouter un
   joueur". Cliquez sur **Commencer l'analyse**.
2. **Analyse vidéo (AnalysisWindow)** : à gauche, le lecteur vidéo (lecture,
   pause, ±5s, curseur de progression). À droite, les deux effectifs, le
   sélecteur de quart-temps, les boutons d'événements (2PTS+, 3PTS-, RO, RD,
   AST, TO, STL, BLK, FAUTE...) et le tableau de statistiques en direct.
   Workflow : cliquez sur un joueur puis sur un événement — il est
   enregistré avec le timestamp vidéo courant. Le bouton "Annuler le
   dernier événement" permet de corriger une erreur de saisie.
3. **Export** : le bouton "Exporter en CSV" génère un fichier CSV listant
   tous les événements du match (timestamp, quart-temps, joueur, type
   d'événement, coordonnées x/y si renseignées).

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
│   ├── setup/
│   │   ├── setup_window.py        # fenêtre de préparation du match
│   │   ├── team_editor.py         # widget de composition d'une équipe
│   │   └── player_editor.py       # boîte de dialogue d'ajout de joueur
│   └── analysis/
│       ├── analysis_window.py     # fenêtre principale d'analyse
│       ├── video_panel.py         # lecteur vidéo + contrôles
│       ├── player_panel.py        # listes des deux effectifs
│       ├── event_panel.py         # boutons d'événements
│       └── stats_panel.py         # tableau de statistiques en direct
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

- Raccourcis clavier configurables pour les boutons d'événements.
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
