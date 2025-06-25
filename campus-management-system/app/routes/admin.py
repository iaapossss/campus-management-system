from flask import Blueprint, request, jsonify, render_template, flash, redirect, url_for
from flask_jwt_extended import jwt_required, get_jwt_identity, exceptions as jwt_exceptions
from sqlalchemy import func
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import logging

# 配置日志
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

from ..models import User, Student, Teacher, Course, Grade, Role
from .. import db

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

# Decorator to check if user is admin
def admin_required(fn):
    @jwt_required(optional=True)
    def wrapper(*args, **kwargs):
        current_user_identity = None
        current_user = None
        
        # ✅ 修正点：将 jwt_exceptions.NoResultFound 也添加到捕获中
        # 这通常发生在 get_jwt_identity() 无法解析令牌内容时
        try:
            current_user_identity = get_jwt_identity()
            if current_user_identity:
                user_id = current_user_identity.get('id')
                current_user = User.query.get(user_id)
                logging.debug(f"JWT identity: {current_user_identity}, User found: {current_user}")
            else:
                logging.debug("No JWT token or token is invalid/missing.")
        except jwt_exceptions.NoAuthorizationError:
            logging.warning("No Authorization header provided.")
        except jwt_exceptions.InvalidHeaderError:
            logging.warning("Invalid Authorization header format.")
        except jwt_exceptions.DecodeError as e:
            logging.error(f"JWT DecodeError: {e}. Token might be invalid or secret key mismatch.")
            # 对于 HTML 请求，重定向到登录页，并带上闪现消息
            if 'text/html' in request.headers.get('Accept', ''):
                flash('认证令牌无效或已过期，请重新登录。', 'danger')
                return redirect(url_for('auth.login'))
            else:
                # 对于 API 请求，返回 401 JSON 响应
                return jsonify({'message': '认证令牌无效或已过期，请重新登录。'}), 401
        except jwt_exceptions.NoResultFound as e: # ✅ 新增捕获此异常
            logging.error(f"JWT NoResultFound error (token parse failed): {e}. This might cause 422.")
            if 'text/html' in request.headers.get('Accept', ''):
                flash('认证令牌解析失败，请重新登录。', 'danger')
                return redirect(url_for('auth.login'))
            else:
                return jsonify({'message': '认证令牌解析失败，请重新登录。'}), 401
        except Exception as e:
            logging.error(f"Unexpected JWT error: {e}")
            if 'text/html' in request.headers.get('Accept', ''):
                flash('认证过程中发生未知错误，请重试。', 'danger')
                return redirect(url_for('auth.login'))
            else:
                return jsonify({'message': f'认证过程中发生未知错误: {str(e)}'}), 500


        accepts_html = 'text/html' in request.headers.get('Accept', '')

        # 如果用户未认证或者不是管理员角色
        if not current_user or current_user.role != Role.ADMIN:
            logging.debug(f"Access denied for user: {current_user_identity}. Is HTML request: {accepts_html}")
            if accepts_html:
                flash('您需要登录并拥有管理员权限才能访问。', 'warning')
                return redirect(url_for('auth.login'))
            else:
                return jsonify({'message': '管理员权限不足或认证令牌缺失/无效。'}), 401
        
        logging.debug(f"Access granted for user: {current_user_identity}")
        return fn(*args, **kwargs)
    wrapper.__name__ = fn.__name__
    return wrapper


# =======================================================================
# Dashboard Route
# =======================================================================
@admin_bp.route('/')
@admin_required # 现在这个装饰器会处理重定向
def dashboard():
    """Admin dashboard"""
    total_students = Student.query.count()
    total_teachers = Teacher.query.count()
    total_courses = Course.query.count()
    total_users = User.query.count()
    return render_template('admin/dashboard.html',
                           active_page='dashboard',
                           total_students=total_students,
                           total_teachers=total_teachers,
                           total_courses=total_courses,
                           total_users=total_users)


# =======================================================================
# User Management Routes
# =======================================================================
@admin_bp.route('/users', methods=['GET'])
@admin_required
def manage_users():
    """Render user management page"""
    return render_template('admin/users.html', active_page='users')

