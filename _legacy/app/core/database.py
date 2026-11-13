"""Gestionnaire central de la persistance SQLAlchemy et des sessions de base de données."""

from __future__ import annotations

from collections.abc import Generator
from contextlib import contextmanager

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.core.config import ConfigurationApplication


class Base(DeclarativeBase):
    """Classe de base déclarative pour tous les modèles de persistance ORM."""

    pass


_configuration = ConfigurationApplication()
_moteur: Engine | None = None
_fabrique_sessions: sessionmaker[Session] | None = None


def obtenir_moteur(database_url: str | None = None) -> Engine:
    """Retourne ou initialise le moteur SQLAlchemy (singleton par défaut)."""
    global _moteur
    url = database_url or _configuration.database_url
    if _moteur is None or database_url is not None:
        args_connexion = {}
        if url.startswith("sqlite"):
            args_connexion["check_same_thread"] = False
        moteur = create_engine(url, connect_args=args_connexion, pool_pre_ping=True)
        if database_url is None:
            _moteur = moteur
        return moteur
    return _moteur


def obtenir_fabrique_sessions(
    database_url: str | None = None,
) -> sessionmaker[Session]:
    """Retourne ou initialise la fabrique de sessions SQLAlchemy."""
    global _fabrique_sessions
    if _fabrique_sessions is None or database_url is not None:
        moteur = obtenir_moteur(database_url)
        fabrique = sessionmaker(autocommit=False, autoflush=False, bind=moteur)
        if database_url is None:
            _fabrique_sessions = fabrique
        return fabrique
    return _fabrique_sessions


@contextmanager
def session_scope(
    database_url: str | None = None,
) -> Generator[Session, None, None]:
    """Gestionnaire de contexte fournissant une session transactionnelle avec commit et rollback."""
    fabrique = obtenir_fabrique_sessions(database_url)
    session: Session = fabrique()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_db() -> Generator[Session, None, None]:
    """Dépendance FastAPI fournissant une session de base de données."""
    fabrique = obtenir_fabrique_sessions()
    session: Session = fabrique()
    try:
        yield session
    finally:
        session.close()
