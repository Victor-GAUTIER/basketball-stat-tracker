"""Fenêtre indépendante affichant les statistiques complètes des joueurs.

Ouverte depuis la fenêtre d'analyse (bouton "Voir les statistiques"), elle
reste synchronisée : chaque nouvel événement enregistré ou annulé dans
AnalysisWindow déclenche un rafraîchissement de cette fenêtre si elle est
ouverte.
"""

from __future__ import annotations

from typing import List, Optional

from PySide6.QtWidgets import QMainWindow, QWidget

from controller.analysis_controller import AnalysisController
from data.models import Player
from ui.analysis.stats_panel import StatsPanel


class StatsWindow(QMainWindow):
    """Fenêtre dédiée aux statistiques cumulées des joueurs d'un match."""

    def __init__(self, controller: AnalysisController, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.controller = controller

        self.setWindowTitle("Statistiques des joueurs")
        self.resize(950, 500)

        self.stats_panel = StatsPanel(self)
        self.setCentralWidget(self.stats_panel)

    def refresh(self, players: List[Player]) -> None:
        """Recalcule et réaffiche les statistiques pour la liste de joueurs donnée."""
        stats = self.controller.get_player_stats()
        self.stats_panel.refresh(players, stats)
