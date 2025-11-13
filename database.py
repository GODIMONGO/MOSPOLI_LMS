from sqlalchemy import (
    create_engine, Column, Integer, String, Boolean, DateTime, ForeignKey, Text, Table
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
import os
from loguru import logger
import uuid
from werkzeug.security import generate_password_hash, check_password_hash

# Базовый класс для моделей
Base = declarative_base()

# Путь к базе данных (локально sqlite)
DATABASE_URL = os.environ.get('DATABASE_URL', 'sqlite:///sdo.db')

# Создание движка
engine = create_engine(DATABASE_URL, echo=False)

# Создание сессии
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def gen_uuid():
    return str(uuid.uuid4())


# ----------------------------- MODELS -----------------------------


class Role(Base):
    __tablename__ = 'roles'
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(80), unique=True, nullable=False)
    description = Column(String(255))
    permissions = Column(Text)  # optional JSON as text


class Group(Base):
    __tablename__ = 'groups'
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(120), nullable=False)
    code = Column(String(50))
    created_at = Column(DateTime, default=datetime.utcnow)


class Subgroup(Base):
    __tablename__ = 'subgroups'
    id = Column(Integer, primary_key=True, index=True)
    group_id = Column(Integer, ForeignKey('groups.id'), nullable=False)
    name = Column(String(120), nullable=True)
    group = relationship('Group', backref='subgroups')


class User(Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, nullable=False, index=True)
    password = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=True)
    first_name = Column(String(120))
    last_name = Column(String(120))
    group_id = Column(Integer, ForeignKey('groups.id'), nullable=True)
    subgroup_id = Column(Integer, ForeignKey('subgroups.id'), nullable=True)
    two_fa_secret = Column(String(255), nullable=True)
    role_id = Column(Integer, ForeignKey('roles.id'), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    group = relationship('Group', backref='members')
    subgroup = relationship('Subgroup', backref='members')
    role = relationship('Role', backref='users')


class UserSettings(Base):
    __tablename__ = 'user_settings'
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey('users.id'), unique=True, nullable=False)
    theme = Column(String, default='light')
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    user = relationship('User', backref='settings')


# Course composition association tables
course_tests = Table(
    'course_tests', Base.metadata,
    Column('course_id', String(36), ForeignKey('courses.id'), primary_key=True),
    Column('test_id', String(36), ForeignKey('tests.id'), primary_key=True),
)

course_assignments = Table(
    'course_assignments', Base.metadata,
    Column('course_id', String(36), ForeignKey('courses.id'), primary_key=True),
    Column('assignment_id', String(36), ForeignKey('assignments.id'), primary_key=True),
)