@admin_bp.route('/api/users', methods=['GET'])
@admin_required
def api_users():
    """API to get all users for table"""
    page = request.args.get('page', 1, type=int)
    limit = request.args.get('limit', 10, type=int)
    keyword = request.args.get('keyword', type=str)
    role_filter = request.args.get('role', type=str)

    query = User.query

    if keyword:
        query = query.filter(
            (User.username.ilike(f'%{keyword}%')) |
            (User.email.ilike(f'%{keyword}%'))
        )
    if role_filter and role_filter != 'all':
        query = query.filter_by(role=Role[role_filter.upper()])

    pagination = query.paginate(page=page, per_page=limit, error_out=False)
    users = pagination.items
    total = pagination.total

    users_data = []
    for user in users:
        users_data.append(user.to_dict())

    return jsonify({
        "code": 0,
        "msg": "",
        "count": total,
        "data": users_data
    })

@admin_bp.route('/add_user_form', methods=['GET'])
@admin_required
def add_user_form():
    """Display form to add a new user"""
    return render_template('admin/add_user.html')

@admin_bp.route('/edit_user_form', methods=['GET'])
@admin_required
def edit_user_form():
    """Display form to edit user information"""
    user_id = request.args.get('user_id', type=int)
    user = User.query.get_or_404(user_id)
    return render_template('admin/edit_user.html', user=user)

@admin_bp.route('/api/users', methods=['POST'])
@admin_required
def create_user_api():
    """API: Create a new user"""
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    email = data.get('email')
    role_str = data.get('role')

    if not all([username, password, email, role_str]):
        return jsonify({'code': 1, 'msg': '所有字段都必须填写'}), 400

    if User.query.filter_by(username=username).first():
        return jsonify({'code': 1, 'msg': '用户名已存在'}), 409
    if User.query.filter_by(email=email).first():
        return jsonify({'code': 1, 'msg': '邮箱已存在'}), 409

    try:
        role = Role[role_str.upper()]
    except KeyError:
        return jsonify({'code': 1, 'msg': '无效的用户角色'}), 400

    hashed_password = generate_password_hash(password)
    new_user = User(username=username, password_hash=hashed_password, email=email, role=role)
    db.session.add(new_user)
    db.session.commit()
    return jsonify({'code': 0, 'msg': '用户创建成功'}), 201

@admin_bp.route('/api/users/<int:user_id>', methods=['PUT'])
@admin_required
def update_user_api(user_id):
    """API: Update an existing user"""
    user = User.query.get_or_404(user_id)
    data = request.get_json()

    user.username = data.get('username', user.username)
    user.email = data.get('email', user.email)
    
    new_password = data.get('password')
    if new_password:
        user.password_hash = generate_password_hash(new_password)
    
    role_str = data.get('role')
    if role_str:
        try:
            user.role = Role[role_str.upper()]
        except KeyError:
            return jsonify({'code': 1, 'msg': '无效的用户角色'}), 400

    db.session.commit()
    return jsonify({'code': 0, 'msg': '用户更新成功'})

@admin_bp.route('/api/users/<int:user_id>', methods=['DELETE'])
@admin_bp.route('/delete_user/<int:user_id>', methods=['POST']) # Add POST for Layui compatibility
@admin_required
def delete_user_api(user_id):
    """API: Delete a user"""
    user = User.query.get_or_404(user_id)
    db.session.delete(user)
    db.session.commit()
    return jsonify({'code': 0, 'msg': '用户删除成功'})


# =======================================================================
# Student Management Routes (Layui 兼容版)
# =======================================================================

@admin_bp.route('/students_layui')
@admin_required
def manage_students_layui():
    """
    管理学生信息（Layui表格页面）
    """
    return render_template('admin/students_layui.html', active_page='students')

