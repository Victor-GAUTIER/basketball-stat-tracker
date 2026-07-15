from __future__ import annotations

import math

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import (
    QPainter,
    QPixmap,
    QTransform,
)
from PySide6.QtWidgets import (
    QWidget,
    QSizePolicy,
)


class ShotChartWidget(QWidget):
    """
    Terrain de basket interactif pour enregistrer les tirs.
    """

    shot_clicked = Signal(float, float, bool)


    def __init__(
        self,
        svg_path: str,
        parent=None
    ):
        super().__init__(parent)


        self.pixmap = QPixmap(
            svg_path
        )


        self.setMinimumSize(
            300,
            150
        )


        self.setMaximumHeight(
            150
        )


        self.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Fixed
        )



    # =====================================================
    # Paramètres terrain
    # =====================================================

    def court_parameters(self):

        return {

            "basket_left_x": 0.18,
            "basket_right_x": 0.81,
            "basket_y": 0.50,


            # rayon arc 3 points
            "radius": 0.17,


            # corners
            "corner_x": 0.20,
            "corner_y_min": 0.15,
            "corner_y_max": 0.85,


            # rectangle zone 2 points sous chaque panier
            "paint_x": 0.32,
            "paint_y_min": 0.35,
            "paint_y_max": 0.65,
        }



    # =====================================================
    # Affichage terrain uniquement
    # =====================================================

    def paintEvent(
        self,
        event
    ):

        if self.pixmap.isNull():
            return


        painter = QPainter(
            self
        )


        court = self.pixmap.transformed(
            QTransform().rotate(90),
            Qt.TransformationMode.SmoothTransformation
        )


        court = court.scaled(
            self.width(),
            self.height(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )


        x_offset = (
            self.width()
            -
            court.width()
        ) // 2


        y_offset = (
            self.height()
            -
            court.height()
        ) // 2


        painter.drawPixmap(
            x_offset,
            y_offset,
            court
        )



    # =====================================================
    # Clic terrain
    # =====================================================

    def mousePressEvent(
        self,
        event
    ):

        if event.button() != Qt.MouseButton.LeftButton:
            return


        x = (
            event.position().x()
            /
            self.width()
        )


        y = (
            event.position().y()
            /
            self.height()
        )


        # True = tir raté
        missed = (
            event.modifiers()
            == Qt.KeyboardModifier.ShiftModifier
        )


        print(
            "CLICK TERRAIN",
            x,
            y,
            "RATE" if missed else "REUSSI"
        )


        self.shot_clicked.emit(
            x,
            y,
            missed
        )



    # =====================================================
    # Détection 2 ou 3 points
    # =====================================================

    def shot_value(
        self,
        x: float,
        y: float
    ) -> str:

        params = self.court_parameters()



        # ==========================
        # Zone intérieure sous panier
        # ==========================

        if x < 0.5:

            paint = (
                x <= params["paint_x"]
                and
                params["paint_y_min"]
                <= y
                <=
                params["paint_y_max"]
            )

        else:

            paint = (
                x >= 1 - params["paint_x"]
                and
                params["paint_y_min"]
                <= y
                <=
                params["paint_y_max"]
            )


        if paint:

            return "2PTS"



        # ==========================
        # Corners
        # ==========================

        if (
            x < params["corner_x"]
            and
            params["corner_y_min"]
            <= y
            <= params["corner_y_max"]
        ):
            return "3PTS"



        if (
            x > 1 - params["corner_x"]
            and
            params["corner_y_min"]
            <= y
            <= params["corner_y_max"]
        ):
            return "3PTS"



        # ==========================
        # Distance panier
        # ==========================

        if x < 0.5:

            basket_x = params["basket_left_x"]

        else:

            basket_x = params["basket_right_x"]


        distance = math.sqrt(
            (x - basket_x) ** 2
            +
            (y - params["basket_y"]) ** 2
        )


        if distance >= params["radius"]:

            return "3PTS"


        return "2PTS"