class Course(Base):
    __tablename__ = 'courses'
    id = Column(String(36), primary_key=True, default=gen_uuid)
    short_id = Column(String(32), unique=True, nullable=False)
    title = Column(String(255), nullable=False)
    description = Column(Text)
    created_by = Column(Integer, ForeignKey('users.id'), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    is_published = Column(Boolean, default=False)

    creator = relationship('User', backref='created_courses')


class CourseInfoResource(Base):
    """Informational block resources for course: files, documents, video references"""
    __tablename__ = 'course_info_resources'
    id = Column(String(36), primary_key=True, default=gen_uuid)
    course_id = Column(String(36), ForeignKey('courses.id'), nullable=False)
    title = Column(String(255))
    description = Column(Text)
    filename = Column(String(255), nullable=True)
    filepath = Column(String(1024), nullable=True)
    video_path = Column(String(1024), nullable=True)
    uploaded_by = Column(Integer, ForeignKey('users.id'), nullable=True)
    uploaded_at = Column(DateTime, default=datetime.utcnow)

    course = relationship('Course', backref='info_resources')


class Test(Base):
    __tablename__ = 'tests'
    id = Column(String(36), primary_key=True, default=gen_uuid)
    title = Column(String(255), nullable=False)
    instructions = Column(Text)
    created_by = Column(Integer, ForeignKey('users.id'), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class Question(Base):
    __tablename__ = 'questions'
    id = Column(String(36), primary_key=True, default=gen_uuid)
    test_id = Column(String(36), ForeignKey('tests.id'), nullable=False)
    text = Column(Text, nullable=False)
    question_type = Column(String(20), default='single')  # 'single' or 'multiple'
    points = Column(Integer, default=1)

    test = relationship('Test', backref='questions')


class Option(Base):
    __tablename__ = 'options'
    id = Column(Integer, primary_key=True)
    question_id = Column(String(36), ForeignKey('questions.id'), nullable=False)
    text = Column(Text, nullable=False)
    is_correct = Column(Boolean, default=False)

    question = relationship('Question', backref='options')


class Assignment(Base):
    __tablename__ = 'assignments'
    id = Column(String(36), primary_key=True, default=gen_uuid)
    title = Column(String(255), nullable=False)
    description = Column(Text)
    created_by = Column(Integer, ForeignKey('users.id'), nullable=True)
    open_at = Column(DateTime, nullable=True)
    close_at = Column(DateTime, nullable=True)
    allow_upload = Column(Boolean, default=True)
    max_grade = Column(Integer, default=100)
    group_restriction = Column(Integer, ForeignKey('groups.id'), nullable=True)
    subgroup_restriction = Column(Integer, ForeignKey('subgroups.id'), nullable=True)

    creator = relationship('User', backref='created_assignments')


class AssignmentResource(Base):
    __tablename__ = 'assignment_resources'
    id = Column(String(36), primary_key=True, default=gen_uuid)
    assignment_id = Column(String(36), ForeignKey('assignments.id'), nullable=False)
    filename = Column(String(255), nullable=False)
    filepath = Column(String(1024), nullable=False)
    uploaded_by = Column(Integer, ForeignKey('users.id'), nullable=True)  # usually teacher
    uploaded_at = Column(DateTime, default=datetime.utcnow)

    assignment = relationship('Assignment', backref='teacher_files')


class Submission(Base):
    __tablename__ = 'submissions'
    id = Column(String(36), primary_key=True, default=gen_uuid)
    assignment_id = Column(String(36), ForeignKey('assignments.id'), nullable=False)
    student_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    submitted_at = Column(DateTime, default=datetime.utcnow)
    graded_by = Column(Integer, ForeignKey('users.id'), nullable=True)
    graded_at = Column(DateTime, nullable=True)
    grade = Column(Integer, nullable=True)
    status = Column(String(50), default='submitted')  # submitted, checked, returned
    feedback = Column(Text, nullable=True)

    assignment = relationship('Assignment', backref='submissions')


class SubmissionFile(Base):
    __tablename__ = 'submission_files'
    id = Column(String(36), primary_key=True, default=gen_uuid)
    submission_id = Column(String(36), ForeignKey('submissions.id'), nullable=False)
    filename = Column(String(255), nullable=False)
    filepath = Column(String(1024), nullable=False)
    uploaded_at = Column(DateTime, default=datetime.utcnow)

    submission = relationship('Submission', backref='files')


class CourseAccess(Base):
    __tablename__ = 'course_access'
    id = Column(Integer, primary_key=True, index=True)
    course_id = Column(String(36), ForeignKey('courses.id'), nullable=False)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=True)
    group_id = Column(Integer, ForeignKey('groups.id'), nullable=True)
    subgroup_id = Column(Integer, ForeignKey('subgroups.id'), nullable=True)
    granted_by = Column(Integer, ForeignKey('users.id'), nullable=True)
    granted_at = Column(DateTime, default=datetime.utcnow)


class ExcelTable(Base):
    __tablename__ = 'excel_table'
    id = Column(String(36), primary_key=True, default=gen_uuid)
    name = Column(String(200), nullable=False)
    description = Column(Text)
    owner_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    rows = Column(Integer, default=50)
    cols = Column(Integer, default=26)
    data = Column(Text)  # store JSON as text for sqlite compatibility
    styles = Column(Text)
    is_public = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    owner = relationship('User', backref='owned_tables')


# ==================== ФУНКЦИИ ====================


def init_db():
    """Инициализация базы данных - создание всех таблиц"""
    Base.metadata.create_all(bind=engine)
    logger.success("База данных инициализирована")


def get_db():
    """Получить сессию базы данных"""
    db = SessionLocal()
    return db


def close_db(db):
    """Закрыть сессию базы данных"""
    if db:
        db.close()


def create_user(username, password, email=None, first_name=None, last_name=None, role_id=None):
    """Создать нового пользователя (пароль хэшируется)"""
    db = get_db()
    try:
        hashed = generate_password_hash(password)
        user = User(username=username, password=hashed, email=email, first_name=first_name, last_name=last_name, role_id=role_id)
        db.add(user)
        db.commit()
        db.refresh(user)

        # Создаем настройки по умолчанию
        settings = UserSettings(user_id=user.id)
        db.add(settings)
        db.commit()

        return user
    except Exception as e:
        db.rollback()
        logger.error(f"Ошибка создания пользователя: {e}")
        return None
    finally:
        close_db(db)


def check_user_password(username, raw_password):
    db = get_db()
    try:
        user = db.query(User).filter(User.username == username).first()
        if not user:
            return False
        return check_password_hash(user.password, raw_password)
    finally:
        close_db(db)


def get_user_by_username(username):
    """Получить пользователя по username"""
    db = get_db()
    try:
        return db.query(User).filter(User.username == username).first()
    finally:
        close_db(db)


def get_user_settings(user_id):
    """Получить настройки пользователя"""
    db = get_db()
    try:
        return db.query(UserSettings).filter(UserSettings.user_id == user_id).first()
    finally:
        close_db(db)


def update_user_settings(user_id, theme=None):
    """Обновить настройки пользователя"""
    db = get_db()
    try:
        settings = db.query(UserSettings).filter(UserSettings.user_id == user_id).first()

        if not settings:
            settings = UserSettings(user_id=user_id)
            db.add(settings)

        if theme is not None:
            settings.theme = theme

        settings.updated_at = datetime.utcnow()
        db.commit()
        return True
    except Exception as e:
        db.rollback()
        logger.error(f"Ошибка обновления настроек: {e}")
        return False
    finally:
        close_db(db)


def save_assignment_resource(assignment_id, filename, filepath, uploaded_by=None):
    """Сохранить ресурс преподавателя для задания"""
    db = get_db()
    try:
        res = AssignmentResource(assignment_id=assignment_id, filename=filename, filepath=filepath, uploaded_by=uploaded_by)
        db.add(res)
        db.commit()
        db.refresh(res)
        return res
    except Exception as e:
        db.rollback()
        logger.error(f"Ошибка сохранения ресурса задания: {e}")
        return None
    finally:
        close_db(db)


def save_submission_file(submission_id, filename, filepath):
    """Сохранить файл, загруженный студентом в отправке"""
    db = get_db()
    try:
        sf = SubmissionFile(submission_id=submission_id, filename=filename, filepath=filepath)
        db.add(sf)
        db.commit()
        db.refresh(sf)
        return sf
    except Exception as e:
        db.rollback()
        logger.error(f"Ошибка сохранения файла отправки: {e}")
        return None
    finally:
        close_db(db)


def get_submission_files(submission_id):
    db = get_db()
    try:
        return db.query(SubmissionFile).filter(SubmissionFile.submission_id == submission_id).all()
    finally:
        close_db(db)


# legacy models removed


# ==================== ИНИЦИАЛИЗАЦИЯ ====================

if __name__ == "__main__":
    # Инициализация БД
    init_db()
    
    # Создание тестовых пользователей
    logger.info("Создание тестовых пользователей...")
    create_user("admin", "admin", "admin@mospolytech.ru")
    create_user("student", "123", "student@mospolytech.ru")
    
    logger.success("Инициализация завершена!")
