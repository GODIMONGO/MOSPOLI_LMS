from __future__ import annotations

import base64
from datetime import datetime
from uuid import uuid4

from flask import Blueprint, jsonify, request, session
from sqlalchemy import delete, func, select

from auth_helpers import current_user_id, is_admin, require_auth_json
from db import session_scope
from models import (
    AssignmentSubmission,
    Course,
    CourseItem,
    CourseItemType,
    CourseStatus,
    StudentCourse,
    TestResult,
    TestStatus,
    User,
    UserRole,
)

lms_bp = Blueprint("lms", __name__)

MAX_SUBMISSION_SIZE = 20 * 1024 * 1024


def _json_error(message: str, code: int):
    return jsonify({"error": message}), code


def _iso(dt: datetime | None) -> str | None:
    return dt.isoformat() if dt else None


def _find_student_course(db_session, course_instance_id: str) -> StudentCourse | None:
    return db_session.scalar(select(StudentCourse).where(StudentCourse.course_instance_id == course_instance_id))


def _find_student_course_by_id(db_session, student_course_id: int) -> StudentCourse | None:
    return db_session.get(StudentCourse, student_course_id)


def _can_access_student_course(student_course: StudentCourse) -> bool:
    if is_admin():
        return True
    user_id = current_user_id()
    return bool(user_id and user_id == student_course.student_id)


def _build_student_course_detail_payload(db_session, student_course: StudentCourse) -> dict:
    course = db_session.get(Course, student_course.course_id)
    student = db_session.get(User, student_course.student_id)
    items = db_session.scalars(
        select(CourseItem).where(CourseItem.course_id == student_course.course_id).order_by(CourseItem.id.asc())
    ).all()
    test_results = db_session.scalars(
        select(TestResult).where(TestResult.student_course_id == student_course.id)
    ).all()
    submissions = db_session.scalars(
        select(AssignmentSubmission).where(AssignmentSubmission.student_course_id == student_course.id)
    ).all()
    test_map = {row.course_item_id: row for row in test_results}
    submission_counts = {}
    for row in submissions:
        submission_counts[row.course_item_id] = submission_counts.get(row.course_item_id, 0) + 1

    items_payload = []
    for item in items:
        test_result = test_map.get(item.id)
        items_payload.append(
            {
                "id": item.id,
                "item_type": item.item_type,
                "title": item.title,
                "description": item.description,
                "max_score": item.max_score,
                "test_result": None
                if not test_result
                else {
                    "status": test_result.status,
                    "score": test_result.score,
                    "result_text": test_result.result_text,
                    "updated_at": _iso(test_result.updated_at),
                },
                "submission_count": submission_counts.get(item.id, 0),
            }
        )

    return {
        "id": student_course.id,
        "student_course_id": student_course.id,
        "course_instance_id": student_course.course_instance_id,
        "status": student_course.status,
        "assigned_at": _iso(student_course.assigned_at),
        "completed_at": _iso(student_course.completed_at),
        "course": {
            "id": course.id if course else None,
            "course_code": course.course_code if course else None,
            "title": course.title if course else None,
            "description": course.description if course else None,
        },
        "student": {
            "id": student.id if student else None,
            "username": student.username if student else None,
        },
        "items": items_payload,
    }


def _refresh_student_course_status(db_session, student_course: StudentCourse) -> None:
    test_count = db_session.scalar(
        select(func.count()).select_from(CourseItem).where(
            CourseItem.course_id == student_course.course_id,
            CourseItem.item_type == CourseItemType.TEST.value,
        )
    )
    completed_tests = db_session.scalar(
        select(func.count()).select_from(TestResult).where(
            TestResult.student_course_id == student_course.id,
            TestResult.status == TestStatus.COMPLETED.value,
        )
    )
    submission_count = db_session.scalar(
        select(func.count()).select_from(AssignmentSubmission).where(AssignmentSubmission.student_course_id == student_course.id)
    )
    test_count = int(test_count or 0)
    completed_tests = int(completed_tests or 0)
    submission_count = int(submission_count or 0)

    if test_count > 0 and completed_tests >= test_count:
        student_course.status = CourseStatus.COMPLETED.value
        student_course.completed_at = student_course.completed_at or datetime.utcnow()
        return

    if completed_tests > 0 or submission_count > 0:
        student_course.status = CourseStatus.IN_PROGRESS.value
        student_course.completed_at = None
        return

    student_course.status = CourseStatus.ASSIGNED.value
    student_course.completed_at = None


