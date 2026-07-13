from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QListWidget, QListWidgetItem, QInputDialog, QMessageBox
)
from PySide6.QtCore import Signal, Qt

from data.models import Player


class PlayerPanel(QWidget):
    """Liste des joueurs + sélection du joueur actif.
    Émet player_selected(Player) quand l'utilisateur clique sur un joueur."""

    player_selected = Signal(object)   # Player
    player_added = Signal(object)      # Player

    def __init__(self, parent=None):
        super().__init__(parent)

        self.list_widget = QListWidget()
        self.list_widget.itemClicked.connect(self._on_item_clicked)

        add_button = QPushButton("+ Ajouter un joueur")
        add_button.clicked.connect(self._prompt_add_player)

        self.active_label = QLabel("Joueur actif : aucun")
        self.active_label.setStyleSheet("font-weight: bold;")

        layout = QVBoxLayout()
        layout.addWidget(QLabel("Joueurs"))
        layout.addWidget(self.list_widget)
        layout.addWidget(add_button)
        layout.addWidget(self.active_label)
        self.setLayout(layout)

        self._players: dict[int, Player] = {}

    def set_players(self, players: list[Player]):
        self.list_widget.clear()
        self._players.clear()
        for p in players:
            item = QListWidgetItem(f"#{p.number} - {p.name}")
            item.setData(Qt.UserRole, p.id)
            self.list_widget.addItem(item)
            self._players[p.id] = p

    def _prompt_add_player(self):
        name, ok = QInputDialog.getText(self, "Nouveau joueur", "Nom du joueur :")
        if not ok or not name.strip():
            return
        number, ok = QInputDialog.getInt(
            self, "Nouveau joueur", "Numéro de maillot :", 0, 0, 99
        )
        if not ok:
            return
        # Player.id sera assigné par la BDD ; on émet un Player "brouillon"
        self.player_added.emit(Player(id=None, name=name.strip(), number=number))

    def _on_item_clicked(self, item: QListWidgetItem):
        player_id = item.data(Qt.UserRole)
        player = self._players.get(player_id)
        if player:
            self.active_label.setText(f"Joueur actif : #{player.number} {player.name}")
            self.player_selected.emit(player)

    def require_active_player(self) -> bool:
        if self.active_label.text() == "Joueur actif : aucun":
            QMessageBox.warning(self, "Aucun joueur", "Sélectionne d'abord un joueur.")
            return False
        return True