@admin_bp.route('/api/students', methods=['GET'])
@admin_required
def api_students():
    """API: 提供学生数据给Layui表格"""
    page = request.args.get('page', 1, type=int)
    limit = request.args.get('limit', 10, type=int)
    keyword = request.args.get('keyword', type=str)
    major = request.args.get('major', type=str)
    class_name = request.args.get('class_name', type=str)
    hometown = request.args.get('hometown', type=str)

    query = Student.query

    if keyword:
        query = query.filter((Student.student_id.ilike(f'%{keyword}%')) |
                             (Student.name.ilike(f'%{keyword}%')))
    if major:
        query = query.filter(Student.major == major)
    if class_name:
        query = query.filter(Student.class_name == class_name)
    if hometown:
        query = query.filter(Student.hometown == hometown)

    pagination = query.paginate(page=page, per_page=limit, error_out=False)
    students = pagination.items
    total = pagination.total

    students_data = []
    for student in students:
        students_data.append(student.to_dict())

    return jsonify({
        "code": 0,
        "msg": "",
        "count": total,
        "data": students_data
    })

@admin_bp.route('/add_student_form', methods=['GET'])
@admin_required
def add_student_form():
    """显示添加学生的表单页面（Layui iframe 弹窗内容）"""
    majors = sorted([m[0] for m in db.session.query(Student.major).distinct().all() if m[0]])
    classes = sorted([c[0] for c in db.session.query(Student.class_name).distinct().all() if c[0]])
    return render_template('admin/add_student.html', majors=majors, classes=classes)

@admin_bp.route('/api/students', methods=['POST'])
@admin_required
def create_student_api():
    """API: 创建新学生"""
    data = request.get_json()
    required_fields = ['student_id', 'name', 'gender', 'major', 'class_name', 'hometown']
    if not all(field in data and data[field] for field in required_fields):
        return jsonify({'code': 1, 'msg': '所有必填字段都不能为空'}), 400

    if Student.query.filter_by(student_id=data['student_id']).first():
        return jsonify({'code': 1, 'msg': '学号已存在'}), 409

    try:
        new_student = Student(
            student_id=data['student_id'],
            name=data['name'],
            gender=data['gender'],
            major=data['major'],
            class_name=data['class_name'],
            hometown=data['hometown'],
            birthdate=datetime.strptime(data['birthdate'], '%Y-%m-%d').date() if data.get('birthdate') else None,
            enrollment_date=datetime.strptime(data['enrollment_date'], '%Y-%m-%d').date() if data.get('enrollment_date') else None
        )
        db.session.add(new_student)
        db.session.commit()
        return jsonify({'code': 0, 'msg': '学生添加成功'}), 201
    except Exception as e:
        db.session.rollback()
        print(f"Error adding student: {e}")
        return jsonify({'code': 1, 'msg': f'添加失败: {str(e)}'}), 500

@admin_bp.route('/edit_student_form', methods=['GET'])
@admin_required
def edit_student_form():
    """显示编辑学生信息的表单页面（Layui iframe 弹窗内容）"""
    student_id = request.args.get('student_id', type=int)
    student = Student.query.get_or_404(student_id)
    majors = sorted([m[0] for m in db.session.query(Student.major).distinct().all() if m[0]])
    classes = sorted([c[0] for c in db.session.query(Student.class_name).distinct().all() if c[0]])
    return render_template('admin/edit_student.html', student=student, majors=majors, classes=classes)

@admin_bp.route('/api/students/<int:student_id>', methods=['PUT'])
@admin_required
def update_student_api(student_id):
    """API: 更新学生信息"""
    student = Student.query.get_or_404(student_id)
    data = request.get_json()

    try:
        student.name = data.get('name', student.name)
        student.gender = data.get('gender', student.gender)
        student.major = data.get('major', student.major)
        student.class_name = data.get('class_name', student.class_name)
        student.hometown = data.get('hometown', student.hometown)
        if 'birthdate' in data and data['birthdate']:
            student.birthdate = datetime.strptime(data['birthdate'], '%Y-%m-%d').date()
        elif 'birthdate' in data and not data['birthdate']:
            student.birthdate = None
        if 'enrollment_date' in data and data['enrollment_date']:
            student.enrollment_date = datetime.strptime(data['enrollment_date'], '%Y-%m-%d').date()
        elif 'enrollment_date' in data and not data['enrollment_date']:
            student.enrollment_date = None

        db.session.commit()
        return jsonify({'code': 0, 'msg': '学生信息更新成功'})
    except Exception as e:
        db.session.rollback()
        print(f"Error updating student {student_id}: {e}")
        return jsonify({'code': 1, 'msg': f'更新失败: {str(e)}'}), 500

