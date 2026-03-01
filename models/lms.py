from __future__ import annotations

from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING
from uuid import uuid4

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, LargeBinary, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db import Base

if TYPE_CHECKING:
    from models.user import User


def _utcnow() -> datetime:
    return datetime.utcnow()


class CourseItemType(str, Enum):
    TEST = "test"
    LECTURE = "lecture"
    LAB = "lab"


class CourseStatus(str, Enum):
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"


class TestStatus(str, Enum):
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"


class Course(Base):
    __tablename__ = "courses"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    course_code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text(), nullable=True)
    created_by_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(), nullable=False, default=_utcnow)
    created_by: Mapped["User"] = relationship("User", back_populates="created_courses", foreign_keys=[created_by_user_id])
    items: Mapped[list["CourseItem"]] = relationship("CourseItem", back_populates="course", cascade="all, delete-orphan")
    student_courses: Mapped[list["StudentCourse"]] = relationship(
        "StudentCourse",
        back_populates="course",
        cascade="all, delete-orphan",
    )


class CourseItem(Base):
    __tablename__ = "course_items"
    __table_args__ = (
        CheckConstraint("item_type in ('test', 'lecture', 'lab')", name="ck_course_items_item_type"),
        Index("ix_course_items_course_id_item_type", "course_id", "item_type"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id"), nullable=False, index=True)
    item_type: Mapped[str] = mapped_column(String(16), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text(), nullable=True)
    max_score: Mapped[int | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(), nullable=False, default=_utcnow)
    course: Mapped["Course"] = relationship("Course", back_populates="items")
    test_results: Mapped[list["TestResult"]] = relationship(
        "TestResult",
        back_populates="course_item",
        cascade="all, delete-orphan",
    )
    submissions: Mapped[list["AssignmentSubmission"]] = relationship(
        "AssignmentSubmission",
        back_populates="course_item",
        cascade="all, delete-orphan",
    )


class StudentCourse(Base):
    __tablename__ = "student_courses"
    __table_args__ = (
        UniqueConstraint("course_id", "student_id", name="uq_student_course_single_assignment"),
        CheckConstraint("status in ('assigned', 'in_progress', 'completed')", name="ck_student_courses_status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    course_instance_id: Mapped[str] = mapped_column(
        String(36),
        nullable=False,
        unique=True,
        index=True,
        default=lambda: str(uuid4()),
    )
    course_id: Mapped[int] = mapped_column(ForeignKey("courses.id"), nullable=False, index=True)
    student_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    assigned_by_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default=CourseStatus.ASSIGNED.value, index=True)
    assigned_at: Mapped[datetime] = mapped_column(DateTime(), nullable=False, default=_utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(), nullable=True)
    course: Mapped["Course"] = relationship("Course", back_populates="student_courses")
    student: Mapped["User"] = relationship("User", back_populates="student_courses", foreign_keys=[student_id])
    assigned_by: Mapped["User"] = relationship(
        "User",
        back_populates="assigned_student_courses",
        foreign_keys=[assigned_by_user_id],
    )
    test_results: Mapped[list["TestResult"]] = relationship(
        "TestResult",
        back_populates="student_course",
        cascade="all, delete-orphan",
    )
    submissions: Mapped[list["AssignmentSubmission"]] = relationship(
        "AssignmentSubmission",
        back_populates="student_course",
        cascade="all, delete-orphan",
    )


class TestResult(Base):
    __tablename__ = "test_results"
    __table_args__ = (
        UniqueConstraint("student_course_id", "course_item_id", name="uq_test_result_student_course_item"),
        CheckConstraint("status in ('not_started', 'in_progress', 'completed')", name="ck_test_results_status"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    student_course_id: Mapped[int] = mapped_column(ForeignKey("student_courses.id"), nullable=False, index=True)
    course_item_id: Mapped[int] = mapped_column(ForeignKey("course_items.id"), nullable=False, index=True)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default=TestStatus.NOT_STARTED.value)
    score: Mapped[float | None] = mapped_column(nullable=True)
    answers_json: Mapped[str | None] = mapped_column(Text(), nullable=True)
    result_text: Mapped[str | None] = mapped_column(Text(), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(), nullable=False, default=_utcnow, onupdate=_utcnow)
    student_course: Mapped["StudentCourse"] = relationship("StudentCourse", back_populates="test_results")
    course_item: Mapped["CourseItem"] = relationship("CourseItem", back_populates="test_results")


class AssignmentSubmission(Base):
    __tablename__ = "assignment_submissions"
    __table_args__ = (Index("ix_assignment_submissions_student_course_item", "student_course_id", "course_item_id"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    student_course_id: Mapped[int] = mapped_column(ForeignKey("student_courses.id"), nullable=False, index=True)
    course_item_id: Mapped[int] = mapped_column(ForeignKey("course_items.id"), nullable=False, index=True)
    submitted_by_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    mime_type: Mapped[str | None] = mapped_column(String(128), nullable=True)
    file_data: Mapped[bytes] = mapped_column(LargeBinary(), nullable=False)
    note: Mapped[str | None] = mapped_column(Text(), nullable=True)
    submitted_at: Mapped[datetime] = mapped_column(DateTime(), nullable=False, default=_utcnow)
    student_course: Mapped["StudentCourse"] = relationship("StudentCourse", back_populates="submissions")
    course_item: Mapped["CourseItem"] = relationship("CourseItem", back_populates="submissions")
    submitted_by: Mapped["User"] = relationship(
        "User",
        back_populates="assignment_submissions",
        foreign_keys=[submitted_by_user_id],
    )
