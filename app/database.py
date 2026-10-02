"""SQLAlchemy models and database helper functions for FitBuddy."""
import os
from contextlib import contextmanager
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import Column, Float, ForeignKey, Integer, String, Text, create_engine
from sqlalchemy.orm import declarative_base, relationship, sessionmaker

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

# On Vercel serverless, only /tmp is writable; fall back to /tmp/fitbuddy.db
_default_db = (
    "sqlite:////tmp/fitbuddy.db"
    if os.getenv("VERCEL")
    else f"sqlite:///{(BASE_DIR / 'fitbuddy.db').as_posix()}"
)
DATABASE_URL = os.getenv("DATABASE_URL", _default_db)


engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, autoincrement=False)  # user supplies the ID
    name = Column(String(100), nullable=False)
    age = Column(Integer, nullable=False)
    weight = Column(Float, nullable=False)
    goal = Column(String(100), nullable=False)
    intensity = Column(String(20), nullable=False)
    schedule = Column(Integer, default=7)  # days in the plan

    plan = relationship(
        "WorkoutPlan", back_populates="user", uselist=False, cascade="all, delete-orphan"
    )


class WorkoutPlan(Base):
    __tablename__ = "plans"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True)
    original_plan = Column(Text, nullable=False)
    updated_plan = Column(Text, nullable=True)

    user = relationship("User", back_populates="plan")


def init_db() -> None:
    """Create tables if they do not exist."""
    Base.metadata.create_all(bind=engine)


@contextmanager
def session_scope():
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def _user_to_dict(u: User) -> dict:
    return {
        "id": u.id,
        "name": u.name,
        "age": u.age,
        "weight": u.weight,
        "goal": u.goal,
        "intensity": u.intensity,
        "schedule": u.schedule,
    }


def _plan_to_dict(p: WorkoutPlan) -> dict:
    return {
        "id": p.id,
        "user_id": p.user_id,
        "original_plan": p.original_plan,
        "updated_plan": p.updated_plan,
    }


def save_user(user_id: int, name: str, age: int, weight: float, goal: str, intensity: str) -> None:
    """Create the user, or update their details if the ID already exists."""
    with session_scope() as db:
        existing = db.query(User).filter_by(id=user_id).first()
        if existing:
            existing.name = name
            existing.age = age
            existing.weight = weight
            existing.goal = goal
            existing.intensity = intensity
        else:
            db.add(
                User(
                    id=user_id,
                    name=name,
                    age=age,
                    weight=weight,
                    goal=goal,
                    intensity=intensity,
                    schedule=7,
                )
            )


def save_plan(user_id: int, plan: str) -> None:
    """Store a freshly generated plan. Regenerating replaces the old plan and clears any update."""
    with session_scope() as db:
        existing = db.query(WorkoutPlan).filter_by(user_id=user_id).first()
        if existing:
            existing.original_plan = plan
            existing.updated_plan = None
        else:
            db.add(WorkoutPlan(user_id=user_id, original_plan=plan))


def update_plan(user_id: int, updated: str) -> bool:
    """Store the feedback-based plan next to the original. Returns False if no plan exists."""
    with session_scope() as db:
        row = db.query(WorkoutPlan).filter_by(user_id=user_id).first()
        if not row:
            return False
        row.updated_plan = updated
        return True


def get_original_plan(user_id: int):
    with session_scope() as db:
        row = db.query(WorkoutPlan).filter_by(user_id=user_id).first()
        return row.original_plan if row else None


def get_plan(user_id: int):
    """Return {'original_plan', 'updated_plan', ...} or None."""
    with session_scope() as db:
        row = db.query(WorkoutPlan).filter_by(user_id=user_id).first()
        return _plan_to_dict(row) if row else None


def get_user(user_id: int):
    with session_scope() as db:
        u = db.query(User).filter_by(id=user_id).first()
        return _user_to_dict(u) if u else None


def get_all_users() -> list:
    with session_scope() as db:
        return [_user_to_dict(u) for u in db.query(User).order_by(User.id).all()]


def get_all_plans() -> list:
    with session_scope() as db:
        return [_plan_to_dict(p) for p in db.query(WorkoutPlan).all()]


def delete_user(user_id: int) -> bool:
    """Delete a user and their plan (admin action)."""
    with session_scope() as db:
        u = db.query(User).filter_by(id=user_id).first()
        if not u:
            return False
        db.delete(u)
        return True
