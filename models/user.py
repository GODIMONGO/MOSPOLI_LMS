from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from db import Base

if TYPE_CHECKING:
    from models.lms import AssignmentSubmission, Course, StudentCourse


class UserRole(str, Enum):
    ADMIN = "admin"
    STUDENT = "student"


class User(Base):
    __tablename__ = "users"
    __table_args__ = (CheckConstraint("role in ('admin', 'student')", name="ck_users_role"),)

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(32), nullable=False, default=UserRole.STUDENT.value)
    created_courses: Mapped[list["Course"]] = relationship(
        "Course",
        back_populates="created_by",
        foreign_keys="Course.created_by_user_id",
    )
    student_courses: Mapped[list["StudentCourse"]] = relationship(
        "StudentCourse",
        back_populates="student",
        foreign_keys="StudentCourse.student_id",
    )
    assigned_student_courses: Mapped[list["StudentCourse"]] = relationship(
        "StudentCourse",
        back_populates="assigned_by",
        foreign_keys="StudentCourse.assigned_by_user_id",
    )
    assignment_submissions: Mapped[list["AssignmentSubmission"]] = relationship(
        "AssignmentSubmission",
        back_populates="submitted_by",
        foreign_keys="AssignmentSubmission.submitted_by_user_id",
    )

    def is_admin(self) -> bool:
        return self.role == UserRole.ADMIN.value
