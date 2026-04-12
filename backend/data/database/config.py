import os
import time
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, declarative_base

DATABASE_URL = os.environ.get("DATABASE_URL", "")

if DATABASE_URL:
    engine = None
    for attempt in range(10):
        try:
            engine = create_engine(
                DATABASE_URL,
                pool_size=20,
                max_overflow=30,
                pool_pre_ping=True,
                pool_recycle=300,
            )
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            print(f"[CONTROLLO] PostgreSQL conectado (tentativa {attempt+1})")
            break
        except Exception as e:
            print(f"[CONTROLLO] DB tentativa {attempt+1}/10 falhou: {e}")
            time.sleep(3)
            engine = None
    if engine is None:
        raise RuntimeError("Nao foi possivel conectar ao PostgreSQL apos 10 tentativas")
else:
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    DATA_DIR = os.path.join(BASE_DIR, "data")
    os.makedirs(DATA_DIR, exist_ok=True)
    SQLALCHEMY_DATABASE_URL = f"sqlite:///{os.path.join(DATA_DIR, 'controllo.db')}"
    engine = create_engine(
        SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
