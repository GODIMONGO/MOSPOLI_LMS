from flask_sqlalchemy import SQLAlchemy
from datetime import datetime
import uuid
import json

db = SQLAlchemy()

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Связь с таблицами
    owned_tables = db.relationship('ExcelTable', backref='owner', lazy=True, foreign_keys='ExcelTable.owner_id')
    
    def __repr__(self):
        return f'<User {self.username}>'

class ExcelTable(db.Model):
    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    
    # Владелец таблицы
    owner_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    # Метаданные таблицы
    rows = db.Column(db.Integer, default=50)
    cols = db.Column(db.Integer, default=26)
    
    # Данные таблицы в JSON
    data = db.Column(db.JSON, default=dict)
    styles = db.Column(db.JSON, default=dict)  # Стили ячеек
    
    # Настройки доступа
    is_public = db.Column(db.Boolean, default=False)
    password_protected = db.Column(db.Boolean, default=False)
    access_password = db.Column(db.String(120))
    
    # Временные метки
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_accessed = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Статистика
    view_count = db.Column(db.Integer, default=0)
    
    def __repr__(self):
        return f'<ExcelTable {self.name}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'rows': self.rows,
            'cols': self.cols,
            'data': self.data,
            'styles': self.styles,
            'is_public': self.is_public,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'owner': self.owner.username if self.owner else None
        }
    
    def can_access(self, user_id=None):
        """Проверяет, может ли пользователь получить доступ к таблице"""
        if self.is_public:
            return True
        if user_id == self.owner_id:
            return True
        # Проверка разрешений
        return TablePermission.query.filter_by(
            table_id=self.id, 
            user_id=user_id, 
            is_active=True
        ).first() is not None

class TablePermission(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    table_id = db.Column(db.String(36), db.ForeignKey('excel_table.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    # Права доступа
    can_view = db.Column(db.Boolean, default=True)
    can_edit = db.Column(db.Boolean, default=False)
    can_share = db.Column(db.Boolean, default=False)
    can_export = db.Column(db.Boolean, default=True)
    
    # Метаданные
    granted_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    granted_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_active = db.Column(db.Boolean, default=True)
    
    # Связи
    table = db.relationship('ExcelTable', backref='permissions')
    user = db.relationship('User', foreign_keys=[user_id], backref='table_permissions')
    granter = db.relationship('User', foreign_keys=[granted_by])
    
    def __repr__(self):
        return f'<Permission {self.user.username} -> {self.table.name}>'

class TableActivity(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    table_id = db.Column(db.String(36), db.ForeignKey('excel_table.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    
    # Тип активности
    action_type = db.Column(db.String(50), nullable=False)  # view, edit, create, share, export
    action_details = db.Column(db.JSON)  # Дополнительные детали
    
    # Метаданные
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    ip_address = db.Column(db.String(50))
    user_agent = db.Column(db.String(500))
    
    # Связи
    table = db.relationship('ExcelTable', backref='activities')
    user = db.relationship('User', backref='activities')
    
    def __repr__(self):
        return f'<Activity {self.action_type} on {self.table.name}>'