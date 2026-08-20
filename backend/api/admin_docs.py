"""
管理员API - 带Swagger文档
为系统管理功能添加API文档
"""

from flask import Blueprint, request, jsonify
from flasgger import swag_from

admin_docs_bp = Blueprint('admin_docs', __name__)

@admin_docs_bp.route('/users', methods=['GET'])
@swag_from({
    'tags': ['管理员'],
    'summary': '获取用户列表',
    'description': '获取系统中所有用户的分页列表（需要管理员权限）',
    'security': [{'Bearer': []}],
    'parameters': [
        {
            'name': 'page',
            'in': 'query',
            'type': 'integer',
            'default': 1,
            'description': '页码'
        },
        {
            'name': 'per_page',
            'in': 'query',
            'type': 'integer',
            'default': 20,
            'description': '每页数量'
        },
        {
            'name': 'role',
            'in': 'query',
            'type': 'string',
            'enum': ['admin', 'teacher', 'student'],
            'description': '用户角色筛选'
        },
        {
            'name': 'status',
            'in': 'query',
            'type': 'string',
            'enum': ['active', 'inactive'],
            'description': '用户状态筛选'
        },
        {
            'name': 'search',
            'in': 'query',
            'type': 'string',
            'description': '搜索用户名或邮箱'
        }
    ],
    'responses': {
        '200': {
            'description': '获取成功',
            'schema': {
                'type': 'object',
                'properties': {
                    'users': {
                        'type': 'array',
                        'items': {'$ref': '#/definitions/User'}
                    },
                    'pagination': {
                        'type': 'object',
                        'properties': {
                            'total': {'type': 'integer'},
                            'page': {'type': 'integer'},
                            'per_page': {'type': 'integer'},
                            'pages': {'type': 'integer'}
                        }
                    }
                }
            }
        },
        '403': {'description': '权限不足'}
    }
})
def get_users_admin_docs():
    """获取用户列表（管理员）"""
    return jsonify({
        "users": [
            {
                "id": 1,
                "username": "admin",
                "email": "admin@example.com",
                "full_name": "系统管理员",
                "role": "admin",
                "is_active": True,
                "created_at": "2024-01-01T00:00:00"
            },
            {
                "id": 2,
                "username": "teacher1",
                "email": "teacher@example.com",
                "full_name": "张老师",
                "role": "teacher",
                "is_active": True,
                "created_at": "2024-01-02T00:00:00"
            }
        ],
        "pagination": {
            "total": 2,
            "page": 1,
            "per_page": 20,
            "pages": 1
        }
    })

@admin_docs_bp.route('/users', methods=['POST'])
@swag_from({
    'tags': ['管理员'],
    'summary': '创建新用户',
    'description': '管理员创建新用户账户',
    'security': [{'Bearer': []}],
    'parameters': [
        {
            'name': 'body',
            'in': 'body',
            'required': True,
            'schema': {
                'type': 'object',
                'required': ['username', 'email', 'password', 'full_name', 'role'],
                'properties': {
                    'username': {
                        'type': 'string',
                        'description': '用户名（唯一）',
                        'example': 'newteacher'
                    },
                    'email': {
                        'type': 'string',
                        'format': 'email',
                        'description': '邮箱地址',
                        'example': 'newteacher@example.com'
                    },
                    'password': {
                        'type': 'string',
                        'minLength': 6,
                        'description': '密码',
                        'example': 'password123'
                    },
                    'full_name': {
                        'type': 'string',
                        'description': '全名',
                        'example': '李老师'
                    },
                    'role': {
                        'type': 'string',
                        'enum': ['admin', 'teacher', 'student'],
                        'description': '用户角色',
                        'example': 'teacher'
                    },
                    'is_active': {
                        'type': 'boolean',
                        'description': '是否激活',
                        'default': True
                    }
                }
            }
        }
    ],
    'responses': {
        '201': {
            'description': '创建成功',
            'schema': {'$ref': '#/definitions/User'}
        },
        '400': {'description': '请求参数错误'},
        '409': {'description': '用户名或邮箱已存在'},
        '403': {'description': '权限不足'}
    }
})
def create_user_admin_docs():
    """创建新用户（管理员）"""
    data = request.get_json()
    return jsonify({
        "id": 3,
        "username": data.get('username'),
        "email": data.get('email'),
        "full_name": data.get('full_name'),
        "role": data.get('role'),
        "is_active": data.get('is_active', True),
        "created_at": "2024-01-01T00:00:00"
    }), 201

