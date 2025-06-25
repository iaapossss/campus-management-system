from flask import Flask, redirect, url_for
from .models import db
from .routes import auth, admin, teacher
from flask_jwt_extended import JWTManager
from datetime import timedelta

# ✅ 修正点: 从 app.config 导入 Config 类
from . import config # 导入 app 目录下的 config 模块

def create_app():
    app = Flask(__name__)
    # ✅ 修正点: 从 app.config 导入 Config 类
    app.config.from_object(config.Config) # 直接引用导入的 config 模块中的 Config 类

    db.init_app(app)

    jwt = JWTManager(app)

    app.register_blueprint(auth.auth_bp)
    app.register_blueprint(admin.admin_bp)
    app.register_blueprint(teacher.teacher_bp)

    @app.route('/')
    def index():
        return redirect(url_for('auth.login'))

    return app

