"""Widget de filtre à sélection multiple, réutilisé dans les onglets de
TeamAnalysisWindow (joueurs, matchs, équipes...).
"""

from __future__ import annotations

from typing import Callable, List, Optional, Tuple

from PySide6.QtGui import QAction
from PySide6.QtWidgets import QMenu, QPushButton, QWidget


class MultiSelectFilter(QPushButton):
    """Bouton ouvrant un menu à cases à cocher.

    Toutes les entrées sont cochées par défaut (= pas de filtre actif).
    `selected_ids()` retourne None dans ce cas, pour distinguer "tout est
    coché" de "un sous-ensemble précis est coché".
    """

    def __init__(
        self,
        label: str,
        items: List[Tuple[int, str]],
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)

        self._label = label
        self.on_change: Optional[Callable[[], None]] = None
        self._actions: List[QAction] = []

        self.setMenu(QMenu(self))
        self.set_items(items)

    def set_items(self, items: List[Tuple[int, str]]) -> None:

        menu = self.menu()
        menu.clear()
        self._actions.clear()

        for item_id, item_label in items:
            action = QAction(item_label, self)
            action.setCheckable(True)
            action.setChecked(True)
            action.setData(item_id)
            action.toggled.connect(self._on_toggled)
            menu.addAction(action)
            self._actions.append(action)

        self._update_text()

    def selected_ids(self) -> Optional[List[int]]:
        """None = tout est coché = pas de filtre à appliquer."""

        if not self._actions:
            return None

        selected = [a.data() for a in self._actions if a.isChecked()]

        if len(selected) == len(self._actions):
            return None

        return selected

    def _on_toggled(self, *_args) -> None:
        self._update_text()
        if self.on_change:
            self.on_change()

    def _update_text(self) -> None:

        selected = [a for a in self._actions if a.isChecked()]

        if not self._actions or len(selected) == len(self._actions):
            self.setText(f"{self._label} : tous")
        elif not selected:
            self.setText(f"{self._label} : aucun")
        elif len(selected) == 1:
            self.setText(f"{self._label} : {selected[0].text()}")
        else:
            self.setText(f"{self._label} : {len(selected)} sélectionnés")
