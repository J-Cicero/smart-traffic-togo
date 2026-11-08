"""Exceptions métier effectivement utilisées par le domaine intersection."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.intersection.validator import (
        AnomalieValidationIntersection,
    )


class ErreurIntersectionBase(Exception):
    """Exception racine pour les erreurs du domaine intersection."""


class ErreurValidationIntersection(ErreurIntersectionBase):
    """Levée lorsqu'une intersection présente une ou plusieurs erreurs de validation métier."""

    def __init__(
        self,
        message: str,
        anomalies: tuple[AnomalieValidationIntersection, ...] = (),
    ) -> None:
        super().__init__(message)
        self.anomalies = anomalies


class EntiteNonTrouveeErreur(ErreurIntersectionBase):
    """Levée lorsqu'une entité recherchée par son tracking_id n'existe pas."""


class ConflitDonneesErreur(ErreurIntersectionBase):
    """Levée en cas de collision d'identifiant tracking_id ou de contrainte d'intégrité."""


class SuppressionImpossibleErreur(ErreurIntersectionBase):
    """Levée lorsqu'une suppression d'entité créerait des références orphelines."""