@admin_bp.route('/delete_student/<int:student_id>', methods=['POST'])
@admin_required
def delete_student():
    """API: 删除单个学生"""
    student = Student.query.get(student_id)
    if not student:
        return jsonify({'code': 1, 'msg': '学生不存在'}), 404
    try:
        db.session.delete(student)
        db.session.commit()
        return jsonify({'code': 0, 'msg': '删除成功'})
    except Exception as e:
        db.session.rollback()
        print(f"Error deleting student {student_id}: {e}")
        return jsonify({'code': 1, 'msg': f'删除失败: {str(e)}'}), 500

@admin_bp.route('/batch_delete_students', methods=['POST'])
@admin_required
def batch_delete_students():
    """API: 批量删除学生"""
    data = request.get_json()
    student_ids = data.get('ids', [])
    if not student_ids:
        return jsonify({'code': 1, 'msg': '未选择任何学生'}), 400

    try:
        deleted_count = Student.query.filter(Student.id.in_(student_ids)).delete(synchronize_session=False)
        db.session.commit()
        return jsonify({'code': 0, 'msg': f'成功删除 {deleted_count} 名学生'})
    except Exception as e:
        db.session.rollback()
        print(f"Error batch deleting students: {e}")
        return jsonify({'code': 1, 'msg': f'批量删除失败: {str(e)}'}), 500

@admin_bp.route('/api/distinct_majors', methods=['GET'])
@admin_required # 重新启用此装饰器
def get_distinct_majors():
    """API: 获取所有唯一的专业名称"""
    all_majors = [m[0] for m in db.session.query(Student.major).distinct().all() if m[0]]
    return jsonify({'code': 0, 'msg': 'Success', 'data': sorted(all_majors)})

@admin_bp.route('/api/distinct_classes', methods=['GET'])
@admin_required
def get_distinct_classes():
    """API: 获取所有唯一的班级名称"""
    all_classes = [c[0] for c in db.session.query(Student.class_name).distinct().all() if c[0]]
    return jsonify({'code': 0, 'msg': 'Success', 'data': sorted(all_classes)})

@admin_bp.route('/api/distinct_hometowns', methods=['GET'])
@admin_required
def get_distinct_hometowns():
    """API: 获取所有唯一的生源地名称"""
    all_hometowns = [h[0] for h in db.session.query(Student.hometown).distinct().all() if h[0]]
    return jsonify({'code': 0, 'msg': 'Success', 'data': sorted(all_hometowns)})


# =======================================================================
# Teacher Management Routes
# =======================================================================
@admin_bp.route('/teachers', methods=['GET'])
@admin_required
def manage_teachers():
    """Render teacher management page"""
    return render_template('admin/teachers.html', active_page='teachers')

@admin_bp.route('/api/teachers', methods=['GET'])
@admin_required
def api_teachers():
    """API to get all teachers for table"""
    page = request.args.get('page', 1, type=int)
    limit = request.args.get('limit', 10, type=int)
    keyword = request.args.get('keyword', type=str)

    query = Teacher.query

    if keyword:
        query = query.filter(
            (Teacher.teacher_id.ilike(f'%{keyword}%')) |
            (Teacher.name.ilike(f'%{keyword}%'))
        )

    pagination = query.paginate(page=page, per_page=limit, error_out=False)
    teachers = pagination.items
    total = pagination.total

    teachers_data = []
    for teacher in teachers:
        teachers_data.append(teacher.to_dict())

    return jsonify({
        "code": 0,
        "msg": "",
        "count": total,
        "data": teachers_data
    })

@admin_bp.route('/add_teacher_form', methods=['GET'])
@admin_required
def add_teacher_form():
    """Display form to add a new teacher"""
    return render_template('admin/add_teacher.html')

