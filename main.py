"""Point d'entrée simple du backend Traffic Togo."""

from __future__ import annotations

from app.core.config import ConfigurationApplication


def charger_configuration(
    configuration: ConfigurationApplication | None = None,
) -> ConfigurationApplication:
    """Charge et valide la configuration technique globale de l'application."""
    config_active = (
        configuration if configuration is not None else ConfigurationApplication()
    )
    config_active.valider()
    return config_active


def main() -> None:
    """Exécution directe du point d'entrée backend."""
    configuration = charger_configuration()
    print(
        f"[OK] {configuration.nom_application} démarré "
        f"(env={configuration.environnement.value})"
    )


if __name__ == "__main__":
    main()
