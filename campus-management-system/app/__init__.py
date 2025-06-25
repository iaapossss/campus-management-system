from flask import Flask
from .models import db
from .routes import auth, admin, teacher
from flask_jwt_extended import JWTManager # ✅ 导入 JWTManager

def create_app():
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'
    app.config['SECRET_KEY'] = 'your_secret_key'  # 请替换为更安全的密钥

    # ✅ JWT 配置（必须添加）
    # 请确保 JWT_SECRET_KEY 与您的认证模块中的密钥一致
    app.config['JWT_SECRET_KEY'] = 'your_jwt_secret_key'  # 请替换为安全值
    app.config['JWT_TOKEN_LOCATION'] = ['headers']  # JWT 将从 HTTP 请求头中获取
    app.config['JWT_HEADER_NAME'] = 'Authorization' # 默认头部名称
    app.config['JWT_HEADER_TYPE'] = 'Bearer'       # 默认头部类型，即 'Bearer <token>'

    # 初始化插件
    db.init_app(app)
    jwt = JWTManager(app)  # ✅ 初始化 JWTManager 实例

    # 注册蓝图
    app.register_blueprint(auth.auth_bp)
    app.register_blueprint(admin.admin_bp)
    app.register_blueprint(teacher.teacher_bp)

    return app