@admin_bp.route('/api/teachers', methods=['POST'])
@admin_required
def create_teacher_api():
    """Create a new teacher"""
    data = request.get_json()
    required_fields = ['teacher_id', 'name', 'gender', 'title', 'department']
    if not all(field in data and data[field] for field in required_fields):
        return jsonify({'code': 1, 'msg': '所有必填字段都不能为空'}), 400

    if Teacher.query.filter_by(teacher_id=data['teacher_id']).first():
        return jsonify({'code': 1, 'msg': '教师工号已存在'}), 409

    try:
        new_teacher = Teacher(
            teacher_id=data['teacher_id'],
            name=data['name'],
            gender=data['gender'],
            title=data['title'],
            department=data['department']
        )
        db.session.add(new_teacher)
        db.session.commit()
        return jsonify({'code': 0, 'msg': '教师添加成功'}), 201
    except Exception as e:
        db.session.rollback()
        print(f"Error adding teacher: {e}")
        return jsonify({'code': 1, 'msg': f'添加失败: {str(e)}'}), 500

@admin_bp.route('/edit_teacher_form', methods=['GET'])
@admin_required
def edit_teacher_form():
    """Display form to edit teacher information"""
    teacher_id = request.args.get('teacher_id', type=int)
    teacher = Teacher.query.get_or_404(teacher_id)
    return render_template('admin/edit_teacher.html', teacher=teacher)

@admin_bp.route('/api/teachers/<int:teacher_id>', methods=['PUT'])
@admin_required
def update_teacher_api(teacher_id):
    """Update teacher information"""
    teacher = Teacher.query.get_or_404(teacher_id)
    data = request.get_json()

    try:
        teacher.name = data.get('name', teacher.name)
        teacher.gender = data.get('gender', teacher.gender)
        teacher.title = data.get('title', teacher.title)
        teacher.department = data.get('department', teacher.department)
        db.session.commit()
        return jsonify({'code': 0, 'msg': '教师信息更新成功'})
    except Exception as e:
        db.session.rollback()
        print(f"Error updating teacher {teacher_id}: {e}")
        return jsonify({'code': 1, 'msg': f'更新失败: {str(e)}'}), 500

@admin_bp.route('/delete_teacher/<int:teacher_id>', methods=['POST'])
@admin_required
def delete_teacher_api_route(teacher_id):
    """Delete a single teacher"""
    teacher = Teacher.query.get(teacher_id)
    if not teacher:
        return jsonify({'code': 1, 'msg': '教师不存在'}), 404
    try:
        db.session.delete(teacher)
        db.session.commit()
        return jsonify({'code': 0, 'msg': '删除成功'})
    except Exception as e:
        db.session.rollback()
        print(f"Error deleting teacher {teacher_id}: {e}")
        return jsonify({'code': 1, 'msg': f'删除失败: {str(e)}'}), 500

@admin_bp.route('/batch_delete_teachers', methods=['POST'])
@admin_required
def batch_delete_teachers_api_route():
    """Batch delete teachers"""
    data = request.get_json()
    teacher_ids = data.get('ids', [])
    if not teacher_ids:
        return jsonify({'code': 1, 'msg': '未选择任何教师'}), 400

    try:
        teachers_to_delete = Teacher.query.filter(Teacher.id.in_(teacher_ids)).all()
        for teacher in teachers_to_delete:
            db.session.delete(teacher)
        db.session.commit()
        return jsonify({'code': 0, 'msg': f'成功删除 {len(teachers_to_delete)} 名教师'})
    except Exception as e:
        db.session.rollback()
        print(f"Error batch deleting teachers: {e}")
        return jsonify({'code': 1, 'msg': f'批量删除失败: {str(e)}'}), 500


# =======================================================================
# Course Management Routes
# =======================================================================
@admin_bp.route('/courses', methods=['GET'])
@admin_required
def manage_courses():
    """Render course management page"""
    return render_template('admin/courses.html', active_page='courses')

@admin_bp.route('/api/courses', methods=['GET'])
@admin_required
def api_courses():
    """API to get all courses for table"""
    page = request.args.get('page', 1, type=int)
    limit = request.args.get('limit', 10, type=int)
    keyword = request.args.get('keyword', type=str)
    
    query = Course.query

    if keyword:
        query = query.filter(
            (Course.course_id.ilike(f'%{keyword}%')) |
            (Course.name.ilike(f'%{keyword}%')) |
            (Course.teacher.has(Teacher.name.ilike(f'%{keyword}%')))
        )

    pagination = query.paginate(page=page, per_page=limit, error_out=False)
    courses = pagination.items
    total = pagination.total

    courses_data = []
    for course in courses:
        courses_data.append(course.to_dict())

    return jsonify({
        "code": 0,
        "msg": "",
        "count": total,
        "data": courses_data
    })

