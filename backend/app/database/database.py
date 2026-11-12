from sqlalchemy import create_engine
from sqlalchemy.orm import (
    declarative_base,
    sessionmaker,
)

from app.core import settings


DATABASE_URL = settings.DATABASE_URL

if not DATABASE_URL:
    raise ValueError(
        "DATABASE_URL is not set in configuration"
    )


engine_kwargs = {}
if DATABASE_URL.startswith("sqlite"):
    engine_kwargs["connect_args"] = {"check_same_thread": False}
else:
    engine_kwargs.update(
        {
            "pool_pre_ping": True,
            "pool_recycle": getattr(settings, "DB_POOL_RECYCLE", 1800),
            "pool_size": getattr(settings, "DB_POOL_SIZE", 5),
            "max_overflow": getattr(settings, "DB_MAX_OVERFLOW", 5),
            "pool_timeout": getattr(settings, "DB_POOL_TIMEOUT", 30),
        }
    )

engine = create_engine(
    DATABASE_URL,
    **engine_kwargs,
)


SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)


Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
