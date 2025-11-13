from database import (
    init_db, get_db, close_db,
    User, Role, Group, Subgroup, UserSettings,
    Course, CourseInfoResource, Test, Question, Option,
    Assignment, AssignmentResource, Submission, SubmissionFile, CourseAccess
)
from werkzeug.security import generate_password_hash
from datetime import datetime, timedelta
import random


def create_roles(db):
    roles = [
        Role(name='admin', description='Администратор'),
        Role(name='teacher', description='Преподаватель'),
        Role(name='student', description='Студент'),
        Role(name='applicant', description='Абитуриент'),
    ]
    db.add_all(roles)
    db.commit()
    return roles


def create_groups(db):
    group = Group(name='221-361', code='361')
    db.add(group)
    db.commit()
    subgroup1 = Subgroup(group_id=group.id, name='1')
    subgroup2 = Subgroup(group_id=group.id, name='2')
    db.add_all([subgroup1, subgroup2])
    db.commit()
    return group, [subgroup1, subgroup2]


def create_users(db, roles, group, subgroups):
    teacher = User(
        username='teacher',
        password=generate_password_hash('teachpass'),
        email='teacher@polytech.ru',
        first_name='Иван', last_name='Петров',
        role_id=roles[1].id
    )
    student = User(
        username='student',
        password=generate_password_hash('studpass'),
        email='student@polytech.ru',
        first_name='София', last_name='Баранова',
        group_id=group.id, subgroup_id=subgroups[0].id,
        role_id=roles[2].id
    )
    applicant = User(
        username='applicant',
        password=generate_password_hash('applicantpass'),
        email='applicant@polytech.ru',
        first_name='Алексей', last_name='Новиков',
        role_id=roles[3].id
    )
    db.add_all([teacher, student, applicant])
    db.commit()
    for user in [teacher, student, applicant]:
        db.add(UserSettings(user_id=user.id, theme='light'))
    db.commit()
    return teacher, student, applicant


def create_course(db, teacher):
    course = Course(
        short_id='PY101',
        title='Основы Python',
        description='Курс по основам программирования на Python',
        created_by=teacher.id,
        is_published=True
    )
    db.add(course)
    db.commit()
    return course


def create_course_info(db, course, teacher):
    info1 = CourseInfoResource(
        course_id=course.id,
        title='Программа курса',
        description='Документ с программой курса',
        filename='program.pdf',
        filepath='/static/course_info/program.pdf',
        uploaded_by=teacher.id
    )
    info2 = CourseInfoResource(
        course_id=course.id,
        title='Вводное видео',
        description='Видео о курсе',
        video_path='/static/course_info/intro.mp4',
        uploaded_by=teacher.id
    )
    db.add_all([info1, info2])
    db.commit()
    return [info1, info2]


def create_assignment(db, course, teacher, group, subgroup):
    assignment = Assignment(
        title='Задание 1: Hello World',
        description='Напишите программу Hello World',
        created_by=teacher.id,
        open_at=datetime.now(datetime.UTC),
        close_at=datetime.now(datetime.UTC) + timedelta(days=7),
        allow_upload=True,
        max_grade=10,
        group_restriction=group.id,
        subgroup_restriction=subgroup.id
    )
    db.add(assignment)
    db.commit()
    # Привязка к курсу через ассоциацию
    from database import course_assignments
    db.execute(course_assignments.insert().values(course_id=course.id, assignment_id=assignment.id))
    db.commit()
    # Добавим файл преподавателя
    res = AssignmentResource(
        assignment_id=assignment.id,
        filename='task.pdf',
        filepath='/static/assignments/task.pdf',
        uploaded_by=teacher.id
    )
    db.add(res)
    db.commit()
    return assignment, res


def create_test(db, course, teacher):
    test = Test(
        title='Тест 1: Основы',
        instructions='Ответьте на вопросы по основам Python',
        created_by=teacher.id
    )
    db.add(test)
    db.commit()
    # Привязка к курсу через ассоциацию
    from database import course_tests
    db.execute(course_tests.insert().values(course_id=course.id, test_id=test.id))
    db.commit()
    # Вопросы и варианты
    q1 = Question(
        test_id=test.id,
        text='Что выведет print(2+2)?',
        question_type='single',
        points=1
    )
    db.add(q1)
    db.commit()
    o1 = Option(question_id=q1.id, text='4', is_correct=True)
    o2 = Option(question_id=q1.id, text='22', is_correct=False)
    db.add_all([o1, o2])
    db.commit()
    q2 = Question(
        test_id=test.id,
        text='Какие типы данных есть в Python?',
        question_type='multiple',
        points=2
    )
    db.add(q2)
    db.commit()
    o3 = Option(question_id=q2.id, text='int', is_correct=True)
    o4 = Option(question_id=q2.id, text='str', is_correct=True)
    o5 = Option(question_id=q2.id, text='float', is_correct=True)
    o6 = Option(question_id=q2.id, text='char', is_correct=False)
    db.add_all([o3, o4, o5, o6])
    db.commit()
    return test, [q1, q2], [o1, o2, o3, o4, o5, o6]


def create_submission(db, assignment, student):
    submission = Submission(
        assignment_id=assignment.id,
        student_id=student.id,
        submitted_at=datetime.now(datetime.UTC),
        status='submitted'
    )
    db.add(submission)
    db.commit()
    # Добавим файл отправки
    sf = SubmissionFile(
        submission_id=submission.id,
        filename='solution.py',
        filepath='/static/submissions/solution.py'
    )
    db.add(sf)
    db.commit()
    return submission, sf


def create_course_access(db, course, teacher, student, group, subgroup):
    # Доступ преподавателю
    ca1 = CourseAccess(course_id=course.id, user_id=teacher.id, granted_by=teacher.id)
    # Доступ студенту
    ca2 = CourseAccess(course_id=course.id, user_id=student.id, granted_by=teacher.id)
    # Доступ группе
    ca3 = CourseAccess(course_id=course.id, group_id=group.id, granted_by=teacher.id)
    # Доступ подгруппе
    ca4 = CourseAccess(course_id=course.id, subgroup_id=subgroup.id, granted_by=teacher.id)
    db.add_all([ca1, ca2, ca3, ca4])
    db.commit()
    return [ca1, ca2, ca3, ca4]


def main():
    print('Инициализация тестовых данных...')
    init_db()
    db = get_db()
    try:
        roles = create_roles(db)
        group, subgroups = create_groups(db)
        teacher, student, applicant = create_users(db, roles, group, subgroups)
        course = create_course(db, teacher)
        course_info = create_course_info(db, course, teacher)
        assignment, assignment_res = create_assignment(db, course, teacher, group, subgroups[0])
        test, questions, options = create_test(db, course, teacher)
        submission, submission_file = create_submission(db, assignment, student)
        course_access = create_course_access(db, course, teacher, student, group, subgroups[0])
        print('Тестовые данные успешно созданы!')
    finally:
        close_db(db)

if __name__ == '__main__':
    main()
