from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from werkzeug.security import generate_password_hash

from ..models import User, Student, Teacher
from .. import db

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['POST'])
def login():
    """User login endpoint"""
    data = request.get_json()
    
    if not data or not data.get('username') or not data.get('password'):
        return jsonify({'message': 'Missing username or password'}), 400
    
    user = User.query.filter_by(username=data.get('username')).first()
    
    if not user or not user.check_password(data.get('password')):
        return jsonify({'message': 'Invalid username or password'}), 401
    
    # Generate access token
    token = user.generate_token()
    
    return jsonify({
        'message': 'Login successful',
        'token': token,
        'user': user.to_dict()
    }), 200

@auth_bp.route('/register', methods=['POST'])
def register():
    """User registration endpoint"""
    data = request.get_json()
    
    # Validate required fields
    required_fields = ['username', 'password', 'role']
    for field in required_fields:
        if field not in data:
            return jsonify({'message': f'Missing required field: {field}'}), 400
    
    # Check if username already exists
    if User.query.filter_by(username=data['username']).first():
        return jsonify({'message': 'Username already exists'}), 400
    
    # Validate role
    if data['role'] not in ['admin', 'teacher', 'student']:
        return jsonify({'message': 'Invalid role'}), 400
    
    # Create new user
    user = User(
        username=data['username'],
        password=generate_password_hash(data['password']),
        role=data['role']
    )
    
    db.session.add(user)
    
    # If role is student or teacher, create corresponding profile
    if user.role == 'student' and 'student_data' in data:
        student_data = data['student_data']
        student = Student(
            student_id=student_data.get('student_id'),
            name=student_data.get('name'),
            major=student_data.get('major'),
            birthdate=student_data.get('birthdate'),
            enrollment_date=student_data.get('birthdate'),
            origin=student_data.get('origin')
        )
        db.session.add(student)
    
    elif user.role == 'teacher' and 'teacher_data' in data:
        teacher_data = data['teacher_data']
        teacher = Teacher(
            name=teacher_data.get('name'),
            department=teacher_data.get('department')
        )
        db.session.add(teacher)
    
    try:
        db.session.commit()
        return jsonify({
            'message': 'User registered successfully',
            'user': user.to_dict()
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': f'Error registering user: {str(e)}'}), 500

@auth_bp.route('/profile', methods=['GET'])
@jwt_required()
def get_profile():
    """Get current user profile"""
    current_user_id = get_jwt_identity().get('id')
    user = User.query.get(current_user_id)
    
    if not user:
        return jsonify({'message': 'User not found'}), 404
    
    profile_data = user.to_dict()
    
    # Add role-specific data
    if user.role == 'student' and hasattr(user, 'student'):
        profile_data['student_data'] = user.student.to_dict()
    elif user.role == 'teacher' and hasattr(user, 'teacher'):
        profile_data['teacher_data'] = user.teacher.to_dict()
    
    return jsonify(profile_data), 200

@auth_bp.route('/profile', methods=['PUT'])
@jwt_required()
def update_profile():
    """Update current user profile"""
    current_user_id = get_jwt_identity().get('id')
    user = User.query.get(current_user_id)
    
    if not user:
        return jsonify({'message': 'User not found'}), 404
    
    data = request.get_json()
    
    # Update user data
    #if 'email' in data:
    #    user.email = data['email']
    
    if 'password' in data:
        user.password = generate_password_hash(data['password'])
    
    # Update role-specific data
    if user.role == 'student' and hasattr(user, 'student') and 'student_data' in data:
        student_data = data['student_data']
        student = Student.query.filter_by(user_id=current_user_id).first()
        
        for key, value in student_data.items():
            if hasattr(student, key) and key != 'id':
                setattr(student, key, value)
    
    elif user.role == 'teacher' and hasattr(user, 'teacher') and 'teacher_data' in data:
        teacher_data = data['teacher_data']
        teacher = Teacher.query.filter_by(user_id=current_user_id).first()
        
        for key, value in teacher_data.items():
            if hasattr(teacher, key) and key != 'id':
                setattr(teacher, key, value)
    
    try:
        db.session.commit()
        return jsonify({
            'message': 'Profile updated successfully',
            'user': user.to_dict()
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': f'Error updating profile: {str(e)}'}), 500
