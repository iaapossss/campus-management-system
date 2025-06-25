from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='student')

    def __repr__(self):
        return f'<User {{self.username}}>'

class Student(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.String(20), unique=True, nullable=False)
    name = db.Column(db.String(80), nullable=False)
    major = db.Column(db.String(80), nullable=False)
    birthdate = db.Column(db.Date, nullable=True)
    enrollment_date = db.Column(db.Date, nullable=True)
    origin = db.Column(db.String(80), nullable=True)

    def __repr__(self):
        return f'<Student {{self.name}}>'

class Teacher(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    department = db.Column(db.String(80), nullable=False)

    def __repr__(self):
        return f'<Teacher {{self.name}}>'

class Course(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    course_code = db.Column(db.String(20), unique=True, nullable=False)
    name = db.Column(db.String(80), nullable=False)
    credits = db.Column(db.Integer, nullable=False)

    def __repr__(self):
        return f'<Course {{self.name}}>'

class Grade(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'), nullable=False)
    grade = db.Column(db.Float, nullable=False)

    student = db.relationship('Student', backref=db.backref('grades', lazy=True))
    course = db.relationship('Course', backref=db.backref('grades', lazy=True))

    def __repr__(self):
        return f'<Grade {{self.grade}}>'

def generate_mock_data(app, db, num_students=100, num_courses=8):
    import random
    from datetime import date

    with app.app_context():
        # Create courses
        courses = []
        for i in range(num_courses):
            course = Course(
                course_code=f'CS{i+1:03}',
                name=f'Course {i+1}',
                credits=3
            )
            courses.append(course)
            db.session.add(course)

        # Create students
        students = []
        for i in range(num_students):
            student = Student(
                student_id=f'2023{i+1:03}',
                name=f'Student {i+1}',
                major=random.choice(['Computer Science', 'Engineering', 'Mathematics']),
                birthdate=date(random.randint(2000, 2005), random.randint(1, 12), random.randint(1, 28)),
                enrollment_date=date(2023, 9, 1),
                origin='Some City'
            )
            students.append(student)
            db.session.add(student)

        db.session.commit()

        # Create grades
        for student in students:
            for course in courses:
                grade = Grade(
                    student_id=student.id,
                    course_id=course.id,
                    grade=random.randint(60, 100)
                )
                db.session.add(grade)

        db.session.commit()
        return num_students, num_courses
