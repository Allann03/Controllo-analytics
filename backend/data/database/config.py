import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

# ── Database URL ─────────────────────────────────────────────────────
# Em produção: DATABASE_URL=postgresql://user:pass@host:5432/dbname
# Em desenvolvimento: cai no fallback SQLite
DATABASE_URL = os.environ.get("DATABASE_URL", "")

if DATABASE_URL:
    # PostgreSQL (produção)
    engine = create_engine(
        DATABASE_URL,
        pool_size=20,
        max_overflow=30,
        pool_pre_ping=True,
        pool_recycle=300,
    )
else:
    # SQLite (desenvolvimento local)
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    DATA_DIR = os.path.join(BASE_DIR, "data")
    os.makedirs(DATA_DIR, exist_ok=True)
    SQLALCHEMY_DATABASE_URL = f"sqlite:///{os.path.join(DATA_DIR, 'controllo.db')}"
    engine = create_engine(
        SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# Dependência que vamos injetar nas rotas
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
