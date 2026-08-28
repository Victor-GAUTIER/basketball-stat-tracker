"""Point d'entrée de l'application Basketball Stat Tracker."""

from __future__ import annotations

import sys
import traceback
from pathlib import Path

from PySide6.QtWidgets import QApplication, QMessageBox

from data.database import Database
from ui.launch_window import LaunchWindow
from ui.theme import apply_theme, get_theme_setting

from data.event_config import event_config


def show_exception(exc_type, exc_value, exc_traceback) -> None:
    """Affiche et sauvegarde les exceptions non gérées."""

    error = "".join(
        traceback.format_exception(
            exc_type,
            exc_value,
            exc_traceback,
        )
    )


    try:
        QMessageBox.critical(
            None,
            "Erreur de l'application",
            "Une erreur inattendue est survenue.\n\n"
            + error,
        )
    except Exception:
        pass


def main() -> None:
    app = QApplication(sys.argv)
    app.setApplicationName("Basketball Stat Tracker")
    app.setOrganizationName("RennesAvenir")

    apply_theme(app, get_theme_setting())

    sys.excepthook = show_exception

    database = Database()

    event_config.load(database)

    window = LaunchWindow(database)
    window.show()

    exit_code = app.exec()
    database.close()

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
