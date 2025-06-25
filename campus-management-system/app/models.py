from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import date
from enum import Enum # 导入 Enum

db = SQLAlchemy()

# ✅ 新增：Role 枚举定义
class Role(Enum):
    ADMIN = 'Admin'
    STUDENT = 'Student'
    TEACHER = 'Teacher'

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False) # 存储密码哈希值
    # email = db.Column(db.String(120), unique=True, nullable=True) # 根据需要添加 email 字段
    role = db.Column(db.Enum(Role), nullable=False, default=Role.STUDENT)

    # 定义与 Student 和 Teacher 的关系
    # 如果您的 Student 和 Teacher 表中没有 user_id，需要先添加
    student = db.relationship('Student', backref='user', uselist=False, lazy=True, primaryjoin="User.id==Student.user_id")
    teacher = db.relationship('Teacher', backref='user', uselist=False, lazy=True, primaryjoin="User.id==Teacher.user_id")

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            # 'email': self.email, # 如果有 email 字段，取消注释
            'role': self.role.value if self.role else None
        }

    def __repr__(self):
        return f'<User {self.username} ({self.role.value})>'

class Student(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.String(20), unique=True, nullable=False)
    name = db.Column(db.String(80), nullable=False)
    gender = db.Column(db.String(10), nullable=True) # 添加 gender 字段
    major = db.Column(db.String(80), nullable=False)
    class_name = db.Column(db.String(80), nullable=True) # 添加 class_name 字段
    birthdate = db.Column(db.Date, nullable=True)
    enrollment_date = db.Column(db.Date, nullable=True)
    hometown = db.Column(db.String(80), nullable=True) # 添加 hometown 字段

    # ✅ 新增：关联到 User 模型，确保 user_id 字段在数据库表中存在
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), unique=True, nullable=True)

    def to_dict(self):
        return {
            'id': self.id,
            'student_id': self.student_id,
            'name': self.name,
            'gender': self.gender,
            'major': self.major,
            'class_name': self.class_name,
            'birthdate': self.birthdate.strftime('%Y-%m-%d') if self.birthdate else None,
            'enrollment_date': self.enrollment_date.strftime('%Y-%m-%d') if self.enrollment_date else None,
            'hometown': self.hometown,
            'user_id': self.user_id
        }

    def __repr__(self):
        return f'<Student {self.name}>'

class Teacher(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    teacher_id = db.Column(db.String(20), unique=True, nullable=True) # 假设 teacher_id 可为空，如果唯一且必填，请设为 nullable=False
    name = db.Column(db.String(80), nullable=False)
    gender = db.Column(db.String(10), nullable=True) # 添加 gender 字段
    title = db.Column(db.String(80), nullable=True) # 添加 title 字段
    department = db.Column(db.String(80), nullable=True)

    # ✅ 新增：关联到 User 模型，确保 user_id 字段在数据库表中存在
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), unique=True, nullable=True)

    def to_dict(self):
        return {
            'id': self.id,
            'teacher_id': self.teacher_id,
            'name': self.name,
            'gender': self.gender,
            'title': self.title,
            'department': self.department,
            'user_id': self.user_id
        }

    def __repr__(self):
        return f'<Teacher {self.name}>'

