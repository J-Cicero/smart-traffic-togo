"""Exceptions métier pour le domaine intersection."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.intersection.validator import AnomalieValidationIntersection


class ErreurIntersectionBase(Exception):
    """Exception racine pour toutes les erreurs du domaine intersection."""


class ErreurValidationIntersection(ErreurIntersectionBase):
    """Levée lorsqu'une intersection présente une ou plusieurs anomalies bloquantes."""

    def __init__(
        self,
        message: str,
        anomalies: tuple[AnomalieValidationIntersection, ...] = (),
    ) -> None:
        super().__init__(message)
        self.anomalies = anomalies


class ErreurChargementCarrefour(ErreurIntersectionBase):
    """Levée en cas d'erreur de lecture, parsing ou structure d'un fichier de carrefour."""