@admin_bp.route('/add_course_form', methods=['GET'])
@admin_required
def add_course_form():
    """Display form to add a new course"""
    teachers = Teacher.query.all()
    return render_template('admin/add_course.html', teachers=teachers)

@admin_bp.route('/api/courses', methods=['POST'])
@admin_required
def create_course_api():
    """Create a new course"""
    data = request.get_json()
    required_fields = ['course_id', 'name', 'teacher_id', 'credits']
    if not all(field in data and data[field] for field in required_fields):
        return jsonify({'code': 1, 'msg': '所有必填字段都不能为空'}), 400

    if Course.query.filter_by(course_id=data['course_id']).first():
        return jsonify({'code': 1, 'msg': '课程号已存在'}), 409
    
    teacher = Teacher.query.get(data['teacher_id'])
    if not teacher:
        return jsonify({'code': 1, 'msg': '指定教师不存在'}), 400

    try:
        new_course = Course(
            course_id=data['course_id'],
            name=data['name'],
            teacher_id=data['teacher_id'],
            credits=data['credits'],
            description=data.get('description')
        )
        db.session.add(new_course)
        db.session.commit()
        return jsonify({'code': 0, 'msg': '课程添加成功'}), 201
    except Exception as e:
        db.session.rollback()
        print(f"Error adding course: {e}")
        return jsonify({'code': 1, 'msg': f'添加失败: {str(e)}'}), 500

@admin_bp.route('/edit_course_form', methods=['GET'])
@admin_required
def edit_course_form():
    """Display form to edit course information"""
    course_id = request.args.get('course_id', type=int)
    course = Course.query.get_or_404(course_id)
    teachers = Teacher.query.all()
    return render_template('admin/edit_course.html', course=course, teachers=teachers)

@admin_bp.route('/api/courses/<int:course_id>', methods=['PUT'])
@admin_required
def update_course_api(course_id):
    """Update course information"""
    course = Course.query.get_or_404(course_id)
    data = request.get_json()

    try:
        course.name = data.get('name', course.name)
        course.credits = data.get('credits', course.credits)
        course.description = data.get('description', course.description)
        
        teacher_id = data.get('teacher_id')
        if teacher_id:
            teacher = Teacher.query.get(teacher_id)
            if not teacher:
                return jsonify({'code': 1, 'msg': '指定教师不存在'}), 400
            course.teacher_id = teacher_id

        db.session.commit()
        return jsonify({'code': 0, 'msg': '课程信息更新成功'})
    except Exception as e:
        db.session.rollback()
        print(f"Error updating course {course_id}: {e}")
        return jsonify({'code': 1, 'msg': f'更新失败: {str(e)}'}), 500

@admin_bp.route('/delete_course/<int:course_id>', methods=['POST'])
@admin_required
def delete_course_api_route(course_id):
    """Delete a single course"""
    course = Course.query.get(course_id)
    if not course:
        return jsonify({'code': 1, 'msg': '课程不存在'}), 404
    try:
        db.session.delete(course)
        db.session.commit()
        return jsonify({'code': 0, 'msg': '删除成功'})
    except Exception as e:
        db.session.rollback()
        print(f"Error deleting course {course_id}: {e}")
        return jsonify({'code': 1, 'msg': f'删除失败: {str(e)}'}), 500

@admin_bp.route('/batch_delete_courses', methods=['POST'])
@admin_required
def batch_delete_courses_api_route():
    """Batch delete courses"""
    data = request.get_json()
    course_ids = data.get('ids', [])
    if not course_ids:
        return jsonify({'code': 1, 'msg': '未选择任何课程'}), 400

    try:
        deleted_count = Course.query.filter(Course.id.in_(course_ids)).delete(synchronize_session=False)
        db.session.commit()
        return jsonify({'code': 0, 'msg': f'成功删除 {deleted_count} 门课程'})
    except Exception as e:
        db.session.rollback()
        print(f"Error batch deleting courses: {e}")
        return jsonify({'code': 1, 'msg': f'批量删除失败: {str(e)}'}), 500


