"""Exceptions métier effectivement utilisées par le domaine intersection."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.intersection.services.intersection_validator import (
        AnomalieValidationIntersection,
    )


class ErreurValidationIntersection(Exception):
    """Levée lorsqu'une intersection présente une ou plusieurs erreurs de validation métier."""

    def __init__(
        self,
        message: str,
        anomalies: tuple[AnomalieValidationIntersection, ...] = (),
    ) -> None:
        super().__init__(message)
        self.anomalies = anomalies