def _delete_student_course_with_dependencies(db_session, student_course: StudentCourse) -> None:
    db_session.execute(
        delete(TestResult).where(TestResult.student_course_id == student_course.id)
    )
    db_session.execute(
        delete(AssignmentSubmission).where(AssignmentSubmission.student_course_id == student_course.id)
    )
    db_session.delete(student_course)


@lms_bp.route("/api/lms/courses", methods=["GET", "POST"])
def courses_collection():
    auth_error = require_auth_json()
    if auth_error:
        return auth_error
    if not is_admin():
        return _json_error("admin role required", 403)

    if request.method == "GET":
        with session_scope() as db_session:
            courses = db_session.scalars(select(Course).order_by(Course.id.asc())).all()
            payload = []
            for course in courses:
                items_count = db_session.scalar(
                    select(func.count()).select_from(CourseItem).where(CourseItem.course_id == course.id)
                )
                assignments_count = db_session.scalar(
                    select(func.count()).select_from(StudentCourse).where(StudentCourse.course_id == course.id)
                )
                payload.append(
                    {
                        "id": course.id,
                        "course_code": course.course_code,
                        "title": course.title,
                        "description": course.description,
                        "created_by_user_id": course.created_by_user_id,
                        "created_at": _iso(course.created_at),
                        "items_count": int(items_count or 0),
                        "assignments_count": int(assignments_count or 0),
                    }
                )
        return jsonify({"courses": payload})

    data = request.get_json(silent=True) or {}
    title = str(data.get("title") or "").strip()
    if not title:
        return _json_error("title is required", 400)
    course_code = str(data.get("course_code") or "").strip() or f"course-{uuid4().hex[:8]}"
    description = str(data.get("description") or "").strip() or None

    with session_scope() as db_session:
        exists = db_session.scalar(select(Course).where(Course.course_code == course_code))
        if exists is not None:
            return _json_error("course_code already exists", 409)
        course = Course(
            course_code=course_code,
            title=title,
            description=description,
            created_by_user_id=int(current_user_id() or 0),
        )
        db_session.add(course)
        db_session.flush()
        payload = {
            "id": course.id,
            "course_code": course.course_code,
            "title": course.title,
            "description": course.description,
        }
    return jsonify({"course": payload}), 201


@lms_bp.route("/api/lms/courses/<int:course_id>/items", methods=["GET", "POST"])
def course_items_collection(course_id: int):
    auth_error = require_auth_json()
    if auth_error:
        return auth_error

    with session_scope() as db_session:
        course = db_session.get(Course, course_id)
        if course is None:
            return _json_error("course not found", 404)

        if request.method == "POST":
            if not is_admin():
                return _json_error("admin role required", 403)
            data = request.get_json(silent=True) or {}
            item_type = str(data.get("item_type") or "").strip().lower()
            if item_type not in {CourseItemType.TEST.value, CourseItemType.LECTURE.value, CourseItemType.LAB.value}:
                return _json_error("item_type must be one of: test, lecture, lab", 400)
            title = str(data.get("title") or "").strip()
            if not title:
                return _json_error("title is required", 400)
            description = str(data.get("description") or "").strip() or None
            max_score_raw = data.get("max_score")
            max_score = None
            if max_score_raw is not None:
                try:
                    max_score = int(max_score_raw)
                except (TypeError, ValueError):
                    return _json_error("max_score must be integer", 400)
            item = CourseItem(
                course_id=course.id,
                item_type=item_type,
                title=title,
                description=description,
                max_score=max_score,
            )
            db_session.add(item)
            db_session.flush()
            return (
                jsonify(
                    {
                        "item": {
                            "id": item.id,
                            "course_id": item.course_id,
                            "item_type": item.item_type,
                            "title": item.title,
                            "description": item.description,
                            "max_score": item.max_score,
                        }
                    }
                ),
                201,
            )

        if not is_admin():
            user_id = int(current_user_id() or 0)
            assignment_exists = db_session.scalar(
                select(StudentCourse.id).where(
                    StudentCourse.course_id == course.id,
                    StudentCourse.student_id == user_id,
                )
            )
            if assignment_exists is None:
                return _json_error("access denied", 403)

        items = db_session.scalars(select(CourseItem).where(CourseItem.course_id == course.id).order_by(CourseItem.id.asc())).all()
        payload = [
            {
                "id": item.id,
                "course_id": item.course_id,
                "item_type": item.item_type,
                "title": item.title,
                "description": item.description,
                "max_score": item.max_score,
                "created_at": _iso(item.created_at),
            }
            for item in items
        ]
        return jsonify({"items": payload})


