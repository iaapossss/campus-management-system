from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity

from ..models import User, Teacher, Course, Student, Grade
from .. import db

teacher_bp = Blueprint('teacher', __name__)

# Decorator to check if user is a teacher
def teacher_required(fn):
    @jwt_required()
    def wrapper(*args, **kwargs):
        current_user = get_jwt_identity()
        if current_user.get('role') != Role.TEACHER:
            return jsonify({'message': 'Teacher privileges required'}), 403
        return fn(*args, **kwargs)
    wrapper.__name__ = fn.__name__
    return wrapper

# Helper function to get current teacher
def get_current_teacher():
    current_user_id = get_jwt_identity().get('id')
    user = User.query.get(current_user_id)
    
    if not user or user.role != Role.TEACHER or not user.teacher:
        return None
    
    return user.teacher

# Course routes
@teacher_bp.route('/courses', methods=['GET'])
@teacher_required
def get_teacher_courses():
    """Get courses taught by the current teacher"""
    teacher = get_current_teacher()
    
    if not teacher:
        return jsonify({'message': 'Teacher profile not found'}), 404
    
    courses = Course.query.filter_by(teacher_id=teacher.id).all()
    
    return jsonify({
        'courses': [course.to_dict() for course in courses]
    }), 200

@teacher_bp.route('/courses/<int:course_id>', methods=['GET'])
@teacher_required
def get_teacher_course(course_id):
    """Get a specific course taught by the current teacher"""
    teacher = get_current_teacher()
    
    if not teacher:
        return jsonify({'message': 'Teacher profile not found'}), 404
    
    course = Course.query.filter_by(id=course_id, teacher_id=teacher.id).first()
    
    if not course:
        return jsonify({'message': 'Course not found or not taught by you'}), 404
    
    return jsonify(course.to_dict()), 200