@admin_docs_bp.route('/users/<int:user_id>', methods=['PUT'])
@swag_from({
    'tags': ['管理员'],
    'summary': '更新用户信息',
    'description': '管理员更新指定用户的信息',
    'security': [{'Bearer': []}],
    'parameters': [
        {
            'name': 'user_id',
            'in': 'path',
            'type': 'integer',
            'required': True,
            'description': '用户ID'
        },
        {
            'name': 'body',
            'in': 'body',
            'required': True,
            'schema': {
                'type': 'object',
                'properties': {
                    'username': {'type': 'string'},
                    'email': {'type': 'string', 'format': 'email'},
                    'full_name': {'type': 'string'},
                    'role': {
                        'type': 'string',
                        'enum': ['admin', 'teacher', 'student']
                    },
                    'is_active': {'type': 'boolean'},
                    'password': {
                        'type': 'string',
                        'description': '新密码（可选）'
                    }
                }
            }
        }
    ],
    'responses': {
        '200': {
            'description': '更新成功',
            'schema': {'$ref': '#/definitions/User'}
        },
        '400': {'description': '请求参数错误'},
        '404': {'description': '用户不存在'},
        '403': {'description': '权限不足'}
    }
})
def update_user_admin_docs(user_id):
    """更新用户信息（管理员）"""
    data = request.get_json()
    return jsonify({
        "id": user_id,
        "username": data.get('username', 'updated_user'),
        "email": data.get('email', 'updated@example.com'),
        "full_name": data.get('full_name', '更新用户'),
        "role": data.get('role', 'student'),
        "is_active": data.get('is_active', True),
        "updated_at": "2024-01-01T12:00:00"
    })

@admin_docs_bp.route('/users/<int:user_id>', methods=['DELETE'])
@swag_from({
    'tags': ['管理员'],
    'summary': '删除用户',
    'description': '管理员删除指定用户（软删除）',
    'security': [{'Bearer': []}],
    'parameters': [
        {
            'name': 'user_id',
            'in': 'path',
            'type': 'integer',
            'required': True,
            'description': '用户ID'
        }
    ],
    'responses': {
        '200': {
            'description': '删除成功',
            'schema': {
                'type': 'object',
                'properties': {
                    'message': {
                        'type': 'string',
                        'example': '用户已成功删除'
                    }
                }
            }
        },
        '404': {'description': '用户不存在'},
        '403': {'description': '权限不足'},
        '400': {'description': '不能删除自己或其他管理员'}
    }
})
def delete_user_admin_docs(user_id):
    """删除用户（管理员）"""
    return jsonify({
        "message": "用户已成功删除"
    })

