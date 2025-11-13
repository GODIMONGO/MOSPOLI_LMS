from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import uuid
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()


def gen_uuid():
    return str(uuid.uuid4())


class Role(db.Model):
    __tablename__ = 'roles'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), unique=True, nullable=False)
    description = db.Column(db.String(255))
    # optional JSON field for fine-grained permissions per section
    permissions = db.Column(db.JSON, default=dict)

    def __repr__(self):
        return f"<Role {self.name}>"


class Group(db.Model):
    __tablename__ = 'groups'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    code = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    subgroups = db.relationship('Subgroup', backref='group', lazy=True)

    def __repr__(self):
        return f"<Group {self.name}>"


class Subgroup(db.Model):
    __tablename__ = 'subgroups'
    id = db.Column(db.Integer, primary_key=True)
    group_id = db.Column(db.Integer, db.ForeignKey('groups.id'), nullable=False)
    name = db.Column(db.String(120), nullable=True)

    def __repr__(self):
        return f"<Subgroup {self.name or self.id}>"


class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    _password = db.Column('password', db.String(256), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=True, index=True)
    first_name = db.Column(db.String(120))
    last_name = db.Column(db.String(120))
    group_id = db.Column(db.Integer, db.ForeignKey('groups.id'), nullable=True)
    subgroup_id = db.Column(db.Integer, db.ForeignKey('subgroups.id'), nullable=True)
    two_fa_secret = db.Column(db.String(255), nullable=True)
    role_id = db.Column(db.Integer, db.ForeignKey('roles.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # relations
    role = db.relationship('Role', backref='users')
    group = db.relationship('Group', backref='members')
    subgroup = db.relationship('Subgroup', backref='members')

    # submissions, courses created etc
    submissions = db.relationship('Submission', backref='student', lazy=True)

    def set_password(self, raw_password):
        self._password = generate_password_hash(raw_password)

    def check_password(self, raw_password):
        return check_password_hash(self._password, raw_password)

    def __repr__(self):
        return f"<User {self.username}>"


# Association tables for course composition
course_tests = db.Table(
    'course_tests',
    db.Column('course_id', db.String(36), db.ForeignKey('courses.id'), primary_key=True),
    db.Column('test_id', db.String(36), db.ForeignKey('tests.id'), primary_key=True),
)

course_assignments = db.Table(
    'course_assignments',
    db.Column('course_id', db.String(36), db.ForeignKey('courses.id'), primary_key=True),
    db.Column('assignment_id', db.String(36), db.ForeignKey('assignments.id'), primary_key=True),
)


class Course(db.Model):
    __tablename__ = 'courses'
    id = db.Column(db.String(36), primary_key=True, default=gen_uuid)
    short_id = db.Column(db.String(32), unique=True, nullable=False)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_published = db.Column(db.Boolean, default=False)

    creator = db.relationship('User', backref='created_courses')
    tests = db.relationship('Test', secondary=course_tests, backref='courses')
    assignments = db.relationship('Assignment', secondary=course_assignments, backref='courses')

    def __repr__(self):
        return f"<Course {self.short_id} - {self.title}>"


class Test(db.Model):
    __tablename__ = 'tests'
    id = db.Column(db.String(36), primary_key=True, default=gen_uuid)
    title = db.Column(db.String(255), nullable=False)
    instructions = db.Column(db.Text)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    questions = db.relationship('Question', backref='test', lazy=True)

    def __repr__(self):
        return f"<Test {self.title}>"


class Question(db.Model):
    __tablename__ = 'questions'
    id = db.Column(db.String(36), primary_key=True, default=gen_uuid)
    test_id = db.Column(db.String(36), db.ForeignKey('tests.id'), nullable=False)
    text = db.Column(db.Text, nullable=False)
    question_type = db.Column(db.String(20), default='single')  # 'single' or 'multiple'
    points = db.Column(db.Integer, default=1)

    options = db.relationship('Option', backref='question', lazy=True)

    def __repr__(self):
        return f"<Question {self.id}>"


class Option(db.Model):
    __tablename__ = 'options'
    id = db.Column(db.Integer, primary_key=True)
    question_id = db.Column(db.String(36), db.ForeignKey('questions.id'), nullable=False)
    text = db.Column(db.Text, nullable=False)
    is_correct = db.Column(db.Boolean, default=False)

    def __repr__(self):
        return f"<Option {self.id} for Q{self.question_id}>"


class Assignment(db.Model):
    __tablename__ = 'assignments'
    id = db.Column(db.String(36), primary_key=True, default=gen_uuid)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    open_at = db.Column(db.DateTime, nullable=True)
    close_at = db.Column(db.DateTime, nullable=True)
    allow_upload = db.Column(db.Boolean, default=True)
    max_grade = db.Column(db.Integer, default=100)
    group_restriction = db.Column(db.Integer, db.ForeignKey('groups.id'), nullable=True)
    subgroup_restriction = db.Column(db.Integer, db.ForeignKey('subgroups.id'), nullable=True)

    creator = db.relationship('User', backref='created_assignments')
    teacher_files = db.relationship('AssignmentResource', backref='assignment', lazy=True)
    submissions = db.relationship('Submission', backref='assignment', lazy=True)

    def __repr__(self):
        return f"<Assignment {self.title}>"


class AssignmentResource(db.Model):
    __tablename__ = 'assignment_resources'
    id = db.Column(db.String(36), primary_key=True, default=gen_uuid)
    assignment_id = db.Column(db.String(36), db.ForeignKey('assignments.id'), nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    filepath = db.Column(db.String(1024), nullable=False)
    uploaded_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)  # usually teacher
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)

    uploader = db.relationship('User')

    def __repr__(self):
        return f"<AssignmentResource {self.filename}>"


class Submission(db.Model):
    __tablename__ = 'submissions'
    id = db.Column(db.String(36), primary_key=True, default=gen_uuid)
    assignment_id = db.Column(db.String(36), db.ForeignKey('assignments.id'), nullable=False)
    student_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    submitted_at = db.Column(db.DateTime, default=datetime.utcnow)
    graded_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    graded_at = db.Column(db.DateTime, nullable=True)
    grade = db.Column(db.Integer, nullable=True)
    status = db.Column(db.String(50), default='submitted')  # submitted, checked, returned
    feedback = db.Column(db.Text, nullable=True)

    grader = db.relationship('User', foreign_keys=[graded_by])
    files = db.relationship('SubmissionFile', backref='submission', lazy=True)

    def __repr__(self):
        return f"<Submission {self.id} for A{self.assignment_id} by U{self.student_id}>"


class SubmissionFile(db.Model):
    __tablename__ = 'submission_files'
    id = db.Column(db.String(36), primary_key=True, default=gen_uuid)
    submission_id = db.Column(db.String(36), db.ForeignKey('submissions.id'), nullable=False)
    filename = db.Column(db.String(255), nullable=False)
    filepath = db.Column(db.String(1024), nullable=False)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<SubmissionFile {self.filename}>"


class CourseAccess(db.Model):
    __tablename__ = 'course_access'
    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.String(36), db.ForeignKey('courses.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    group_id = db.Column(db.Integer, db.ForeignKey('groups.id'), nullable=True)
    subgroup_id = db.Column(db.Integer, db.ForeignKey('subgroups.id'), nullable=True)
    granted_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    granted_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<CourseAccess course={self.course_id} user={self.user_id} group={self.group_id}>"


# legacy models removed