# Student routes
@teacher_bp.route('/students', methods=['GET'])
@teacher_required
def get_students():
    """Get all students (for reference)"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    search = request.args.get('search', '')
    major = request.args.get('major')
    
    query = Student.query
    
    if search:
        query = query.filter(
            (Student.name.ilike(f'%{search}%')) | 
            (Student.student_id.ilike(f'%{search}%'))
        )
    
    if major:
        query = query.filter_by(major=major)
    
    students = query.paginate(page=page, per_page=per_page)
    
    return jsonify({
        'students': [student.to_dict() for student in students.items],
        'total': students.total,
        'pages': students.pages,
        'current_page': students.page
    }), 200

@teacher_bp.route('/students/<int:student_id>', methods=['GET'])
@teacher_required
def get_student(student_id):
    """Get a specific student"""
    student = Student.query.get(student_id)
    
    if not student:
        return jsonify({'message': 'Student not found'}), 404
    
    return jsonify(student.to_dict()), 200

# Grade routes
@teacher_bp.route('/courses/<int:course_id>/grades', methods=['GET'])
@teacher_required
def get_course_grades(course_id):
    """Get grades for a specific course taught by the current teacher"""
    teacher = get_current_teacher()
    
    if not teacher:
        return jsonify({'message': 'Teacher profile not found'}), 404
    
    # Check if the course is taught by this teacher
    course = Course.query.filter_by(id=course_id, teacher_id=teacher.id).first()
    
    if not course:
        return jsonify({'message': 'Course not found or not taught by you'}), 404
    
    # Get grades for this course
    grades = Grade.query.filter_by(course_id=course_id).all()
    
    return jsonify({
        'grades': [grade.to_dict() for grade in grades]
    }), 200

@teacher_bp.route('/courses/<int:course_id>/grades', methods=['POST'])
@teacher_required
def create_grade(course_id):
    """Create a new grade for a course taught by the current teacher"""
    teacher = get_current_teacher()
    
    if not teacher:
        return jsonify({'message': 'Teacher profile not found'}), 404
    
    # Check if the course is taught by this teacher
    course = Course.query.filter_by(id=course_id, teacher_id=teacher.id).first()
    
    if not course:
        return jsonify({'message': 'Course not found or not taught by you'}), 404
    
    data = request.get_json()
    
    # Validate required fields
    required_fields = ['student_id', 'score', 'semester']
    for field in required_fields:
        if field not in data:
            return jsonify({'message': f'Missing required field: {field}'}), 400
    
    # Check if student exists
    student = Student.query.get(data['student_id'])
    if not student:
        return jsonify({'message': 'Student not found'}), 404
    
    # Check if grade already exists for this student, course, and semester
    existing_grade = Grade.query.filter_by(
        student_id=data['student_id'],
        course_id=course_id,
        semester=data['semester']
    ).first()
    
    if existing_grade:
        return jsonify({'message': 'Grade already exists for this student, course, and semester'}), 400
    
    # Create new grade
    grade = Grade(
        student_id=data['student_id'],
        course_id=course_id,
        score=data['score'],
        semester=data['semester']
    )
    
    try:
        db.session.add(grade)
        db.session.commit()
        return jsonify({
            'message': 'Grade created successfully',
            'grade': grade.to_dict()
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': f'Error creating grade: {str(e)}'}), 500

@teacher_bp.route('/grades/<int:grade_id>', methods=['PUT'])
@teacher_required
def update_grade(grade_id):
    """Update a grade for a course taught by the current teacher"""
    teacher = get_current_teacher()
    
    if not teacher:
        return jsonify({'message': 'Teacher profile not found'}), 404
    
    # Get the grade
    grade = Grade.query.get(grade_id)
    
    if not grade:
        return jsonify({'message': 'Grade not found'}), 404
    
    # Check if the course is taught by this teacher
    course = Course.query.filter_by(id=grade.course_id, teacher_id=teacher.id).first()
    
    if not course:
        return jsonify({'message': 'Grade not for a course taught by you'}), 403
    
    data = request.get_json()
    
    # Update grade data
    if 'score' in data:
        grade.score = data['score']
    
    if 'semester' in data:
        grade.semester = data['semester']
    
    try:
        db.session.commit()
        return jsonify({
            'message': 'Grade updated successfully',
            'grade': grade.to_dict()
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': f'Error updating grade: {str(e)}'}), 500

@teacher_bp.route('/grades/<int:grade_id>', methods=['DELETE'])
@teacher_required
def delete_grade(grade_id):
    """Delete a grade for a course taught by the current teacher"""
    teacher = get_current_teacher()
    
    if not teacher:
        return jsonify({'message': 'Teacher profile not found'}), 404
    
    # Get the grade
    grade = Grade.query.get(grade_id)
    
    if not grade:
        return jsonify({'message': 'Grade not found'}), 404
    
    # Check if the course is taught by this teacher
    course = Course.query.filter_by(id=grade.course_id, teacher_id=teacher.id).first()
    
    if not course:
        return jsonify({'message': 'Grade not for a course taught by you'}), 403
    
    try:
        db.session.delete(grade)
        db.session.commit()
        return jsonify({'message': 'Grade deleted successfully'}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': f'Error deleting grade: {str(e)}'}), 500

# Analytics routes
@teacher_bp.route('/courses/<int:course_id>/analytics', methods=['GET'])
@teacher_required
def get_course_analytics(course_id):
    """Get analytics for a specific course taught by the current teacher"""
    teacher = get_current_teacher()
    
    if not teacher:
        return jsonify({'message': 'Teacher profile not found'}), 404
    
    # Check if the course is taught by this teacher
    course = Course.query.filter_by(id=course_id, teacher_id=teacher.id).first()
    
    if not course:
        return jsonify({'message': 'Course not found or not taught by you'}), 404
    
    # Get grades for this course
    grades = Grade.query.filter_by(course_id=course_id).all()
    
    if not grades:
        return jsonify({'message': 'No grades found for this course'}), 404
    
    # Calculate statistics
    scores = [grade.score for grade in grades]
    
    # Basic statistics
    stats = {
        'count': len(scores),
        'avg_score': sum(scores) / len(scores),
        'min_score': min(scores),
        'max_score': max(scores)
    }
    
    # Score distribution
    distribution = {
        '90-100': len([s for s in scores if 90 <= s <= 100]),
        '80-89': len([s for s in scores if 80 <= s < 90]),
        '70-79': len([s for s in scores if 70 <= s < 80]),
        '60-69': len([s for s in scores if 60 <= s < 70]),
        'Below 60': len([s for s in scores if s < 60])
    }
    
    # Get student majors for this course
    student_majors = db.session.query(
        Student.major, 
        db.func.count(Student.id).label('count'),
        db.func.avg(Grade.score).label('avg_score')
    ).join(
        Grade, Student.id == Grade.student_id
    ).filter(
        Grade.course_id == course_id
    ).group_by(
        Student.major
    ).all()
    
    major_stats = [
        {
            'major': major,
            'count': count,
            'avg_score': float(avg_score)
        }
        for major, count, avg_score in student_majors
    ]
    
    return jsonify({
        'course_name': course.name,
        'stats': stats,
        'distribution': distribution,
        'major_stats': major_stats
    }), 200

@teacher_bp.route('/profile', methods=['GET'])
@teacher_required
def get_teacher_profile():
    """Get current teacher profile"""
    teacher = get_current_teacher()
    
    if not teacher:
        return jsonify({'message': 'Teacher profile not found'}), 404
    
    return jsonify(teacher.to_dict()), 200

@teacher_bp.route('/profile', methods=['PUT'])
@teacher_required
def update_teacher_profile():
    """Update current teacher profile"""
    teacher = get_current_teacher()
    
    if not teacher:
        return jsonify({'message': 'Teacher profile not found'}), 404
    
    data = request.get_json()
    
    # Update teacher data
    for key, value in data.items():
        if hasattr(teacher, key) and key != 'id' and key != 'user_id':
            setattr(teacher, key, value)
    
    try:
        db.session.commit()
        return jsonify({
            'message': 'Profile updated successfully',
            'teacher': teacher.to_dict()
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': f'Error updating profile: {str(e)}'}), 500