@lms_bp.route("/api/lms/courses/<int:course_id>/assign", methods=["POST"])
def assign_course_to_student(course_id: int):
    auth_error = require_auth_json()
    if auth_error:
        return auth_error
    if not is_admin():
        return _json_error("admin role required", 403)

    data = request.get_json(silent=True) or {}
    student_id_raw = data.get("student_id")
    student_username = str(data.get("student_username") or "").strip()

    with session_scope() as db_session:
        course = db_session.get(Course, course_id)
        if course is None:
            return _json_error("course not found", 404)

        student = None
        if student_id_raw is not None:
            try:
                student_id = int(student_id_raw)
            except (TypeError, ValueError):
                return _json_error("student_id must be integer", 400)
            student = db_session.get(User, student_id)
        elif student_username:
            student = db_session.scalar(select(User).where(User.username == student_username))
        else:
            return _json_error("student_id or student_username is required", 400)

        if student is None:
            return _json_error("student not found", 404)
        if student.role != UserRole.STUDENT.value:
            return _json_error("user is not a student", 400)
        assignment_exists = db_session.scalar(
            select(StudentCourse.id).where(
                StudentCourse.course_id == course.id,
                StudentCourse.student_id == student.id,
            )
        )
        if assignment_exists is not None:
            return _json_error("course already assigned to this student", 409)

        assignment = StudentCourse(
            course_instance_id=str(uuid4()),
            course_id=course.id,
            student_id=student.id,
            assigned_by_user_id=int(current_user_id() or 0),
            status=CourseStatus.ASSIGNED.value,
        )
        db_session.add(assignment)
        db_session.flush()

        test_items = db_session.scalars(
            select(CourseItem).where(
                CourseItem.course_id == course.id,
                CourseItem.item_type == CourseItemType.TEST.value,
            )
        ).all()
        for test_item in test_items:
            db_session.add(
                TestResult(
                    student_course_id=assignment.id,
                    course_item_id=test_item.id,
                    status=TestStatus.NOT_STARTED.value,
                )
            )
        payload = {
            "id": assignment.id,
            "student_course_id": assignment.id,
            "course_instance_id": assignment.course_instance_id,
            "course_id": assignment.course_id,
            "student_id": assignment.student_id,
            "status": assignment.status,
            "assigned_at": _iso(assignment.assigned_at),
        }
    return jsonify({"student_course": payload}), 201


@lms_bp.route("/api/lms/student-courses", methods=["GET"])
def student_courses_collection():
    auth_error = require_auth_json()
    if auth_error:
        return auth_error

    with session_scope() as db_session:
        query = select(StudentCourse).order_by(StudentCourse.id.asc())
        if is_admin():
            student_id_raw = request.args.get("student_id")
            if student_id_raw:
                try:
                    student_id = int(student_id_raw)
                except ValueError:
                    return _json_error("student_id must be integer", 400)
                query = query.where(StudentCourse.student_id == student_id)
        else:
            query = query.where(StudentCourse.student_id == int(current_user_id() or 0))

        student_courses = db_session.scalars(query).all()
        course_ids = {item.course_id for item in student_courses}
        user_ids = {item.student_id for item in student_courses}
        courses = db_session.scalars(select(Course).where(Course.id.in_(course_ids))).all() if course_ids else []
        users = db_session.scalars(select(User).where(User.id.in_(user_ids))).all() if user_ids else []
        course_map = {c.id: c for c in courses}
        user_map = {u.id: u for u in users}

        payload = []
        for item in student_courses:
            course = course_map.get(item.course_id)
            student = user_map.get(item.student_id)
            payload.append(
                {
                    "id": item.id,
                    "student_course_id": item.id,
                    "course_instance_id": item.course_instance_id,
                    "status": item.status,
                    "assigned_at": _iso(item.assigned_at),
                    "completed_at": _iso(item.completed_at),
                    "course": {
                        "id": item.course_id,
                        "course_code": course.course_code if course else None,
                        "title": course.title if course else None,
                    },
                    "student": {
                        "id": item.student_id,
                        "username": student.username if student else None,
                    },
                }
            )
        return jsonify({"student_courses": payload})


