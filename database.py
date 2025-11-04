from sqlalchemy import create_engine, Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime
import os
from loguru import logger

# Базовый класс для моделей
Base = declarative_base()

# Путь к базе данных
DATABASE_URL = "sqlite:///sdo.db"

# Создание движка
engine = create_engine(DATABASE_URL, echo=False)

# Создание сессии
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# ==================== МОДЕЛИ ====================

class User(Base):
    """Модель пользователя"""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, nullable=False, index=True)
    password = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Связи
    settings = relationship("UserSettings", back_populates="user", uselist=False)
    files = relationship("UploadedFile", back_populates="user")


class UserSettings(Base):
    """Модель настроек пользователя"""
    __tablename__ = "user_settings"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    theme = Column(String, default="light")
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Связи
    user = relationship("User", back_populates="settings")


class Lesson(Base):
    """Модель занятия"""
    __tablename__ = "lessons"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    lecturer_name = Column(String, nullable=False)
    start_time = Column(String, nullable=False)
    end_time = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class UploadedFile(Base):
    """Модель загруженного файла"""
    __tablename__ = "uploaded_files"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    filename = Column(String, nullable=False)
    filepath = Column(String, nullable=False)
    uploaded_at = Column(DateTime, default=datetime.utcnow)
    
    # Связи
    user = relationship("User", back_populates="files")


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


def create_user(username, password, email=None):
    """Создать нового пользователя"""
    db = get_db()
    try:
        user = User(username=username, password=password, email=email)
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


def update_user_settings(user_id, theme=None, notifications=None, email_notifications=None):
    """Обновить настройки пользователя"""
    db = get_db()
    try:
        settings = db.query(UserSettings).filter(UserSettings.user_id == user_id).first()
        
        if not settings:
            settings = UserSettings(user_id=user_id)
            db.add(settings)
        
        if theme is not None:
            settings.theme = theme
        if notifications is not None:
            settings.notifications = notifications
        if email_notifications is not None:
            settings.email_notifications = email_notifications
        
        settings.updated_at = datetime.utcnow()
        db.commit()
        return True
    except Exception as e:
        db.rollback()
        logger.error(f"Ошибка обновления настроек: {e}")
        return False
    finally:
        close_db(db)


def create_lesson(name, lecturer_name, start_time, end_time):
    """Создать новое занятие"""
    db = get_db()
    try:
        lesson = Lesson(
            name=name,
            lecturer_name=lecturer_name,
            start_time=start_time,
            end_time=end_time
        )
        db.add(lesson)
        db.commit()
        db.refresh(lesson)
        return lesson
    except Exception as e:
        db.rollback()
        logger.error(f"Ошибка создания занятия: {e}")
        return None
    finally:
        close_db(db)


def get_all_lessons():
    """Получить все занятия"""
    db = get_db()
    try:
        return db.query(Lesson).all()
    finally:
        close_db(db)


def save_uploaded_file(user_id, filename, filepath):
    """Сохранить информацию о загруженном файле"""
    db = get_db()
    try:
        file = UploadedFile(user_id=user_id, filename=filename, filepath=filepath)
        db.add(file)
        db.commit()
        return True
    except Exception as e:
        db.rollback()
        logger.error(f"Ошибка сохранения файла: {e}")
        return False
    finally:
        close_db(db)


def get_user_files(user_id):
    """Получить все файлы пользователя"""
    db = get_db()
    try:
        return db.query(UploadedFile).filter(UploadedFile.user_id == user_id).all()
    finally:
        close_db(db)


# ==================== ИНИЦИАЛИЗАЦИЯ ====================

if __name__ == "__main__":
    # Инициализация БД
    init_db()
    
    # Создание тестовых пользователей
    logger.info("Создание тестовых пользователей...")
    create_user("admin", "admin", "admin@mospolytech.ru")
    create_user("student", "123", "student@mospolytech.ru")
    
    # Создание тестового занятия
    logger.info("Создание тестового занятия...")
    create_lesson(
        name="Программирование на Python",
        lecturer_name="Иванов И.И.",
        start_time="12:00",
        end_time="13:30"
    )
    
    logger.success("Инициализация завершена!")
    logger.info("Создано пользователей: 2")
    logger.info("Создано занятий: 1")
