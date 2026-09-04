"""Widget de filtre à sélection multiple, réutilisé dans les onglets de
TeamAnalysisWindow (joueurs, matchs, équipes...) et dans PlayByPlayPanel.

Comportement de sélection :
- Par défaut, tout est coché (= aucun filtre actif).
- Tant que tout est coché, cliquer sur un élément désélectionne tous les
  autres et ne garde que celui-ci (sélection exclusive au premier clic).
- Les clics suivants s'ajoutent/se retirent normalement de la sélection.
- Si, en cochant manuellement, on finit par tout recocher, on repasse en
  mode "tous" (un nouveau clic redeviendra exclusif).
- L'entrée "Tout sélectionner" en haut du menu recoche tout d'un coup et
  repasse également en mode "tous".
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

        # True tant qu'aucune sélection exclusive n'a été faite (état
        # initial et après "Tout sélectionner") : le prochain clic sur un
        # élément deviendra alors une sélection exclusive (voir
        # _on_action_toggled).
        self._all_selected_mode = True

        # Empêche _on_action_toggled de réagir aux modifications de case
        # à cocher que l'on déclenche nous-mêmes par programme (sélection
        # exclusive, "Tout sélectionner").
        self._updating = False

        self.setMenu(QMenu(self))
        self.set_items(items)

    def set_items(self, items: List[Tuple[int, str]]) -> None:

        # Préserve l'état coché/décoché des entrées déjà présentes : sans
        # ça, tout appel à set_items() (ex. refresh() de PlayByPlayPanel,
        # rappelé après CHAQUE événement enregistré) réinitialiserait le
        # filtre choisi par l'utilisateur. Une entrée nouvellement apparue
        # (ex. nouveau type d'événement) est cochée par défaut, comme au
        # premier remplissage.
        previous_state = {
            action.data(): action.isChecked()
            for action in self._actions
        }

        menu = self.menu()
        menu.clear()
        self._actions.clear()

        select_all_action = QAction("Tout sélectionner", self)
        select_all_action.triggered.connect(self.select_all)
        menu.addAction(select_all_action)

        if items:
            menu.addSeparator()

        for item_id, item_label in items:
            action = QAction(item_label, self)
            action.setCheckable(True)
            action.setChecked(previous_state.get(item_id, True))
            action.setData(item_id)
            action.toggled.connect(
                lambda checked, a=action: self._on_action_toggled(a, checked)
            )
            menu.addAction(action)
            self._actions.append(action)

        # Repart en mode "tous" si, après reconstruction, tout se trouve
        # effectivement coché (cas du premier remplissage, ou d'une
        # sélection qui couvrait déjà tout).
        self._all_selected_mode = (
            not self._actions
            or all(a.isChecked() for a in self._actions)
        )

        self._update_text()

    # =====================================================
    # Sélection
    # =====================================================

    def select_all(self) -> None:
        """Recoche tout et repasse en mode "tous" (le prochain clic sur
        un élément redeviendra une sélection exclusive)."""

        self._updating = True

        for action in self._actions:
            action.setChecked(True)

        self._updating = False

        self._all_selected_mode = True

        self._update_text()

        if self.on_change:
            self.on_change()

    def selected_ids(self) -> Optional[List[int]]:
        """None = tout est coché = pas de filtre à appliquer."""

        if not self._actions:
            return None

        selected = [a.data() for a in self._actions if a.isChecked()]

        if len(selected) == len(self._actions):
            return None

        return selected

    # =====================================================
    # Réaction aux clics
    # =====================================================

    def _on_action_toggled(self, action: QAction, checked: bool) -> None:

        if self._updating:
            return

        if self._all_selected_mode:

            # Premier clic depuis l'état "tous" : sélection exclusive de
            # l'élément cliqué, quel que soit le sens du clic (coché ou
            # décoché), pour repartir d'une sélection nette d'un seul
            # élément plutôt que de "tous sauf celui-ci".
            self._updating = True

            for other in self._actions:
                other.setChecked(other is action)

            self._updating = False

            self._all_selected_mode = False

        elif all(a.isChecked() for a in self._actions):

            # Les clics manuels ont fini par tout recocher : on repasse
            # en mode "tous", le prochain clic redeviendra exclusif.
            self._all_selected_mode = True

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
