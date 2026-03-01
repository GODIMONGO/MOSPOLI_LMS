import json
import os
import unittest
import uuid
from http import HTTPStatus
from http.cookiejar import CookieJar
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import HTTPCookieProcessor, Request, build_opener

BASE_URL = os.getenv("TEST_BASE_URL", "http://localhost:5000")


def _session():
    return build_opener(HTTPCookieProcessor(CookieJar()))


def _request(opener, path, method="GET", data=None, json_body=False):
    headers = {}
    payload = None
    if data is not None:
        if json_body:
            headers["Content-Type"] = "application/json"
            payload = json.dumps(data).encode("utf-8")
        else:
            headers["Content-Type"] = "application/x-www-form-urlencoded"
            payload = urlencode(data).encode("utf-8")

    request = Request(url=f"{BASE_URL}{path}", method=method, data=payload, headers=headers)
    return opener.open(request, timeout=10)


def _login(opener, username, password):
    return _request(
        opener,
        "/login",
        method="POST",
        data={"username": username, "password": password},
        json_body=False,
    )


class LMSEdgeCasesTestCase(unittest.TestCase):
    def test_duplicate_course_code_conflict(self):
        admin = _session()
        self.assertEqual(_login(admin, "admin", "admin").status, HTTPStatus.OK)

        code = f"dup-{uuid.uuid4().hex[:8]}"
        first = _request(
            admin,
            "/api/lms/courses",
            method="POST",
            data={"course_code": code, "title": "First"},
            json_body=True,
        )
        self.assertEqual(first.status, HTTPStatus.CREATED)

        with self.assertRaises(HTTPError) as exc:
            _request(
                admin,
                "/api/lms/courses",
                method="POST",
                data={"course_code": code, "title": "Second"},
                json_body=True,
            )
        self.assertEqual(exc.exception.code, HTTPStatus.CONFLICT)

    def test_student_cannot_create_course(self):
        student = _session()
        self.assertEqual(_login(student, "student", "123").status, HTTPStatus.OK)
        with self.assertRaises(HTTPError) as exc:
            _request(
                student,
                "/api/lms/courses",
                method="POST",
                data={"course_code": f"st-{uuid.uuid4().hex[:8]}", "title": "Nope"},
                json_body=True,
            )
        self.assertEqual(exc.exception.code, HTTPStatus.FORBIDDEN)

    def test_invalid_test_status_and_invalid_base64(self):
        admin = _session()
        student = _session()
        self.assertEqual(_login(admin, "admin", "admin").status, HTTPStatus.OK)
        self.assertEqual(_login(student, "student", "123").status, HTTPStatus.OK)

        course_code = f"edge-{uuid.uuid4().hex[:8]}"
        course_resp = _request(
            admin,
            "/api/lms/courses",
            method="POST",
            data={"course_code": course_code, "title": "Edge"},
            json_body=True,
        )
        course_id = json.loads(course_resp.read().decode("utf-8"))["course"]["id"]

        test_item_resp = _request(
            admin,
            f"/api/lms/courses/{course_id}/items",
            method="POST",
            data={"item_type": "test", "title": "T1"},
            json_body=True,
        )
        test_item_id = json.loads(test_item_resp.read().decode("utf-8"))["item"]["id"]

        lab_item_resp = _request(
            admin,
            f"/api/lms/courses/{course_id}/items",
            method="POST",
            data={"item_type": "lab", "title": "L1"},
            json_body=True,
        )
        lab_item_id = json.loads(lab_item_resp.read().decode("utf-8"))["item"]["id"]

        assign_resp = _request(
            admin,
            f"/api/lms/courses/{course_id}/assign",
            method="POST",
            data={"student_username": "student"},
            json_body=True,
        )
        course_instance_id = json.loads(assign_resp.read().decode("utf-8"))["student_course"]["course_instance_id"]

        with self.assertRaises(HTTPError) as invalid_status_exc:
            _request(
                student,
                f"/api/lms/student-courses/{course_instance_id}/tests/{test_item_id}/result",
                method="POST",
                data={"status": "wrong_status", "score": 10},
                json_body=True,
            )
        self.assertEqual(invalid_status_exc.exception.code, HTTPStatus.BAD_REQUEST)

        with self.assertRaises(HTTPError) as invalid_base64_exc:
            _request(
                student,
                f"/api/lms/student-courses/{course_instance_id}/items/{lab_item_id}/submissions",
                method="POST",
                data={
                    "file_name": "bad.bin",
                    "file_content_base64": "###not-base64###",
                },
                json_body=True,
            )
        self.assertEqual(invalid_base64_exc.exception.code, HTTPStatus.BAD_REQUEST)

    def test_student_course_unique_id_persists_until_admin_delete(self):
        admin = _session()
        student = _session()
        self.assertEqual(_login(admin, "admin", "admin").status, HTTPStatus.OK)
        self.assertEqual(_login(student, "student", "123").status, HTTPStatus.OK)

        course_code = f"own-{uuid.uuid4().hex[:8]}"
        course_resp = _request(
            admin,
            "/api/lms/courses",
            method="POST",
            data={"course_code": course_code, "title": "Owned Course"},
            json_body=True,
        )
        course_id = json.loads(course_resp.read().decode("utf-8"))["course"]["id"]

        assign_resp = _request(
            admin,
            f"/api/lms/courses/{course_id}/assign",
            method="POST",
            data={"student_username": "student"},
            json_body=True,
        )
        assigned = json.loads(assign_resp.read().decode("utf-8"))["student_course"]
        first_student_course_id = assigned["student_course_id"]
        first_course_instance_id = assigned["course_instance_id"]

        student_courses = _request(student, "/api/lms/student-courses")
        student_courses_payload = json.loads(student_courses.read().decode("utf-8"))["student_courses"]
        own_course_row = next(row for row in student_courses_payload if row["course_instance_id"] == first_course_instance_id)
        self.assertEqual(own_course_row["student_course_id"], first_student_course_id)

        admin_by_id = _request(admin, f"/api/lms/student-courses/by-id/{first_student_course_id}")
        self.assertEqual(admin_by_id.status, HTTPStatus.OK)
        admin_by_id_payload = json.loads(admin_by_id.read().decode("utf-8"))["student_course"]
        self.assertEqual(admin_by_id_payload["student_course_id"], first_student_course_id)
        self.assertEqual(admin_by_id_payload["course_instance_id"], first_course_instance_id)

        delete_resp = _request(admin, f"/api/lms/student-courses/by-id/{first_student_course_id}", method="DELETE")
        self.assertEqual(delete_resp.status, HTTPStatus.OK)

        with self.assertRaises(HTTPError) as missing_after_delete:
            _request(student, f"/api/lms/student-courses/{first_course_instance_id}")
        self.assertEqual(missing_after_delete.exception.code, HTTPStatus.NOT_FOUND)

        reassign_resp = _request(
            admin,
            f"/api/lms/courses/{course_id}/assign",
            method="POST",
            data={"student_username": "student"},
            json_body=True,
        )
        self.assertEqual(reassign_resp.status, HTTPStatus.CREATED)
        reassigned = json.loads(reassign_resp.read().decode("utf-8"))["student_course"]
        self.assertNotEqual(reassigned["student_course_id"], first_student_course_id)
        self.assertNotEqual(reassigned["course_instance_id"], first_course_instance_id)


if __name__ == "__main__":
    unittest.main(verbosity=2)
