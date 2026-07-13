from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QTableWidget, QTableWidgetItem


COLUMNS = ["#", "Nom", "Pts", "2PTS %", "3PTS %", "Rebonds", "Pertes", "Fautes"]


class StatsPanel(QWidget):
    """Tableau récapitulatif des stats. Purement passif : reçoit un dict
    (produit par data/stats.py) et l'affiche, ne calcule rien lui-même."""

    def __init__(self, parent=None):
        super().__init__(parent)

        self.table = QTableWidget(0, len(COLUMNS))
        self.table.setHorizontalHeaderLabels(COLUMNS)

        layout = QVBoxLayout()
        layout.addWidget(QLabel("Statistiques"))
        layout.addWidget(self.table)
        self.setLayout(layout)

    def update_stats(self, summary: dict[int, dict]):
        self.table.setRowCount(len(summary))
        for row, (player_id, data) in enumerate(summary.items()):
            counts = data["counts"]
            values = [
                str(data["number"]),
                data["name"],
                str(data["points"]),
                f'{data["pct_2pts"]}%',
                f'{data["pct_3pts"]}%',
                str(data["rebonds"]),
                str(counts.get("PERTE_BALLE", 0)),
                str(counts.get("FAUTE", 0)),
            ]
            for col, value in enumerate(values):
                self.table.setItem(row, col, QTableWidgetItem(value))
