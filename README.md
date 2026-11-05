# Traffic Togo — Backend

Système intelligent de surveillance, d'analyse et de régulation du trafic routier au Togo.

## Architecture du Socle Backend

Le backend est organisé en **architecture modulithique par domaine métier**, avec séparation interne des responsabilités et indépendance stricte du noyau métier vis-à-vis des frameworks web et de la persistance :

```text
smart-traffic-togo/
├── PROJECT_CONTEXT.md                              # Référence permanente du projet
├── README.md                                       # Documentation du dépôt
├── requirements.txt                                # Dépendances actives (pytest)
├── main.py                                         # Point d'entrée simple de l'application
├── app/
│   ├── __init__.py
│   ├── core/                                       # Configuration technique globale
│   │   ├── __init__.py
│   │   └── config.py                               # AppConfig, Environment, ConfigurationError
│   └── intersection/                               # Domaine métier : Intersection
│       ├── __init__.py
│       ├── exceptions.py                           # IntersectionValidationError
│       ├── models/
│       │   ├── __init__.py
│       │   └── topology.py                         # Modèle métier Intersection
│       └── services/
│           ├── __init__.py
│           └── intersection_validator.py           # Validation évolutive d'une intersection
└── tests/
    ├── __init__.py
    ├── core/
    │   ├── __init__.py
    │   └── test_config.py
    └── intersection/
        ├── __init__.py
        └── test_intersection_validation.py
```

## Exécution des Tests et du Point d'Entrée

```bash
source .venv/bin/activate
pytest -v
python main.py
```
