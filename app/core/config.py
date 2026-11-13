from __future__ import annotations

from typing import Literal
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Configuration globale de l'application."""

    model_config = SettingsConfigDict(
        env_prefix="TRAFFIC_",
        case_sensitive=False,
    )

    nom_application: str = "Traffic Togo"
    environnement: Literal["dev", "test", "prod"] = "dev"

    @field_validator("nom_application")
    @classmethod
    def valider_nom_application(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Le nom de l'application ne peut pas être vide.")
        return v.strip()


def charger_configuration() -> Settings:
    """Charge et retourne la configuration validée."""
    return Settings()
