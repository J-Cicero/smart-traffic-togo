"""
Modèles de persistance SQLAlchemy du module Intersection.

Règles architecturales :
- Double identification : `id` (clé primaire technique BDD) et `tracking_id` (UUID unique fonctionnel).
- Absence absolue de relations ORM imbriquées (`relationship()`, `OneToMany`, `ManyToMany`).
- Indépendance totale des tables avec associations par clés et identifiants explicites.
- Séparation stricte avec les entités métier pures définies dans entities.py.
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.intersection.entities import (
    Branche,
    DirectionVoie,
    Intersection,
    Voie,
)


class IntersectionModel(Base):
    """Table de persistance pour l'entité Intersection."""

    __tablename__ = "intersections"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tracking_id: Mapped[UUID] = mapped_column(
        String(36),
        unique=True,
        nullable=False,
        index=True,
    )
    nom: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False, default="")
    date_creation: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    date_modification: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        onupdate=func.now(),
        nullable=True,
    )

    def to_domain(self) -> Intersection:
        """Convertit le modèle de persistance en entité métier pure."""
        tid = self.tracking_id if isinstance(self.tracking_id, UUID) else UUID(str(self.tracking_id))
        return Intersection(
            nom=self.nom,
            description=self.description,
            id=self.id,
            tracking_id=tid,
        )

    @classmethod
    def from_domain(cls, domain: Intersection) -> IntersectionModel:
        """Instancie un modèle de persistance à partir de l'entité métier."""
        return cls(
            id=domain.id,
            tracking_id=str(domain.tracking_id),
            nom=domain.nom,
            description=domain.description or "",
        )


class BrancheModel(Base):
    """Table de persistance pour l'entité Branche."""

    __tablename__ = "branches"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tracking_id: Mapped[UUID] = mapped_column(
        String(36),
        unique=True,
        nullable=False,
        index=True,
    )
    intersection_tracking_id: Mapped[UUID] = mapped_column(
        String(36),
        nullable=False,
        index=True,
    )
    intersection_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("intersections.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    nom: Mapped[str] = mapped_column(String(255), nullable=False)
    angle_degres: Mapped[float | None] = mapped_column(Float, nullable=True)
    date_creation: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    __table_args__ = (
        Index("idx_branches_intersection_tracking_id", "intersection_tracking_id"),
    )

    def to_domain(self) -> Branche:
        """Convertit le modèle de persistance en entité métier pure."""
        tid = self.tracking_id if isinstance(self.tracking_id, UUID) else UUID(str(self.tracking_id))
        itid = (
            self.intersection_tracking_id
            if isinstance(self.intersection_tracking_id, UUID)
            else UUID(str(self.intersection_tracking_id))
        )
        return Branche(
            nom=self.nom,
            intersection_tracking_id=itid,
            intersection_id=self.intersection_id,
            angle_degres=self.angle_degres,
            id=self.id,
            tracking_id=tid,
        )

    @classmethod
    def from_domain(
        cls, domain: Branche, intersection_id: int | None = None
    ) -> BrancheModel:
        """Instancie un modèle de persistance à partir de l'entité métier."""
        return cls(
            id=domain.id,
            tracking_id=str(domain.tracking_id),
            intersection_tracking_id=str(domain.intersection_tracking_id),
            intersection_id=intersection_id or domain.intersection_id,
            nom=domain.nom,
            angle_degres=domain.angle_degres,
        )


class VoieModel(Base):
    """Table de persistance pour l'entité Voie."""

    __tablename__ = "voies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tracking_id: Mapped[UUID] = mapped_column(
        String(36),
        unique=True,
        nullable=False,
        index=True,
    )
    branche_tracking_id: Mapped[UUID] = mapped_column(
        String(36),
        nullable=False,
        index=True,
    )
    branche_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("branches.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    nom: Mapped[str] = mapped_column(String(255), nullable=False)
    direction: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    date_creation: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    __table_args__ = (
        UniqueConstraint(
            "branche_tracking_id",
            "direction",
            "position",
            name="uq_voies_branche_direction_position",
        ),
        CheckConstraint("position >= 1", name="ck_voies_position_positive"),
        Index("idx_voies_branche_tracking_id", "branche_tracking_id"),
        Index("idx_voies_direction", "direction"),
    )

    def to_domain(self) -> Voie:
        """Convertit le modèle de persistance en entité métier pure."""
        tid = self.tracking_id if isinstance(self.tracking_id, UUID) else UUID(str(self.tracking_id))
        btid = (
            self.branche_tracking_id
            if isinstance(self.branche_tracking_id, UUID)
            else UUID(str(self.branche_tracking_id))
        )
        return Voie(
            nom=self.nom,
            branche_tracking_id=btid,
            branche_id=self.branche_id,
            direction=DirectionVoie(self.direction),
            position=self.position,
            id=self.id,
            tracking_id=tid,
        )

    @classmethod
    def from_domain(
        cls, domain: Voie, branche_id: int | None = None
    ) -> VoieModel:
        """Instancie un modèle de persistance à partir de l'entité métier."""
        return cls(
            id=domain.id,
            tracking_id=str(domain.tracking_id),
            branche_tracking_id=str(domain.branche_tracking_id),
            branche_id=branche_id or domain.branche_id,
            nom=domain.nom,
            direction=domain.direction.value,
            position=domain.position,
        )