@lms_bp.route("/api/lms/student-courses/<string:course_instance_id>", methods=["GET"])
def student_course_detail(course_instance_id: str):
    auth_error = require_auth_json()
    if auth_error:
        return auth_error

    with session_scope() as db_session:
        student_course = _find_student_course(db_session, course_instance_id)
        if student_course is None:
            return _json_error("student course not found", 404)
        if not _can_access_student_course(student_course):
            return _json_error("access denied", 403)
        payload = _build_student_course_detail_payload(db_session, student_course)
        return jsonify({"student_course": payload})


@lms_bp.route("/api/lms/student-courses/<string:course_instance_id>", methods=["DELETE"])
def student_course_delete(course_instance_id: str):
    auth_error = require_auth_json()
    if auth_error:
        return auth_error
    if not is_admin():
        return _json_error("admin role required", 403)

    with session_scope() as db_session:
        student_course = _find_student_course(db_session, course_instance_id)
        if student_course is None:
            return _json_error("student course not found", 404)
        payload = {
            "id": student_course.id,
            "student_course_id": student_course.id,
            "course_instance_id": student_course.course_instance_id,
            "course_id": student_course.course_id,
            "student_id": student_course.student_id,
        }
        _delete_student_course_with_dependencies(db_session, student_course)
        return jsonify({"deleted_student_course": payload})


@lms_bp.route("/api/lms/student-courses/by-id/<int:student_course_id>", methods=["GET", "DELETE"])
def student_course_by_id(student_course_id: int):
    auth_error = require_auth_json()
    if auth_error:
        return auth_error

    with session_scope() as db_session:
        student_course = _find_student_course_by_id(db_session, student_course_id)
        if student_course is None:
            return _json_error("student course not found", 404)

        if request.method == "GET":
            if not _can_access_student_course(student_course):
                return _json_error("access denied", 403)
            payload = _build_student_course_detail_payload(db_session, student_course)
            return jsonify({"student_course": payload})

        if not is_admin():
            return _json_error("admin role required", 403)
        payload = {
            "id": student_course.id,
            "student_course_id": student_course.id,
            "course_instance_id": student_course.course_instance_id,
            "course_id": student_course.course_id,
            "student_id": student_course.student_id,
        }
        _delete_student_course_with_dependencies(db_session, student_course)
        return jsonify({"deleted_student_course": payload})


@lms_bp.route("/api/lms/student-courses/<string:course_instance_id>/tests/<int:item_id>/result", methods=["POST"])
def submit_test_result(course_instance_id: str, item_id: int):
    auth_error = require_auth_json()
    if auth_error:
        return auth_error

    with session_scope() as db_session:
        student_course = _find_student_course(db_session, course_instance_id)
        if student_course is None:
            return _json_error("student course not found", 404)
        if not _can_access_student_course(student_course):
            return _json_error("access denied", 403)

        course_item = db_session.get(CourseItem, item_id)
        if course_item is None or course_item.course_id != student_course.course_id:
            return _json_error("course item not found", 404)
        if course_item.item_type != CourseItemType.TEST.value:
            return _json_error("course item is not test", 400)

        data = request.get_json(silent=True) or {}
        status = str(data.get("status") or TestStatus.COMPLETED.value).strip().lower()
        if status not in {TestStatus.NOT_STARTED.value, TestStatus.IN_PROGRESS.value, TestStatus.COMPLETED.value}:
            return _json_error("invalid test status", 400)

        score = data.get("score")
        score_value = None
        if score is not None:
            try:
                score_value = float(score)
            except (TypeError, ValueError):
                return _json_error("score must be numeric", 400)

        answers_json_raw = data.get("answers")
        answers_json = None
        if answers_json_raw is not None:
            try:
                import json

                answers_json = json.dumps(answers_json_raw, ensure_ascii=False)
            except TypeError:
                return _json_error("answers must be JSON-serializable", 400)

        result_text = str(data.get("result_text") or "").strip() or None

        test_result = db_session.scalar(
            select(TestResult).where(
                TestResult.student_course_id == student_course.id,
                TestResult.course_item_id == course_item.id,
            )
        )
        if test_result is None:
            test_result = TestResult(
                student_course_id=student_course.id,
                course_item_id=course_item.id,
            )
            db_session.add(test_result)

        test_result.status = status
        test_result.score = score_value
        test_result.answers_json = answers_json
        test_result.result_text = result_text

        _refresh_student_course_status(db_session, student_course)

        payload = {
            "student_course_id": student_course.id,
            "course_item_id": course_item.id,
            "status": test_result.status,
            "score": test_result.score,
            "result_text": test_result.result_text,
            "updated_at": _iso(test_result.updated_at),
            "student_course_status": student_course.status,
        }
        return jsonify({"test_result": payload})


