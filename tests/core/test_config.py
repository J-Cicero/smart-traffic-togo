from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.core.config import Settings, charger_configuration


def test_configuration_par_defaut_valide() -> None:
    settings = charger_configuration()
    assert settings.nom_application == "Traffic Togo"
    assert settings.environnement == "dev"


def test_nom_application_vide_rejete() -> None:
    with pytest.raises(ValidationError) as exc_info:
        Settings(nom_application="")
    assert "nom_application" in str(exc_info.value)

    with pytest.raises(ValidationError) as exc_info_whitespace:
        Settings(nom_application="   ")
    assert "nom_application" in str(exc_info_whitespace.value)


def test_environnement_inconnu_rejete() -> None:
    with pytest.raises(ValidationError) as exc_info:
        Settings(environnement="inconnu")  # type: ignore[arg-type]
    assert "environnement" in str(exc_info.value)


def test_traffic_environnement_lu_depuis_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("TRAFFIC_ENVIRONNEMENT", "test")
    settings = charger_configuration()
    assert settings.environnement == "test"
