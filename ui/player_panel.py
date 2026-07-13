from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QPushButton,
    QListWidget, QListWidgetItem, QInputDialog, QMessageBox
)
from PySide6.QtCore import Signal, Qt

from data.models import Player


class PlayerPanel(QWidget):
    """Liste des joueurs + sélection du joueur actif."""

    player_selected = Signal(object)
    player_added = Signal(object)

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
        self._number_to_player: dict[int, Player] = {}

        # Permet de recevoir les touches
        self.setFocusPolicy(Qt.StrongFocus)


    def set_players(self, players: list[Player]):
        self.list_widget.clear()
        self._players.clear()
        self._number_to_player.clear()

        for p in players:
            item = QListWidgetItem(f"#{p.number} - {p.name}")
            item.setData(Qt.UserRole, p.id)

            self.list_widget.addItem(item)

            self._players[p.id] = p
            self._number_to_player[p.number] = p


    def select_player_by_number(self, number: int):
        """Sélectionne un joueur avec son numéro de maillot."""

        player = self._number_to_player.get(number)

        if player:
            self.active_label.setText(
                f"Joueur actif : #{player.number} {player.name}"
            )
            self.player_selected.emit(player)


    def keyPressEvent(self, event):

        key = event.key()

        # touches 0-9
        if Qt.Key_0 <= key <= Qt.Key_9:
            number = key - Qt.Key_0
            self.select_player_by_number(number)

        else:
            super().keyPressEvent(event)


    def _prompt_add_player(self):
        name, ok = QInputDialog.getText(
            self,
            "Nouveau joueur",
            "Nom du joueur :"
        )

        if not ok or not name.strip():
            return

        number, ok = QInputDialog.getInt(
            self,
            "Nouveau joueur",
            "Numéro de maillot :",
            0,
            0,
            99
        )

        if not ok:
            return

        self.player_added.emit(
            Player(
                id=None,
                name=name.strip(),
                number=number
            )
        )


    def _on_item_clicked(self, item):

        player_id = item.data(Qt.UserRole)
        player = self._players.get(player_id)

        if player:
            self.active_label.setText(
                f"Joueur actif : #{player.number} {player.name}"
            )
            self.player_selected.emit(player)


    def require_active_player(self):

        if self.active_label.text() == "Joueur actif : aucun":
            QMessageBox.warning(
                self,
                "Aucun joueur",
                "Sélectionne d'abord un joueur."
            )
            return False

        return True
