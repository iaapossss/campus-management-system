from flask import Blueprint, request, jsonify, render_template # 导入 render_template
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
from werkzeug.security import generate_password_hash, check_password_hash

from ..models import User, Student, Teacher, Role
from .. import db

auth_bp = Blueprint('auth', __name__)

# ✅ 修正点: 为 /login 路由添加 GET 方法，用于渲染登录页面
@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """用户登录接口：验证凭据并生成 JWT"""
    if request.method == 'GET':
        # 如果是 GET 请求，渲染登录页面
        return render_template('auth/login.html')
    
    # 如果是 POST 请求，执行登录逻辑
    data = request.get_json()

    if not data or not data.get('username') or not data.get('password'):
        return jsonify({'message': '缺少用户名或密码'}), 400

    user = User.query.filter_by(username=data.get('username')).first()

    if not user or not user.check_password(data.get('password')):
        return jsonify({'message': '无效的用户名或密码'}), 401

    try:
        access_token = create_access_token(identity={'id': user.id, 'role': user.role.value})
    except Exception as e:
        return jsonify({'message': f'生成令牌失败: {str(e)}'}), 500

    return jsonify({
        'message': '登录成功',
        'token': access_token,
        'user': user.to_dict()
    }), 200

@auth_bp.route('/register', methods=['POST'])
def register():
    """用户注册接口"""
    data = request.get_json()

    required_fields = ['username', 'password', 'role']
    for field in required_fields:
        if field not in data:
            return jsonify({'message': f'缺少必填字段: {field}'}), 400

    if User.query.filter_by(username=data['username']).first():
        return jsonify({'message': '用户名已存在'}), 400

    role_str = data['role'].upper()
    if role_str not in [r.name for r in Role]:
        return jsonify({'message': '无效的用户角色'}), 400
    
    # 阻止通过此接口注册管理员
    if Role[role_str] == Role.ADMIN:
        return jsonify({'message': '不允许通过此接口注册管理员账号'}), 403

    user = User(
        username=data['username'],
        role=Role[role_str]
    )
    user.set_password(data['password'])

    db.session.add(user)

    if user.role == Role.STUDENT and 'student_data' in data:
        student_data = data['student_data']
        from datetime import datetime # 导入 datetime 以处理日期字符串
        student = Student(
            student_id=student_data.get('student_id'),
            name=student_data.get('name'),
            major=student_data.get('major'),
            birthdate=datetime.strptime(student_data.get('birthdate'), '%Y-%m-%d').date() if student_data.get('birthdate') else None,
            enrollment_date=datetime.strptime(student_data.get('enrollment_date'), '%Y-%m-%d').date() if student_data.get('enrollment_date') else None,
            origin=student_data.get('origin'),
            user_id=user.id
        )
        db.session.add(student)

    elif user.role == Role.TEACHER and 'teacher_data' in data:
        teacher_data = data['teacher_data']
        teacher = Teacher(
            name=teacher_data.get('name'),
            department=teacher_data.get('department'),
            user_id=user.id
        )
        db.session.add(teacher)

    try:
        db.session.commit()
        return jsonify({
            'message': '用户注册成功',
            'user': user.to_dict()
        }), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': f'注册用户失败: {str(e)}'}), 500

@auth_bp.route('/profile', methods=['GET'])
@jwt_required()
def get_profile():
    """获取当前用户资料"""
    current_user_identity = get_jwt_identity()
    user_id = current_user_identity.get('id')
    user = User.query.get(user_id)

    if not user:
        return jsonify({'message': '用户未找到'}), 404

    profile_data = user.to_dict()

    if user.role == Role.STUDENT and user.student:
        profile_data['student_data'] = user.student.to_dict()
    elif user.role == Role.TEACHER and user.teacher:
        profile_data['teacher_data'] = user.teacher.to_dict()

    return jsonify(profile_data), 200

@auth_bp.route('/profile', methods=['PUT'])
@jwt_required()
def update_profile():
    """更新当前用户资料"""
    current_user_id = get_jwt_identity().get('id')
    user = User.query.get(current_user_id)

    if not user:
        return jsonify({'message': '用户未找到'}), 404

    data = request.get_json()

    if 'password' in data and data['password']:
        user.set_password(data['password'])

    if user.role == Role.STUDENT and user.student and 'student_data' in data:
        student_data = data['student_data']
        student = user.student

        for key, value in student_data.items():
            if hasattr(student, key) and key not in ['id', 'user_id']:
                from datetime import datetime # 导入 datetime 以处理日期字符串
                if key in ['birthdate', 'enrollment_date'] and value:
                    setattr(student, key, datetime.strptime(value, '%Y-%m-%d').date())
                elif key in ['birthdate', 'enrollment_date'] and not value:
                    setattr(student, key, None)
                else:
                    setattr(student, key, value)

    elif user.role == Role.TEACHER and user.teacher and 'teacher_data' in data:
        teacher_data = data['teacher_data']
        teacher = user.teacher

        for key, value in teacher_data.items():
            if hasattr(teacher, key) and key not in ['id', 'user_id']:
                setattr(teacher, key, value)

    try:
        db.session.commit()
        return jsonify({
            'message': '个人资料更新成功',
            'user': user.to_dict()
        }), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({'message': f'更新个人资料失败: {str(e)}'}), 500

@auth_bp.route('/logout', methods=['POST'])
@jwt_required(optional=True)
def logout():
    """用户登出接口"""
    return jsonify({'message': '已成功登出'}), 200

