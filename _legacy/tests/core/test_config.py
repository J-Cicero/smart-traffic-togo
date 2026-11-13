"""Tests unitaires de la configuration technique globale (app.core.config) et du point d'entrée."""

from __future__ import annotations

import pytest

from app.core.config import (
    ConfigurationApplication,
    Environnement,
    ErreurConfiguration,
)
from main import charger_configuration


def test_configuration_par_defaut_est_valide() -> None:
    configuration = ConfigurationApplication()
    configuration.valider()

    assert configuration.nom_application == "Traffic Togo Backend"
    assert configuration.environnement == Environnement.DEVELOPPEMENT
    assert configuration.mode_debug is False


def test_configuration_rejette_nom_application_vide() -> None:
    configuration_invalide = ConfigurationApplication(nom_application="   ")
    with pytest.raises(ErreurConfiguration) as exc_info:
        configuration_invalide.valider()

    assert "nom_application" in str(exc_info.value)


def test_charger_configuration_retourne_configuration_validee() -> None:
    configuration = charger_configuration()
    assert isinstance(configuration, ConfigurationApplication)
    assert configuration.nom_application == "Traffic Togo Backend"
