from app import create_app, db
from app.models import generate_mock_data, Course, User, Role # 确保导入 User 和 Role

app = create_app()

if __name__ == '__main__':
    with app.app_context():
        db.create_all()

        # 检查并创建初始管理员账号
        admin_username = 'admin'
        admin_password = 'admin_password_123' # !!! 务必在生产环境中更改此密码 !!!

        if not User.query.filter_by(username=admin_username, role=Role.ADMIN).first():
            admin_user = User(
                username=admin_username,
                role=Role.ADMIN
            )
            admin_user.set_password(admin_password)
            db.session.add(admin_user)
            db.session.commit()
            print(f"Created initial admin user: {admin_username} with password '{admin_password}'")
        else:
            print(f"Admin user '{admin_username}' already exists.")

        # 现有数据生成逻辑
        if not Course.query.first():
            # ✅ 修正这里：generate_mock_data 现在返回三个值 (num_students, num_courses, num_teachers)
            num_students, num_courses, num_teachers = generate_mock_data(app, db) # 解包所有三个返回值
            print(f"Generated {num_students} students, {num_courses} courses, and {num_teachers} teachers.")
        else:
            print("Mock data already exists.")
    app.run(debug=True)

