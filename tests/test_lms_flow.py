import base64
import json
import os
import uuid
import unittest
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


class LMSFlowTestCase(unittest.TestCase):
    def test_lms_admin_student_flow(self):
        admin = _session()
        student = _session()

        self.assertEqual(_login(admin, "admin", "admin").status, HTTPStatus.OK)
        self.assertEqual(_login(student, "student", "123").status, HTTPStatus.OK)

        course_code = f"qa-{uuid.uuid4().hex[:10]}"
        create_course = _request(
            admin,
            "/api/lms/courses",
            method="POST",
            data={"course_code": course_code, "title": "QA Course", "description": "integration"},
            json_body=True,
        )
        self.assertEqual(create_course.status, HTTPStatus.CREATED)
        course_payload = json.loads(create_course.read().decode("utf-8"))
        course_id = course_payload["course"]["id"]

        with self.assertRaises(HTTPError) as student_courses_err:
            _request(student, "/api/lms/courses")
        self.assertEqual(student_courses_err.exception.code, HTTPStatus.FORBIDDEN)

        add_test = _request(
            admin,
            f"/api/lms/courses/{course_id}/items",
            method="POST",
            data={"item_type": "test", "title": "Final Test", "max_score": 100},
            json_body=True,
        )
        self.assertEqual(add_test.status, HTTPStatus.CREATED)
        test_item_id = json.loads(add_test.read().decode("utf-8"))["item"]["id"]

        add_lab = _request(
            admin,
            f"/api/lms/courses/{course_id}/items",
            method="POST",
            data={"item_type": "lab", "title": "Lab #1"},
            json_body=True,
        )
        self.assertEqual(add_lab.status, HTTPStatus.CREATED)
        lab_item_id = json.loads(add_lab.read().decode("utf-8"))["item"]["id"]

        assign = _request(
            admin,
            f"/api/lms/courses/{course_id}/assign",
            method="POST",
            data={"student_username": "student"},
            json_body=True,
        )
        self.assertEqual(assign.status, HTTPStatus.CREATED)
        assigned = json.loads(assign.read().decode("utf-8"))["student_course"]
        course_instance_id = assigned["course_instance_id"]

        student_courses = _request(student, "/api/lms/student-courses")
        self.assertEqual(student_courses.status, HTTPStatus.OK)
        student_courses_payload = json.loads(student_courses.read().decode("utf-8"))["student_courses"]
        self.assertTrue(any(row["course_instance_id"] == course_instance_id for row in student_courses_payload))

        student_detail = _request(student, f"/api/lms/student-courses/{course_instance_id}")
        self.assertEqual(student_detail.status, HTTPStatus.OK)

        submit_test = _request(
            student,
            f"/api/lms/student-courses/{course_instance_id}/tests/{test_item_id}/result",
            method="POST",
            data={"status": "completed", "score": 88.5, "answers": {"q1": "a"}, "result_text": "ok"},
            json_body=True,
        )
        self.assertEqual(submit_test.status, HTTPStatus.OK)

        file_bytes = b"hello-lab"
        submit_file = _request(
            student,
            f"/api/lms/student-courses/{course_instance_id}/items/{lab_item_id}/submissions",
            method="POST",
            data={
                "file_name": "lab1.txt",
                "mime_type": "text/plain",
                "file_content_base64": base64.b64encode(file_bytes).decode("ascii"),
                "note": "done",
            },
            json_body=True,
        )
        self.assertEqual(submit_file.status, HTTPStatus.CREATED)
        submission_id = json.loads(submit_file.read().decode("utf-8"))["submission"]["id"]

        admin_detail = _request(admin, f"/api/lms/student-courses/{course_instance_id}")
        self.assertEqual(admin_detail.status, HTTPStatus.OK)
        admin_detail_payload = json.loads(admin_detail.read().decode("utf-8"))["student_course"]
        self.assertEqual(admin_detail_payload["course_instance_id"], course_instance_id)

        downloaded = _request(admin, f"/api/lms/submissions/{submission_id}/download")
        self.assertEqual(downloaded.status, HTTPStatus.OK)
        downloaded_payload = json.loads(downloaded.read().decode("utf-8"))["submission"]
        self.assertEqual(downloaded_payload["file_name"], "lab1.txt")
        self.assertEqual(base64.b64decode(downloaded_payload["file_content_base64"]), file_bytes)


if __name__ == "__main__":
    unittest.main(verbosity=2)