@admin_docs_bp.route('/stats', methods=['GET'])
@swag_from({
    'tags': ['管理员'],
    'summary': '获取系统统计',
    'description': '获取系统整体统计数据和运行状态',
    'security': [{'Bearer': []}],
    'responses': {
        '200': {
            'description': '获取成功',
            'schema': {
                'type': 'object',
                'properties': {
                    'users': {
                        'type': 'object',
                        'properties': {
                            'total': {'type': 'integer'},
                            'active': {'type': 'integer'},
                            'students': {'type': 'integer'},
                            'teachers': {'type': 'integer'},
                            'admins': {'type': 'integer'}
                        }
                    },
                    'courses': {
                        'type': 'object',
                        'properties': {
                            'total': {'type': 'integer'},
                            'public': {'type': 'integer'},
                            'private': {'type': 'integer'}
                        }
                    },
                    'assessments': {
                        'type': 'object',
                        'properties': {
                            'total': {'type': 'integer'},
                            'published': {'type': 'integer'},
                            'completed_submissions': {'type': 'integer'}
                        }
                    },
                    'system': {
                        'type': 'object',
                        'properties': {
                            'uptime': {'type': 'string'},
                            'version': {'type': 'string'},
                            'storage_used': {'type': 'string'},
                            'ai_requests_today': {'type': 'integer'}
                        }
                    }
                }
            }
        },
        '403': {'description': '权限不足'}
    }
})
def get_stats_admin_docs():
    """获取系统统计"""
    return jsonify({
        "users": {
            "total": 1250,
            "active": 1180,
            "students": 1100,
            "teachers": 45,
            "admins": 5
        },
        "courses": {
            "total": 68,
            "public": 52,
            "private": 16
        },
        "assessments": {
            "total": 234,
            "published": 198,
            "completed_submissions": 5420
        },
        "system": {
            "uptime": "15天 8小时 32分钟",
            "version": "1.0.0",
            "storage_used": "12.5 GB",
            "ai_requests_today": 1456
        }
    })

@admin_docs_bp.route('/config', methods=['GET'])
@swag_from({
    'tags': ['管理员'],
    'summary': '获取系统配置',
    'description': '获取当前系统配置信息',
    'security': [{'Bearer': []}],
    'responses': {
        '200': {
            'description': '获取成功',
            'schema': {
                'type': 'object',
                'properties': {
                    'app_name': {'type': 'string'},
                    'max_file_size': {'type': 'string'},
                    'supported_formats': {
                        'type': 'array',
                        'items': {'type': 'string'}
                    },
                    'ai_features': {
                        'type': 'object',
                        'properties': {
                            'rag_enabled': {'type': 'boolean'},
                            'auto_grading': {'type': 'boolean'},
                            'lesson_generation': {'type': 'boolean'}
                        }
                    },
                    'security': {
                        'type': 'object',
                        'properties': {
                            'jwt_expiry': {'type': 'string'},
                            'password_policy': {'type': 'object'}
                        }
                    }
                }
            }
        },
        '403': {'description': '权限不足'}
    }
})
def get_config_admin_docs():
    """获取系统配置"""
    return jsonify({
        "app_name": "EduNova智能教学系统",
        "max_file_size": "200MB",
        "supported_formats": ["pdf", "docx", "doc", "txt", "md"],
        "ai_features": {
            "rag_enabled": True,
            "auto_grading": True,
            "lesson_generation": True
        },
        "security": {
            "jwt_expiry": "1小时",
            "password_policy": {
                "min_length": 6,
                "require_special_chars": False
            }
        }
    })

@admin_docs_bp.route('/config', methods=['PUT'])
@swag_from({
    'tags': ['管理员'],
    'summary': '更新系统配置',
    'description': '更新系统配置参数',
    'security': [{'Bearer': []}],
    'parameters': [
        {
            'name': 'body',
            'in': 'body',
            'required': True,
            'schema': {
                'type': 'object',
                'properties': {
                    'max_file_size': {'type': 'integer', 'description': '最大文件大小（MB）'},
                    'ai_features': {
                        'type': 'object',
                        'properties': {
                            'rag_enabled': {'type': 'boolean'},
                            'auto_grading': {'type': 'boolean'},
                            'lesson_generation': {'type': 'boolean'}
                        }
                    },
                    'maintenance_mode': {'type': 'boolean'},
                    'registration_enabled': {'type': 'boolean'}
                }
            }
        }
    ],
    'responses': {
        '200': {
            'description': '更新成功',
            'schema': {
                'type': 'object',
                'properties': {
                    'message': {'type': 'string'},
                    'updated_fields': {
                        'type': 'array',
                        'items': {'type': 'string'}
                    }
                }
            }
        },
        '400': {'description': '配置参数错误'},
        '403': {'description': '权限不足'}
    }
})
def update_config_admin_docs():
    """更新系统配置"""
    data = request.get_json()
    return jsonify({
        "message": "系统配置已更新",
        "updated_fields": list(data.keys())
    })



