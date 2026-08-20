"""
认证API - 带完整文档的示例
这是如何为现有API添加Swagger文档的示例
"""

from flask import Blueprint, request, jsonify
from flasgger import swag_from
from backend.docs_config import add_common_responses

auth_documented_bp = Blueprint('auth_documented', __name__)

@auth_documented_bp.route('/login', methods=['POST'])
@swag_from({
    'tags': ['认证'],
    'summary': '用户登录',
    'description': '用户通过用户名和密码登录系统',
    'parameters': [
        {
            'name': 'body',
            'in': 'body',
            'required': True,
            'description': '登录信息',
            'schema': {
                'type': 'object',
                'required': ['username', 'password'],
                'properties': {
                    'username': {
                        'type': 'string',
                        'description': '用户名',
                        'example': 'admin'
                    },
                    'password': {
                        'type': 'string',
                        'description': '密码',
                        'example': 'admin123'
                    }
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
                    'message': {
                        'type': 'string',
                        'example': '登录成功'
                    },
                    'access_token': {
                        'type': 'string',
                        'description': 'JWT访问令牌',
                        'example': 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...'
                    },
                    'refresh_token': {
                        'type': 'string', 
                        'description': 'JWT刷新令牌',
                        'example': 'eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9...'
                    },
                    'user': {
                        '$ref': '#/definitions/User'
                    }
                }
            }
        },
        **add_common_responses()
    }
})
def login_documented():
    """用户登录接口 - 文档化版本"""
    data = request.get_json()
    
    if not data:
        return jsonify({"error": "请提供登录信息"}), 400
    
    username = data.get('username')
    password = data.get('password')
    
    if not username or not password:
        return jsonify({"error": "用户名和密码不能为空"}), 400
    
    # 这里是实际的登录逻辑
    # ...
    
    return jsonify({
        "message": "登录成功",
        "access_token": "示例token",
        "user": {
            "id": 1,
            "username": username,
            "role": "admin"
        }
    })


@auth_documented_bp.route('/register', methods=['POST'])
@swag_from({
    'tags': ['认证'],
    'summary': '用户注册',
    'description': '新用户注册账户',
    'parameters': [
        {
            'name': 'body',
            'in': 'body',
            'required': True,
            'description': '注册信息',
            'schema': {
                'type': 'object',
                'required': ['username', 'email', 'password', 'full_name'],
                'properties': {
                    'username': {
                        'type': 'string',
                        'description': '用户名（唯一）',
                        'example': 'newuser'
                    },
                    'email': {
                        'type': 'string',
                        'format': 'email',
                        'description': '邮箱地址',
                        'example': 'user@example.com'
                    },
                    'password': {
                        'type': 'string',
                        'minLength': 6,
                        'description': '密码（至少6位）',
                        'example': 'password123'
                    },
                    'full_name': {
                        'type': 'string',
                        'description': '全名',
                        'example': '张三'
                    },
                    'role': {
                        'type': 'string',
                        'enum': ['student', 'teacher'],
                        'default': 'student',
                        'description': '用户角色'
                    }
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
                    'message': {
                        'type': 'string',
                        'example': '注册成功'
                    },
                    'user': {
                        '$ref': '#/definitions/User'
                    }
                }
            }
        },
        '409': {
            'description': '用户名或邮箱已存在',
            'schema': {
                'type': 'object',
                'properties': {
                    'error': {
                        'type': 'string',
                        'example': '用户名已存在'
                    }
                }
            }
        },
        **add_common_responses()
    }
})
def register_documented():
    """用户注册接口 - 文档化版本"""
    data = request.get_json()
    
    if not data:
        return jsonify({"error": "请提供注册信息"}), 400
    
    # 验证必填字段
    required_fields = ['username', 'email', 'password', 'full_name']
    for field in required_fields:
        if not data.get(field):
            return jsonify({"error": f"{field}不能为空"}), 400
    
    # 这里是实际的注册逻辑
    # ...
    
    return jsonify({
        "message": "注册成功",
        "user": {
            "id": 2,
            "username": data.get('username'),
            "email": data.get('email'),
            "full_name": data.get('full_name'),
            "role": data.get('role', 'student')
        }
    }), 201


@auth_documented_bp.route('/profile', methods=['GET'])
@swag_from({
    'tags': ['认证'],
    'summary': '获取用户资料',
    'description': '获取当前登录用户的详细资料',
    'security': [{'Bearer': []}],
    'responses': {
        '200': {
            'description': '获取成功',
            'schema': {
                'type': 'object',
                'properties': {
                    'user': {
                        '$ref': '#/definitions/User'
                    }
                }
            }
        },
        **add_common_responses()
    }
})
def get_profile_documented():
    """获取用户资料接口 - 文档化版本"""
    # 这里需要JWT验证逻辑
    # ...
    
    return jsonify({
        "user": {
            "id": 1,
            "username": "admin",
            "email": "admin@example.com",
            "full_name": "系统管理员",
            "role": "admin",
            "is_active": True
        }
    })



