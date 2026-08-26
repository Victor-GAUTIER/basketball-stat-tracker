"""Point d'entrée de l'application Basketball Stat Tracker."""

from __future__ import annotations

import sys
import traceback
from pathlib import Path

from PySide6.QtWidgets import QApplication, QMessageBox

from data.database import Database
from ui.launch_window import LaunchWindow


def show_exception(exc_type, exc_value, exc_traceback) -> None:
    """Affiche et sauvegarde les exceptions non gérées."""

    error = "".join(
        traceback.format_exception(
            exc_type,
            exc_value,
            exc_traceback,
        )
    )

    # Sauvegarde dans un fichier à côté de l'exécutable.
    try:
        log_path = Path("error.log")
        log_path.write_text(
            error,
            encoding="utf-8",
        )
    except Exception:
        pass

    # Affichage dans l'application.
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

    sys.excepthook = show_exception

    database = Database()

    window = LaunchWindow(database)
    window.show()

    exit_code = app.exec()
    database.close()

    sys.exit(exit_code)


if __name__ == "__main__":
    main()