@lms_bp.route("/api/lms/student-courses/<string:course_instance_id>/items/<int:item_id>/submissions", methods=["GET", "POST"])
def submissions_collection(course_instance_id: str, item_id: int):
    auth_error = require_auth_json()
    if auth_error:
        return auth_error

    with session_scope() as db_session:
        student_course = _find_student_course(db_session, course_instance_id)
        if student_course is None:
            return _json_error("student course not found", 404)
        if not _can_access_student_course(student_course):
            return _json_error("access denied", 403)

        course_item = db_session.get(CourseItem, item_id)
        if course_item is None or course_item.course_id != student_course.course_id:
            return _json_error("course item not found", 404)

        if request.method == "POST":
            data = request.get_json(silent=True) or {}
            file_name = str(data.get("file_name") or "").strip()
            if not file_name:
                return _json_error("file_name is required", 400)
            file_content_base64 = str(data.get("file_content_base64") or "").strip()
            if not file_content_base64:
                return _json_error("file_content_base64 is required", 400)
            try:
                file_data = base64.b64decode(file_content_base64, validate=True)
            except Exception:
                return _json_error("file_content_base64 is invalid", 400)
            if len(file_data) > MAX_SUBMISSION_SIZE:
                return _json_error("file is too large", 413)
            mime_type = str(data.get("mime_type") or "").strip() or None
            note = str(data.get("note") or "").strip() or None

            submission = AssignmentSubmission(
                student_course_id=student_course.id,
                course_item_id=course_item.id,
                submitted_by_user_id=int(current_user_id() or 0),
                file_name=file_name,
                mime_type=mime_type,
                file_data=file_data,
                note=note,
            )
            db_session.add(submission)
            db_session.flush()

            _refresh_student_course_status(db_session, student_course)

            return (
                jsonify(
                    {
                        "submission": {
                            "id": submission.id,
                            "student_course_id": submission.student_course_id,
                            "course_item_id": submission.course_item_id,
                            "file_name": submission.file_name,
                            "mime_type": submission.mime_type,
                            "note": submission.note,
                            "submitted_at": _iso(submission.submitted_at),
                            "student_course_status": student_course.status,
                        }
                    }
                ),
                201,
            )

        submissions = db_session.scalars(
            select(AssignmentSubmission).where(
                AssignmentSubmission.student_course_id == student_course.id,
                AssignmentSubmission.course_item_id == course_item.id,
            )
        ).all()
        payload = [
            {
                "id": row.id,
                "file_name": row.file_name,
                "mime_type": row.mime_type,
                "note": row.note,
                "submitted_by_user_id": row.submitted_by_user_id,
                "submitted_at": _iso(row.submitted_at),
                "size_bytes": len(row.file_data),
            }
            for row in submissions
        ]
        return jsonify({"submissions": payload})


@lms_bp.route("/api/lms/submissions/<int:submission_id>/download", methods=["GET"])
def submission_download(submission_id: int):
    auth_error = require_auth_json()
    if auth_error:
        return auth_error

    with session_scope() as db_session:
        submission = db_session.get(AssignmentSubmission, submission_id)
        if submission is None:
            return _json_error("submission not found", 404)
        student_course = db_session.get(StudentCourse, submission.student_course_id)
        if student_course is None:
            return _json_error("student course not found", 404)
        if not _can_access_student_course(student_course):
            return _json_error("access denied", 403)

        payload = {
            "id": submission.id,
            "file_name": submission.file_name,
            "mime_type": submission.mime_type,
            "file_content_base64": base64.b64encode(submission.file_data).decode("ascii"),
            "size_bytes": len(submission.file_data),
            "submitted_at": _iso(submission.submitted_at),
        }
        return jsonify({"submission": payload})
