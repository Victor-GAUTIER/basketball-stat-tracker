"""Gestion du thème d'affichage (sombre / clair) de l'application.

Centralisé ici plutôt que dans main.py pour être importable depuis
n'importe quelle fenêtre sans risque d'import circulaire.
"""

from __future__ import annotations

from typing import Dict, Optional

from PySide6.QtCore import QObject, QSettings, Signal
from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication


ORG_NAME = "RennesAvenir"
APP_NAME = "BasketballStatTracker"

THEME_DARK = "dark"
THEME_LIGHT = "light"
DEFAULT_THEME = THEME_DARK


# Couleurs utilisées par les graphiques matplotlib (fond de figure, fond
# de carte, texte principal, texte secondaire), selon le thème actif.
CHART_COLORS: Dict[str, Dict[str, str]] = {
    THEME_DARK: {
        "background": "#121212",
        "card": "#434343",
        "text": "#eeeeee",
        "secondary_text": "#aaaaaa",
    },
    THEME_LIGHT: {
        "background": "#ffffff",
        "card": "#ffffff",
        "text": "#141414",
        "secondary_text": "#555555",
    },
}


class _ThemeManager(QObject):
    """Signal émis à chaque changement de thème, pour que les fenêtres
    déjà ouvertes (graphiques matplotlib notamment, qui ne suivent pas la
    QPalette Qt) puissent se reconstruire avec les bonnes couleurs."""

    theme_changed = Signal(str)


theme_manager = _ThemeManager()


def get_theme_setting() -> str:
    """Lit le thème choisi par l'utilisateur (persistant entre les
    lancements), ou le thème par défaut si aucun choix n'a encore été
    fait."""

    settings = QSettings(ORG_NAME, APP_NAME)

    return settings.value("appearance/theme", DEFAULT_THEME)


def set_theme_setting(theme: str) -> None:
    """Sauvegarde le thème choisi, pour qu'il soit repris au prochain
    lancement."""

    settings = QSettings(ORG_NAME, APP_NAME)

    settings.setValue("appearance/theme", theme)


def get_chart_colors(theme: Optional[str] = None) -> Dict[str, str]:
    """Couleurs à utiliser dans les graphiques matplotlib pour le thème
    donné (ou le thème actif si non précisé)."""

    theme = theme or get_theme_setting()

    return CHART_COLORS.get(theme, CHART_COLORS[THEME_DARK])


def apply_theme(app: QApplication, theme: str) -> None:
    """Applique le thème sombre ou clair à toute l'application, et
    prévient les fenêtres ouvertes (via theme_changed) pour qu'elles
    reconstruisent leurs graphiques avec les nouvelles couleurs."""

    if theme == THEME_LIGHT:
        _apply_light_theme(app)
    else:
        _apply_dark_theme(app)

    theme_manager.theme_changed.emit(theme)


def _apply_dark_theme(app: QApplication) -> None:

    app.setStyle("Fusion")

    palette = QPalette()

    palette.setColor(QPalette.ColorRole.Window, QColor(30, 30, 30))
    palette.setColor(QPalette.ColorRole.WindowText, QColor(238, 238, 238))

    palette.setColor(QPalette.ColorRole.Base, QColor(37, 37, 37))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor(47, 47, 47))

    palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(238, 238, 238))
    palette.setColor(QPalette.ColorRole.ToolTipText, QColor(238, 238, 238))

    palette.setColor(QPalette.ColorRole.Text, QColor(238, 238, 238))
    palette.setColor(QPalette.ColorRole.PlaceholderText, QColor(170, 170, 170))

    palette.setColor(QPalette.ColorRole.Button, QColor(53, 53, 53))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor(238, 238, 238))

    palette.setColor(QPalette.ColorRole.BrightText, QColor(255, 0, 0))

    palette.setColor(QPalette.ColorRole.Highlight, QColor(41, 127, 254))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor(255, 255, 255))

    palette.setColor(
        QPalette.ColorGroup.Disabled,
        QPalette.ColorRole.Text,
        QColor(120, 120, 120),
    )
    palette.setColor(
        QPalette.ColorGroup.Disabled,
        QPalette.ColorRole.ButtonText,
        QColor(120, 120, 120),
    )
    palette.setColor(
        QPalette.ColorGroup.Disabled,
        QPalette.ColorRole.WindowText,
        QColor(120, 120, 120),
    )

    app.setPalette(palette)

    app.setStyleSheet(
        """
        QToolTip {
            color: #eeeeee;
            background-color: #2a2a2a;
            border: 1px solid #555555;
        }
        QMenu {
            background-color: #2a2a2a;
            color: #eeeeee;
            border: 1px solid #555555;
        }
        QMenu::item:selected {
            background-color: #297ffe;
        }
        """
    )


def _apply_light_theme(app: QApplication) -> None:

    app.setStyle("Fusion")

    palette = QPalette()

    palette.setColor(QPalette.ColorRole.Window, QColor(255, 255, 255))
    palette.setColor(QPalette.ColorRole.WindowText, QColor(20, 20, 20))

    palette.setColor(QPalette.ColorRole.Base, QColor(255, 255, 255))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor(245, 245, 245))

    palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(255, 255, 255))
    palette.setColor(QPalette.ColorRole.ToolTipText, QColor(20, 20, 20))

    palette.setColor(QPalette.ColorRole.Text, QColor(20, 20, 20))
    palette.setColor(QPalette.ColorRole.PlaceholderText, QColor(130, 130, 130))

    palette.setColor(QPalette.ColorRole.Button, QColor(240, 240, 240))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor(20, 20, 20))

    palette.setColor(QPalette.ColorRole.BrightText, QColor(255, 0, 0))

    palette.setColor(QPalette.ColorRole.Highlight, QColor(41, 127, 254))
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor(255, 255, 255))

    palette.setColor(
        QPalette.ColorGroup.Disabled,
        QPalette.ColorRole.Text,
        QColor(160, 160, 160),
    )
    palette.setColor(
        QPalette.ColorGroup.Disabled,
        QPalette.ColorRole.ButtonText,
        QColor(160, 160, 160),
    )
    palette.setColor(
        QPalette.ColorGroup.Disabled,
        QPalette.ColorRole.WindowText,
        QColor(160, 160, 160),
    )

    app.setPalette(palette)

    app.setStyleSheet(
        """
        QToolTip {
            color: #141414;
            background-color: #ffffff;
            border: 1px solid #cccccc;
        }
        QMenu {
            background-color: #ffffff;
            color: #141414;
            border: 1px solid #cccccc;
        }
        QMenu::item:selected {
            background-color: #297ffe;
            color: #ffffff;
        }
        """
    )

def get_court_asset_name(theme: Optional[str] = None) -> str:
    """Nom du fichier SVG du terrain à utiliser pour le thème donné (ou
    le thème actif si non précisé)."""

    theme = theme or get_theme_setting()

    return "court_light.svg" if theme == THEME_LIGHT else "court.svg"
