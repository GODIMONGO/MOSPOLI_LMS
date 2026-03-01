import os
from contextlib import contextmanager
from typing import Iterator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker


class Base(DeclarativeBase):
    pass


DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg2://mospoli_user:mospoli_password@localhost:5432/mospoli_db",
)

engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, expire_on_commit=False)


def init_database() -> None:
    from models import AssignmentSubmission, Course, CourseItem, StudentCourse, TestResult, User

    # Import models so SQLAlchemy registers tables before create_all.
    _ = (AssignmentSubmission, Course, CourseItem, StudentCourse, TestResult, User)

    with engine.begin() as connection:
        lock_acquired = False
        if connection.dialect.name == "postgresql":
            connection.exec_driver_sql("SELECT pg_advisory_lock(81273911)")
            lock_acquired = True
        try:
            Base.metadata.create_all(bind=connection)
        finally:
            if lock_acquired:
                connection.exec_driver_sql("SELECT pg_advisory_unlock(81273911)")


@contextmanager
def session_scope() -> Iterator[Session]:
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