# =======================================================================
# Grade Management Routes
# =======================================================================
@admin_bp.route('/grades', methods=['GET'])
@admin_required
def manage_grades():
    """Render grade management page"""
    students = Student.query.all()
    courses = Course.query.all()
    return render_template('admin/grades.html', active_page='grades', students=students, courses=courses)

@admin_bp.route('/api/grades', methods=['GET'])
@admin_required
def api_grades():
    """API to get all grades for table"""
    page = request.args.get('page', 1, type=int)
    limit = request.args.get('limit', 10, type=int)
    student_id = request.args.get('student_id', type=int)
    course_id = request.args.get('course_id', type=int)
    
    query = Grade.query

    if student_id:
        query = query.filter_by(student_id=student_id)
    if course_id:
        query = query.filter_by(course_id=course_id)
    
    query = query.join(Student).join(Course)

    pagination = query.paginate(page=page, per_page=limit, error_out=False)
    grades = pagination.items
    total = pagination.total

    grades_data = []
    for grade in grades:
        grades_data.append(grade.to_dict())

    all_students_for_filter = [{'id': s.id, 'name': s.name, 'student_id': s.student_id} for s in Student.query.all()]
    all_courses_for_filter = [{'id': c.id, 'name': c.name} for c in Course.query.all()]


    return jsonify({
        "code": 0,
        "msg": "",
        "count": total,
        "data": grades_data,
        "all_students": all_students_for_filter,
        "all_courses": all_courses_for_filter
    })

@admin_bp.route('/add_grade_form', methods=['GET'])
@admin_required
def add_grade_form():
    """Display form to add a new grade"""
    students = Student.query.all()
    courses = Course.query.all()
    return render_template('admin/add_grade.html', students=students, courses=courses)

@admin_bp.route('/api/grades', methods=['POST'])
@admin_required
def create_grade_api():
    """Create a new grade"""
    data = request.get_json()
    student_id = data.get('student_id')
    course_id = data.get('course_id')
    score = data.get('score')

    if not all([student_id, course_id, score is not None]):
        return jsonify({'code': 1, 'msg': '所有字段都必须填写'}), 400
    
    student = Student.query.get(student_id)
    course = Course.query.get(course_id)
    if not student or not course:
        return jsonify({'code': 1, 'msg': '学生或课程不存在'}), 400

    if Grade.query.filter_by(student_id=student_id, course_id=course_id).first():
        return jsonify({'code': 1, 'msg': '该学生已存在此课程的成绩，请编辑'}), 409

    try:
        new_grade = Grade(student_id=student_id, course_id=course_id, score=score)
        db.session.add(new_grade)
        db.session.commit()
        return jsonify({'code': 0, 'msg': '成绩录入成功'}), 201
    except Exception as e:
        db.session.rollback()
        print(f"Error adding grade: {e}")
        return jsonify({'code': 1, 'msg': f'成绩录入失败: {str(e)}'}), 500

@admin_bp.route('/edit_grade_form', methods=['GET'])
@admin_required
def edit_grade_form():
    """Display form to edit grade information"""
    grade_id = request.args.get('grade_id', type=int)
    grade = Grade.query.get_or_404(grade_id)
    students = Student.query.all()
    courses = Course.query.all()
    return render_template('admin/edit_grade.html', grade=grade, students=students, courses=courses)

@admin_bp.route('/api/grades/<int:grade_id>', methods=['PUT'])
@admin_required
def update_grade_api(grade_id):
    """Update grade information"""
    grade = Grade.query.get_or_404(grade_id)
    data = request.get_json()

    score = data.get('score')
    if score is not None:
        grade.score = score
    else:
        return jsonify({'code': 1, 'msg': '分数不能为空'}), 400

    try:
        db.session.commit()
        return jsonify({'code': 0, 'msg': '成绩更新成功'})
    except Exception as e:
        db.session.rollback()
        print(f"Error updating grade {grade_id}: {e}")
        return jsonify({'code': 1, 'msg': f'更新失败: {str(e)}'}), 500

