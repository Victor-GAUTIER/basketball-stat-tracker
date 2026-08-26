# Basketball Stat Tracker

Logiciel de scouting vidéo pour matchs de basketball : chargement d'une
vidéo, préparation du match (équipes + effectifs), enregistrement horodaté
des événements de jeu (tirs, rebonds, pertes de balle, fautes...), génération
de mini-montages vidéo à partir des actions marquantes, et export des
données.

## 📥 Télécharger l'application (utilisateurs)

Aucune installation de Python, ffmpeg ou autre dépendance n'est nécessaire.
Rendez-vous sur la page
[Releases](https://github.com/Victor-GAUTIER/basketball-stat-tracker/releases)
et téléchargez la dernière version :

- **Windows** : téléchargez `BasketballStatTracker.exe` et double-cliquez
dessus.
- **macOS** : téléchargez `BasketballStatTracker-macOS.zip`, décompressez-le,
puis double-cliquez sur `BasketballStatTracker.app`.
  ⚠️ Au premier lancement, macOS affichera un avertissement de sécurité
  ("Apple n'a pas pu confirmer...") car l'application n'est pas signée par un
  compte développeur Apple. Ouvrez **Réglages Système → Confidentialité et
  sécurité**, puis cliquez sur **"Ouvrir quand même"** à côté de la mention
  de l'application bloquée.

La section suivante (Installation depuis le code source) concerne
uniquement les personnes qui veulent développer ou modifier le projet.

## Installation (développement)

```
# (optionnel mais recommandé) créer un environnement virtuel
python -m venv .venv
source .venv/bin/activate  # sous Windows : .venv\Scripts\activate

# installer les dépendances
pip install -r requirements.txt
```

La génération de montages vidéo (voir plus bas) nécessite en plus `ffmpeg`
installé et accessible dans le PATH lorsqu'on lance l'application depuis les
sources. Ce n'est **pas** nécessaire pour les utilisateurs téléchargeant un
exécutable depuis les Releases : ffmpeg y est déjà embarqué.

## Lancement

```
python main.py
```

Au premier lancement, une base de données SQLite est créée automatiquement
dans un dossier propre à l'utilisateur, indépendant de l'endroit d'où
l'application est lancée :

- **Windows** : `%APPDATA%\BasketballStatTracker\basketball_stats.db`
- **macOS** : `~/Library/Application Support/BasketballStatTracker/basketball_stats.db`
- **Linux** : `~/.local/share/BasketballStatTracker/basketball_stats.db`

## Utilisation

1. **Écran de lancement (LaunchWindow)** : au démarrage, choisissez soit
**+ Nouveau match**, soit un match déjà enregistré dans la liste (double-clic
ou bouton "Ouvrir la sélection") pour reprendre son analyse là où vous
l'aviez laissée. Tous les matchs, équipes et joueurs sont conservés d'une
session à l'autre.
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
boutons d'événements, et la liste des **derniers événements enregistrés** (les plus récents en tête) pour vérifier rapidement sa saisie. Workflow :
cliquez sur un joueur puis sur un événement — il est enregistré avec le
timestamp vidéo courant.
4. **Statistiques (StatsWindow)** : le bouton "Voir les statistiques" ouvre
une fenêtre séparée avec le tableau complet des statistiques cumulées par
joueur, qui se rafraîchit automatiquement à chaque nouvel événement.
5. **Montages vidéo** : sélectionnez un ensemble d'événements et générez
automatiquement un clip regroupant les actions correspondantes (une marge
avant/après configurable est appliquée autour de chaque timestamp). Les
segments sont normalisés (résolution, fps) avant d'être concaténés, ce qui
permet de mélanger des vidéos de qualités différentes.
6. **Export** : le bouton "Exporter en CSV" génère un fichier CSV listant
tous les événements du match (timestamp, quart-temps, joueur, type
d'événement, coordonnées x/y si renseignées).

### Raccourcis clavier (dans la fenêtre d'analyse)

| Touche            | Action                                                          |
| ----------------- | --------------------------------------------------------------- |
| Espace            | Lecture / Pause                                                 |
| ← (flèche gauche) | Recule de 5s                                                    |
| → (flèche droite) | Avance de 5s                                                    |
| Ctrl+Z            | Annule le dernier événement                                     |
| Ctrl+E            | Exporter en CSV                                                 |
| Ctrl+I            | Ouvrir les statistiques                                         |
| 2 / Maj+2         | 2PTS+ / 2PTS-                                                   |
| 3 / Maj+3         | 3PTS+ / 3PTS-                                                   |
| 1 / Maj+1         | LF+ / LF-                                                       |
| O / D             | Rebond offensif / défensif                                      |
| A / T / S / B / F | Passe décisive / perte de balle / interception / contre / faute |

## Architecture

```
basketball-stat-tracker/
├── main.py                        # point d'entrée
├── controller/
│   ├── setup_controller.py        # logique de création d'un match
│   └── analysis_controller.py     # logique d'enregistrement des événements
├── data/
│   ├── database.py                # couche d'accès SQLite (CRUD)
│   ├── models.py                  # dataclasses Team / Player / Game / Event
│   └── ffmpeg_path.py             # résolution du chemin ffmpeg (dev vs. exécutable compilé)
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
│   ├── csv_export.py              # export CSV des événements
│   └── video_export_worker.py     # génération de montages vidéo (découpe + concaténation ffmpeg)
├── assets/                        # ressources statiques (icônes, etc.)
└── .github/
    └── workflows/
        └── build.yml               # build automatique Windows + macOS et publication des releases
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

## Montages vidéo et ffmpeg

La génération de montages (`export/video_export_worker.py`) appelle
`ffmpeg` en ligne de commande pour découper puis concaténer les segments
vidéo autour des événements sélectionnés.

- **Exécutables téléchargés depuis les Releases** : ffmpeg est embarqué
directement dans le `.exe`/`.app`, aucune installation requise.
- **Lancement depuis les sources** (`python main.py`) : ffmpeg doit être
installé sur la machine et accessible dans le PATH.

`data/ffmpeg_path.py` détecte automatiquement si l'application tourne en
mode développement ou compilée (PyInstaller), et résout le bon chemin vers
le binaire dans chaque cas.

## Build et publication des releases

Le build est entièrement automatisé via GitHub Actions
(`.github/workflows/build.yml`) : à chaque push d'un tag de la forme `vX.Y.Z`
ou `vX.Y.Z-beta`, deux machines (Windows et macOS) compilent l'application
avec PyInstaller, y embarquent ffmpeg, puis publient automatiquement les
fichiers sur une nouvelle Release GitHub, marquée pré-version si le tag
contient `-beta`.

Pour publier une nouvelle version :

```bash
git tag v0.2.0-beta
git push origin v0.2.0-beta
```

L'avancement du build peut être suivi dans l'onglet **Actions** du dépôt.


## Prérequis techniques

- Python 3.12
- PySide6 (Qt Widgets + QtMultimedia pour la lecture vidéo)
- SQLite (inclus dans la bibliothèque standard Python)
- ffmpeg (uniquement pour lancer depuis les sources ou pour builder ;
embarqué automatiquement dans les exécutables publiés)

## Notes

- Le module vidéo utilise `QtMultimedia`/`QtMultimediaWidgets`. Sur certains
systèmes Linux, l'installation de backends multimédia (GStreamer/FFmpeg)
peut être nécessaire pour la lecture de certains formats vidéo. Sous
Windows et macOS, PySide6 embarque les backends nécessaires.
- La base de données est stockée dans un dossier standard propre à chaque
utilisateur (voir section Lancement ci-dessus), et non plus dans le dossier
d'où l'application est lancée.
