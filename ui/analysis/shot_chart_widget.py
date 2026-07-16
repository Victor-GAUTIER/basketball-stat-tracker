from __future__ import annotations

import math

from PySide6.QtCore import Qt, Signal, QRectF, QPointF
from PySide6.QtGui import (
    QColor,
    QPainter,
    QPixmap,
    QTransform,
    QPen,
)
from PySide6.QtWidgets import (
    QWidget,
    QSizePolicy,
)


class ShotChartWidget(QWidget):

    shot_clicked = Signal(float, float, bool)


    LEFT_SIDE_COLOR = QColor(
        52,
        152,
        219,
        70
    )

    RIGHT_SIDE_COLOR = QColor(
        230,
        126,
        34,
        70
    )


    def __init__(
        self,
        svg_path: str,
        parent=None
    ):

        super().__init__(parent)

        self.pixmap = QPixmap(svg_path)


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


        self._home_attacks_right = True
        self._home_label = "Domicile"
        self._away_label = "Extérieur"

        self.last_shot = None



    # =====================================================
    # Paramètres géométriques
    # =====================================================

    def court_parameters(self):

        return {

            # positions des paniers
            "basket_left_x": 0.12,
            "basket_right_x": 0.88,
            "basket_y": 0.50,


            # rayon de la zone verte
            "radius": 0.34,


            # rectangle vert
            "paint_x": 0.15,
            "paint_y_min": 0.15,
            "paint_y_max": 0.85,
        }



    # =====================================================
    # Géométrie UNIQUE utilisée partout
    # =====================================================

    def get_geometry(self):

        params = self.court_parameters()


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


        w = court.width()
        h = court.height()


        radius = (
            params["radius"]
            *
            min(w, h)
        )


        return {

            "x_offset": x_offset,
            "y_offset": y_offset,

            "w": w,
            "h": h,

            "radius": radius,


            "left_basket": (
                x_offset
                +
                params["basket_left_x"] * w,

                y_offset
                +
                params["basket_y"] * h
            ),


            "right_basket": (
                x_offset
                +
                params["basket_right_x"] * w,

                y_offset
                +
                params["basket_y"] * h
            )
        }



    # =====================================================
    # Orientation
    # =====================================================

    def set_orientation(
        self,
        home_attacks_right,
        home_label,
        away_label
    ):

        self._home_attacks_right = home_attacks_right
        self._home_label = home_label
        self._away_label = away_label

        self.update()



    # =====================================================
    # Dessin
    # =====================================================

    def paintEvent(self, event):

        if self.pixmap.isNull():
            return


        painter = QPainter(self)

        painter.setRenderHint(
            QPainter.RenderHint.Antialiasing
        )


        geometry = self.get_geometry()


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


        painter.drawPixmap(
            geometry["x_offset"],
            geometry["y_offset"],
            court
        )


        # ==========================
        # Zones équipes selon panier attaqué
        # ==========================

        half = geometry["w"] // 2


        if self._home_attacks_right:

            left_color = self.RIGHT_SIDE_COLOR
            right_color = self.LEFT_SIDE_COLOR

        else:

            left_color = self.LEFT_SIDE_COLOR
            right_color = self.RIGHT_SIDE_COLOR



        painter.fillRect(
            geometry["x_offset"],
            geometry["y_offset"],
            half,
            geometry["h"],
            left_color
        )


        painter.fillRect(
            geometry["x_offset"] + half,
            geometry["y_offset"],
            geometry["w"] - half,
            geometry["h"],
            right_color
        )

        # ==========================
        # Affichage dernier tir
        # ==========================

        if self.last_shot is not None:

            shot_x = (
                geometry["x_offset"]
                +
                self.last_shot["x"]
                *
                geometry["w"]
            )


            shot_y = (
                geometry["y_offset"]
                +
                self.last_shot["y"]
                *
                geometry["h"]
            )


            if self.last_shot["missed"]:
                color = QColor(
                    255,
                    0,
                    0
                )
            else:
                color = QColor(
                    0,
                    160,
                    0
                )


            painter.setBrush(
                color
            )

            painter.setPen(
                Qt.PenStyle.NoPen
            )


            painter.drawEllipse(
                QPointF(
                    shot_x,
                    shot_y
                ),
                3,
                3
            )

        # ==========================
        # Zone verte 2 points
        # ==========================

        # params = self.court_parameters()


        # painter.setBrush(
        #     QColor(
        #         0,
        #         255,
        #         0,
        #         70
        #     )
        # )


        # painter.setPen(
        #     QPen(
        #         QColor(0,180,0),
        #         2
        #     )
        # )


        # # rectangles

        # painter.drawRect(
        #     QRectF(
        #         geometry["x_offset"],
        #         geometry["y_offset"]
        #         +
        #         params["paint_y_min"]
        #         *
        #         geometry["h"],

        #         params["paint_x"]
        #         *
        #         geometry["w"],

        #         (
        #             params["paint_y_max"]
        #             -
        #             params["paint_y_min"]
        #         )
        #         *
        #         geometry["h"]
        #     )
        # )


        # painter.drawRect(
        #     QRectF(
        #         geometry["x_offset"]
        #         +
        #         (
        #             1
        #             -
        #             params["paint_x"]
        #         )
        #         *
        #         geometry["w"],

        #         geometry["y_offset"]
        #         +
        #         params["paint_y_min"]
        #         *
        #         geometry["h"],

        #         params["paint_x"]
        #         *
        #         geometry["w"],

        #         (
        #             params["paint_y_max"]
        #             -
        #             params["paint_y_min"]
        #         )
        #         *
        #         geometry["h"]
        #     )
        # )



        # # demi cercles

        # r = geometry["radius"]


        # for bx, by in [
        #     geometry["left_basket"],
        #     geometry["right_basket"]
        # ]:

        #     painter.drawArc(
        #         int(bx-r),
        #         int(by-r),
        #         int(r*2),
        #         int(r*2),
        #         0,
        #         360*16
        #     )


    # =====================================================
    # Affichage dernier tir
    # =====================================================

    def add_shot_point(
        self,
        x: float,
        y: float,
        missed: bool
    ):

        self.last_shot = {
            "x": x,
            "y": y,
            "missed": missed
        }

        self.update()

    # =====================================================
    # Clic
    # =====================================================

    def mousePressEvent(self,event):

        if event.button() != Qt.MouseButton.LeftButton:
            return


        geometry = self.get_geometry()


        x = (
            event.position().x()
            -
            geometry["x_offset"]
        ) / geometry["w"]


        y = (
            event.position().y()
            -
            geometry["y_offset"]
        ) / geometry["h"]


        missed = bool(
            event.modifiers()
            &
            Qt.KeyboardModifier.ShiftModifier
        )

        self.add_shot_point(
            x,
            y,
            missed
        )

        self.shot_clicked.emit(
            x,
            y,
            missed
        )



    # =====================================================
    # Détection EXACTEMENT identique au dessin
    # =====================================================

    def shot_value(self,x,y):

        geometry = self.get_geometry()

        params = self.court_parameters()


        px = (
            geometry["x_offset"]
            +
            x
            *
            geometry["w"]
        )


        py = (
            geometry["y_offset"]
            +
            y
            *
            geometry["h"]
        )



        # rectangles verts

        left_rect = (
            px <= geometry["x_offset"]
            +
            params["paint_x"]
            *
            geometry["w"]

            and

            params["paint_y_min"]
            <= y
            <=
            params["paint_y_max"]
        )


        right_rect = (
            px >= geometry["x_offset"]
            +
            (
                1
                -
                params["paint_x"]
            )
            *
            geometry["w"]

            and

            params["paint_y_min"]
            <= y
            <=
            params["paint_y_max"]
        )


        if left_rect or right_rect:
            return "2PTS"



        # cercles verts

        r = geometry["radius"]


        for bx,by in [
            geometry["left_basket"],
            geometry["right_basket"]
        ]:

            distance = math.sqrt(
                (px-bx)**2
                +
                (py-by)**2
            )


            if distance <= r:

                # moitié intérieure du terrain uniquement
                if (
                    bx < px < geometry["x_offset"]+geometry["w"]/2
                    or
                    geometry["x_offset"]+geometry["w"]/2 < px < bx
                ):
                    return "2PTS"



        return "3PTS"