@admin_bp.route('/delete_grade/<int:grade_id>', methods=['POST'])
@admin_required
def delete_grade_api_route(grade_id):
    """Delete a single grade"""
    grade = Grade.query.get(grade_id)
    if not grade:
        return jsonify({'code': 1, 'msg': '成绩不存在'}), 404
    try:
        db.session.delete(grade)
        db.session.commit()
        return jsonify({'code': 0, 'msg': '删除成功'})
    except Exception as e:
        db.session.rollback()
        print(f"Error deleting grade {grade_id}: {e}")
        return jsonify({'code': 1, 'msg': f'删除失败: {str(e)}'}), 500

@admin_bp.route('/batch_delete_grades', methods=['POST'])
@admin_required
def batch_delete_grades_api_route():
    """Batch delete grades"""
    data = request.get_json()
    grade_ids = data.get('ids', [])
    if not grade_ids:
        return jsonify({'code': 1, 'msg': '未选择任何成绩'}), 400

    try:
        deleted_count = Grade.query.filter(Grade.id.in_(grade_ids)).delete(synchronize_session=False)
        db.session.commit()
        return jsonify({'code': 0, 'msg': f'成功删除 {deleted_count} 条成绩'})
    except Exception as e:
        db.session.rollback()
        print(f"Error batch deleting grades: {e}")
        return jsonify({'code': 1, 'msg': f'批量删除失败: {str(e)}'}), 500


# =======================================================================
# Data Analytics and Visualization Routes
# =======================================================================
@admin_bp.route('/data_visualization', methods=['GET'])
@admin_required
def data_visualization():
    """Render data visualization page"""
    courses = Course.query.all()
    majors = sorted([m[0] for m in db.session.query(Student.major).distinct().all() if m[0]])
    return render_template('admin/data_visualization.html',
                           active_page='grade_analytics',
                           courses=courses,
                           majors=majors)

@admin_bp.route('/analytics/grades_distribution', methods=['GET'])
@admin_required
def get_grades_distribution():
    """Get data for grade distribution box plot and course/major average scores"""
    course_id = request.args.get('course_id', type=int)
    major_name = request.args.get('major', type=str)
    student_id = request.args.get('student_id', type=str)

    grades_query = Grade.query.join(Student).join(Course)

    if course_id:
        grades_query = grades_query.filter(Grade.course_id == course_id)
    if major_name:
        grades_query = grades_query.filter(Student.major == major_name)
    if student_id:
        grades_query = grades_query.filter(Student.student_id == student_id)

    grades = grades_query.all()

    all_scores = [grade.score for grade in grades]

    courses_avg = db.session.query(
        Course.name,
        func.avg(Grade.score)
    ).join(Grade).group_by(Course.name).all()

    majors_avg = db.session.query(
        Student.major,
        func.avg(Grade.score)
    ).join(Grade).group_by(Student.major).all()

    student_scores_radar = {}
    if student_id:
        student = Student.query.filter_by(student_id=student_id).first()
        if student:
            student_grades = Grade.query.filter_by(student_id=student.id).join(Course).all()
            for sg in student_grades:
                student_scores_radar[sg.course.name] = sg.score

    course_score_distribution = {}
    if course_id:
        course_grades = Grade.query.filter_by(course_id=course_id).all()
        scores_for_pie = [grade.score for grade in course_grades]
        course_score_distribution = {'scores': scores_for_pie, 'total_grades': len(scores_for_pie)}


    return jsonify({
        'all_scores': all_scores,
        'courses_avg': [{'name': c_name, 'avg': avg} for c_name, avg in courses_avg],
        'majors_avg': [{'major': m_name, 'avg': avg} for m_name, avg in majors_avg],
        'student_scores_radar': student_scores_radar,
        'course_score_distribution': course_score_distribution
    }), 200


@admin_bp.route('/analytics/hometowns', methods=['GET'])
@admin_required
def get_hometown_analytics():
    """Render hometown analytics page (for a separate visualization)"""
    hometown_counts = db.session.query(
        Student.hometown,
        func.count(Student.id)
    ).group_by(Student.hometown).order_by(func.count(Student.id).desc()).all()

    hometown_data = [{'name': h[0], 'value': h[1]} for h in hometown_counts if h[0]]
    
    return render_template('admin/hometown_analytics.html',
                           active_page='hometown_analytics',
                           hometown_data_json=jsonify(hometown_data).get_data(as_text=True))
