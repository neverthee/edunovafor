"""
认证API - 添加了简单Swagger文档
"""

from flask import Blueprint, request, jsonify
from flasgger import swag_from
from backend.api.auth import *  # 导入原有的认证逻辑

auth_simple_bp = Blueprint('auth_simple', __name__)

@auth_simple_bp.route('/login', methods=['POST'])
@swag_from({
    'tags': ['认证'],
    'summary': '用户登录',
    'description': '用户通过用户名和密码登录系统',
    'parameters': [
        {
            'name': 'body',
            'in': 'body',
            'required': True,
            'schema': {
                'type': 'object',
                'required': ['username', 'password'],
                'properties': {
                    'username': {'type': 'string', 'example': 'admin'},
                    'password': {'type': 'string', 'example': 'admin123'}
                }
            }
        }
    ],
    'responses': {
        '200': {
            'description': '登录成功',
            'schema': {
                'type': 'object',
                'properties': {
                    'access_token': {'type': 'string'},
                    'user': {'$ref': '#/definitions/User'}
                }
            }
        },
        '401': {'description': '认证失败'}
    }
})
def login_simple():
    """用户登录"""
    # 这里直接调用原有的登录逻辑
    from backend.api.auth import auth_bp
    # 或者重新实现登录逻辑
    data = request.get_json()
    
    if not data:
        return jsonify({"error": "请提供登录信息"}), 400
    
    username = data.get('username')
    password = data.get('password')
    
    if not username or not password:
        return jsonify({"error": "用户名和密码不能为空"}), 400
    
    # 这里应该是实际的认证逻辑
    return jsonify({
        "message": "登录成功",
        "access_token": "示例token",
        "user": {"id": 1, "username": username, "role": "admin"}
    })

@auth_simple_bp.route('/register', methods=['POST'])
@swag_from({
    'tags': ['认证'],
    'summary': '用户注册',
    'description': '新用户注册账户',
    'parameters': [
        {
            'name': 'body',
            'in': 'body',
            'required': True,
            'schema': {
                'type': 'object',
                'required': ['username', 'email', 'password', 'full_name'],
                'properties': {
                    'username': {'type': 'string', 'example': 'newuser'},
                    'email': {'type': 'string', 'example': 'user@example.com'},
                    'password': {'type': 'string', 'example': 'password123'},
                    'full_name': {'type': 'string', 'example': '张三'},
                    'role': {'type': 'string', 'enum': ['student', 'teacher'], 'default': 'student'}
                }
            }
        }
    ],
    'responses': {
        '201': {
            'description': '注册成功',
            'schema': {
                'type': 'object',
                'properties': {
                    'message': {'type': 'string'},
                    'user': {'$ref': '#/definitions/User'}
                }
            }
        }
    }
})
def register_simple():
    """用户注册"""
    data = request.get_json()
    
    if not data:
        return jsonify({"error": "请提供注册信息"}), 400
    
    return jsonify({
        "message": "注册成功",
        "user": {
            "id": 2,
            "username": data.get('username'),
            "email": data.get('email'),
            "role": data.get('role', 'student')
        }
    }), 201

@auth_simple_bp.route('/profile', methods=['GET'])
@swag_from({
    'tags': ['认证'],
    'summary': '获取用户资料',
    'description': '获取当前登录用户的详细资料',
    'security': [{'Bearer': []}],
    'responses': {
        '200': {
            'description': '获取成功',
            'schema': {'$ref': '#/definitions/User'}
        }
    }
})
def get_profile_simple():
    """获取用户资料"""
    return jsonify({
        "id": 1,
        "username": "admin",
        "email": "admin@example.com",
        "full_name": "系统管理员",
        "role": "admin"
    })
