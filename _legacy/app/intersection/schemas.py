"""
Schémas Pydantic (DTOs) pour l'API publique du module Intersection.

Règle absolue :
- Aucun identifiant technique `id` n'est exposé ou accepté en entrée/sortie.
- Seul `tracking_id` (UUID) est utilisé pour identifier les ressources.
"""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.intersection.entities import DirectionVoie


# ---------------------------------------------------------------------------
# Schémas Intersection
# ---------------------------------------------------------------------------


class IntersectionCreate(BaseModel):
    """Données requises pour créer une intersection."""

    nom: str = Field(..., min_length=1, max_length=255, description="Nom du carrefour")
    description: str = Field(
        default="", max_length=1000, description="Description contextuelle"
    )

    model_config = ConfigDict(extra="forbid")


class IntersectionUpdate(BaseModel):
    """Données modifiables d'une intersection."""

    nom: str | None = Field(
        default=None, min_length=1, max_length=255, description="Nouveau nom"
    )
    description: str | None = Field(
        default=None, max_length=1000, description="Nouvelle description"
    )

    model_config = ConfigDict(extra="forbid")


class IntersectionResponse(BaseModel):
    """Représentation publique d'une intersection (sans id technique)."""

    tracking_id: UUID = Field(..., description="Identifiant unique fonctionnel UUID")
    nom: str
    description: str

    model_config = ConfigDict(from_attributes=True, extra="forbid")


# ---------------------------------------------------------------------------
# Schémas Branche
# ---------------------------------------------------------------------------


class BrancheCreate(BaseModel):
    """Données requises pour créer une branche."""

    nom: str = Field(..., min_length=1, max_length=255, description="Nom de la branche")
    intersection_tracking_id: UUID = Field(
        ..., description="UUID tracking_id de l'intersection de rattachement"
    )
    angle_degres: float | None = Field(
        default=None, ge=0.0, le=360.0, description="Angle en degrés (0 à 360)"
    )

    model_config = ConfigDict(extra="forbid")


class BrancheUpdate(BaseModel):
    """Données modifiables d'une branche."""

    nom: str | None = Field(
        default=None, min_length=1, max_length=255, description="Nouveau nom"
    )
    angle_degres: float | None = Field(
        default=None, ge=0.0, le=360.0, description="Nouvel angle"
    )

    model_config = ConfigDict(extra="forbid")


class BrancheResponse(BaseModel):
    """Représentation publique d'une branche (sans id technique)."""

    tracking_id: UUID = Field(..., description="Identifiant unique fonctionnel UUID")
    intersection_tracking_id: UUID = Field(
        ..., description="UUID de l'intersection parente"
    )
    nom: str
    angle_degres: float | None = None

    model_config = ConfigDict(from_attributes=True, extra="forbid")


# ---------------------------------------------------------------------------
# Schémas Voie
# ---------------------------------------------------------------------------


class VoieCreate(BaseModel):
    """Données requises pour créer une voie."""

    nom: str = Field(..., min_length=1, max_length=255, description="Nom de la voie")
    branche_tracking_id: UUID = Field(
        ..., description="UUID tracking_id de la branche de rattachement"
    )
    direction: DirectionVoie = Field(
        default=DirectionVoie.ENTRANTE, description="Sens de circulation"
    )
    position: int = Field(default=1, ge=1, description="Indice de position (>= 1)")

    model_config = ConfigDict(extra="forbid")


class VoieUpdate(BaseModel):
    """Données modifiables d'une voie."""

    nom: str | None = Field(
        default=None, min_length=1, max_length=255, description="Nouveau nom"
    )
    direction: DirectionVoie | None = Field(
        default=None, description="Nouveau sens de circulation"
    )
    position: int | None = Field(
        default=None, ge=1, description="Nouvel indice de position"
    )

    model_config = ConfigDict(extra="forbid")


class VoieResponse(BaseModel):
    """Représentation publique d'une voie (sans id technique)."""

    tracking_id: UUID = Field(..., description="Identifiant unique fonctionnel UUID")
    branche_tracking_id: UUID = Field(
        ..., description="UUID de la branche parente"
    )
    nom: str
    direction: DirectionVoie
    position: int

    model_config = ConfigDict(from_attributes=True, extra="forbid")
