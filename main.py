"""Point d'entrée de l'application Basketball Stat Tracker.

Lance l'application PySide6 et affiche la fenêtre de préparation du match
(SetupWindow). Lancer avec : python main.py
"""

from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from data.database import Database
from ui.setup.setup_window import SetupWindow


def main() -> None:
    app = QApplication(sys.argv)
    app.setApplicationName("Basketball Stat Tracker")

    # La base SQLite est créée (si besoin) à la racine du projet.
    database = Database("basketball_stats.db")

    window = SetupWindow(database)
    window.show()

    exit_code = app.exec()
    database.close()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