class Course(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    course_id = db.Column(db.String(20), unique=True, nullable=False)
    name = db.Column(db.String(80), nullable=False)
    teacher_id = db.Column(db.Integer, db.ForeignKey('teacher.id'), nullable=True) # 课程可以没有老师，如果必选请设为 False
    credits = db.Column(db.Integer, nullable=False)
    description = db.Column(db.Text, nullable=True)
    teacher = db.relationship('Teacher', backref='courses_taught') # backref 名称建议更明确

    def to_dict(self):
        return {
            'id': self.id,
            'course_id': self.course_id,
            'name': self.name,
            'teacher_id': self.teacher_id,
            'teacher_name': self.teacher.name if self.teacher else 'N/A',
            'credits': self.credits,
            'description': self.description
        }

    def __repr__(self):
        return f'<Course {self.name}>'

class Grade(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'), nullable=False)
    score = db.Column(db.Float, nullable=False)
    student = db.relationship('Student', backref='grades_received') # backref 名称建议更明确
    course = db.relationship('Course', backref='grades_given') # backref 名称建议更明确

    # Add a unique constraint to prevent a student from having multiple grades for the same course
    __table_args__ = (db.UniqueConstraint('student_id', 'course_id', name='_student_course_uc'),)

    def to_dict(self):
        return {
            'id': self.id,
            'student_id': self.student_id,
            'student_name': self.student.name if self.student else 'N/A',
            'student_id_num': self.student.student_id if self.student else 'N/A',
            'course_id': self.course_id,
            'course_name': self.course.name if self.course else 'N/A',
            'score': self.score
        }

    def __repr__(self):
        return f'<Grade {self.grade}>'


def generate_mock_data(app, db, num_students=100, num_courses=8, num_teachers=10):
    import random
    from datetime import date

    with app.app_context():
        # Clean up existing data (optional, for fresh start)
        # db.drop_all()
        # db.create_all()

        # Create Admin User (if not exists)
        admin_username = 'admin'
        admin_password = 'admin_password_123'
        if not User.query.filter_by(username=admin_username, role=Role.ADMIN).first():
            admin_user = User(
                username=admin_username,
                role=Role.ADMIN
            )
            admin_user.set_password(admin_password)
            db.session.add(admin_user)
            db.session.commit()
            print(f"Created initial admin user: {admin_username}")
        else:
            print(f"Admin user '{admin_username}' already exists.")


        # Create teachers
        teachers = []
        for i in range(num_teachers):
            teacher = Teacher(
                teacher_id=f'T{i+1:03}',
                name=f'Teacher {i+1}',
                gender=random.choice(['Male', 'Female']),
                title=random.choice(['Professor', 'Associate Professor', 'Lecturer']),
                department=random.choice(['Computer Science', 'Engineering', 'Mathematics', 'Arts'])
            )
            teachers.append(teacher)
            db.session.add(teacher)
            # Create a user for each teacher
            teacher_user = User(
                username=f'teacher{i+1}',
                role=Role.TEACHER
            )
            teacher_user.set_password('password123') # Default password for teachers
            db.session.add(teacher_user)
            db.session.flush() # Flush to get ID for relationship
            teacher.user_id = teacher_user.id # Link teacher to user
            db.session.add(teacher) # Re-add teacher to ensure relationship is tracked
        db.session.commit()
        print(f"Generated {num_teachers} teachers.")


        # Create courses
        courses = []
        available_teachers = Teacher.query.all()
        if not available_teachers:
            print("No teachers available to assign to courses. Please create teachers first.")
            return 0, 0, 0 # Return 0 for counts if no teachers
            
        for i in range(num_courses):
            course = Course(
                course_id=f'C{i+1:03}',
                name=f'Course {i+1}',
                credits=random.choice([2, 3, 4]),
                teacher_id=random.choice(available_teachers).id,
                description=f'Description for Course {i+1}'
            )
            courses.append(course)
            db.session.add(course)
        db.session.commit()
        print(f"Generated {num_courses} courses.")

        # Create students
        students = []
        majors = ['Computer Science', 'Engineering', 'Mathematics', 'Physics', 'Chemistry', 'Biology']
        classes = ['Class A', 'Class B', 'Class C']
        hometowns = ['Beijing', 'Shanghai', 'Guangzhou', 'Shenzhen', 'Chengdu', 'Wuhan', 'Xi\'an', 'Nanjing']

        for i in range(num_students):
            student = Student(
                student_id=f'S{2023000 + i + 1:04}', # Use a more distinct student ID
                name=f'Student {i+1}',
                gender=random.choice(['Male', 'Female']),
                major=random.choice(majors),
                class_name=random.choice(classes),
                birthdate=date(random.randint(2000, 2005), random.randint(1, 12), random.randint(1, 28)),
                enrollment_date=date(2023, 9, 1),
                hometown=random.choice(hometowns)
            )
            students.append(student)
            db.session.add(student)
            # Create a user for each student
            student_user = User(
                username=f'student{i+1}',
                role=Role.STUDENT
            )
            student_user.set_password('password123') # Default password for students
            db.session.add(student_user)
            db.session.flush() # Flush to get ID for relationship
            student.user_id = student_user.id # Link student to user
            db.session.add(student) # Re-add student to ensure relationship is tracked
        db.session.commit()
        print(f"Generated {num_students} students.")


        # Create grades
        available_students = Student.query.all()
        available_courses = Course.query.all()

        for student in available_students:
            # Each student takes 3-5 random courses
            num_courses_for_student = random.randint(3, 5)
            selected_courses = random.sample(available_courses, min(num_courses_for_student, len(available_courses)))

            for course in selected_courses:
                # Check if a grade already exists for this student and course
                existing_grade = Grade.query.filter_by(student_id=student.id, course_id=course.id).first()
                if not existing_grade:
                    grade = Grade(
                        student_id=student.id,
                        course_id=course.id,
                        score=random.randint(50, 100) # Random score between 50 and 100
                    )
                    db.session.add(grade)
        db.session.commit()
        print("Generated grades.")

        return num_students, num_courses, num_teachers # Return all counts
