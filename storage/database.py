"""SQLite database for simulation runs (SQLAlchemy, PostgreSQL-ready)."""

import json
from datetime import datetime, timezone
from sqlalchemy import (
    create_engine, Column, Integer, String, Float, DateTime, Text, ForeignKey,
)
from sqlalchemy.orm import declarative_base, sessionmaker, Session

from config import DB_PATH

engine = create_engine(f"sqlite:///{DB_PATH}", echo=False)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()


class UserRow(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=True)
    email = Column(String, unique=True, nullable=False)
    name = Column(String)
    avatar_url = Column(String)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class SimulationRunRow(Base):
    __tablename__ = "simulation_runs"

    id = Column(String, primary_key=True)  # UUID
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    status = Column(String, default="running")  # running, completed, failed
    num_simulations = Column(Integer)
    input_params = Column(Text)  # JSON
    results_summary = Column(Text, nullable=True)  # JSON
    trajectory_file = Column(String, nullable=True)  # path to .npz


def init_db():
    Base.metadata.create_all(engine)


def get_session() -> Session:
    return SessionLocal()


def save_run(
    run_id: str,
    num_simulations: int,
    input_params: dict,
    user_id: int | None = None,
) -> SimulationRunRow:
    session = get_session()
    try:
        row = SimulationRunRow(
            id=run_id,
            user_id=user_id,
            num_simulations=num_simulations,
            input_params=json.dumps(input_params),
            status="running",
        )
        session.add(row)
        session.commit()
        session.refresh(row)
        return row
    finally:
        session.close()


def update_run(
    run_id: str,
    status: str,
    results_summary: dict | None = None,
    trajectory_file: str | None = None,
):
    session = get_session()
    try:
        row = session.query(SimulationRunRow).filter_by(id=run_id).first()
        if row:
            row.status = status
            if results_summary:
                row.results_summary = json.dumps(results_summary)
            if trajectory_file:
                row.trajectory_file = trajectory_file
            session.commit()
    finally:
        session.close()


def get_run(run_id: str) -> SimulationRunRow | None:
    session = get_session()
    try:
        return session.query(SimulationRunRow).filter_by(id=run_id).first()
    finally:
        session.close()


def list_runs(user_id: int | None = None, limit: int = 50) -> list[dict]:
    session = get_session()
    try:
        q = session.query(SimulationRunRow).order_by(SimulationRunRow.created_at.desc())
        if user_id is not None:
            q = q.filter_by(user_id=user_id)
        rows = q.limit(limit).all()
        return [
            {
                "id": r.id,
                "created_at": r.created_at.isoformat() if r.created_at else None,
                "status": r.status,
                "num_simulations": r.num_simulations,
                "results_summary": json.loads(r.results_summary) if r.results_summary else None,
                "input_params": json.loads(r.input_params) if r.input_params else None,
            }
            for r in rows
        ]
    finally:
        session.close()


def upsert_user(email: str, name: str | None = None, avatar_url: str | None = None) -> UserRow:
    """Create or update a user by email. Returns the user row."""
    session = get_session()
    try:
        user = session.query(UserRow).filter_by(email=email).first()
        if user:
            if name:
                user.name = name
            if avatar_url:
                user.avatar_url = avatar_url
            session.commit()
            session.refresh(user)
        else:
            user = UserRow(email=email, name=name, avatar_url=avatar_url)
            session.add(user)
            session.commit()
            session.refresh(user)
        return user
    finally:
        session.close()


def get_user_by_email(email: str) -> UserRow | None:
    session = get_session()
    try:
        return session.query(UserRow).filter_by(email=email).first()
    finally:
        session.close()
