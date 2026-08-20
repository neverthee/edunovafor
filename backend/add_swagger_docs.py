#!/usr/bin/env python3
"""
为现有API路由批量添加Swagger文档的工具
"""

import os
import re
import ast
from typing import Dict, List, Any

class SwaggerDocAdder:
    """Swagger文档添加器"""
    
    def __init__(self):
        self.method_tags = {
            'auth.py': '认证',
            'user.py': '用户管理', 
            'admin.py': '管理员',
            'learning.py': '课程管理',
            'rag_ai.py': 'AI助手',
            'student_quiz.py': '评估系统'
        }
    
    def generate_simple_docs_for_auth(self):
        """为认证模块生成简单的文档"""
        auth_file = "api/auth_simple_docs.py"
        
        content = '''"""
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
'''
        
        with open(auth_file, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"✅ 已生成简单文档版本: {auth_file}")
        return auth_file
    
    def generate_course_docs(self):
        """为课程管理生成文档"""
        course_file = "api/course_simple_docs.py"
        
        content = '''"""
课程管理API - 添加了简单Swagger文档
"""

from flask import Blueprint, request, jsonify
from flasgger import swag_from

course_simple_bp = Blueprint('course_simple', __name__)

@course_simple_bp.route('/courses', methods=['GET'])
@swag_from({
    'tags': ['课程管理'],
    'summary': '获取课程列表',
    'description': '获取所有可用课程的列表',
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
            'default': 10,
            'description': '每页数量'
        }
    ],
    'responses': {
        '200': {
            'description': '获取成功',
            'schema': {
                'type': 'object',
                'properties': {
                    'courses': {
                        'type': 'array',
                        'items': {'$ref': '#/definitions/Course'}
                    },
                    'total': {'type': 'integer'},
                    'page': {'type': 'integer'}
                }
            }
        }
    }
})
def get_courses_simple():
    """获取课程列表"""
    return jsonify({
        "courses": [
            {
                "id": 1,
                "name": "Python编程基础",
                "description": "学习Python编程的基本概念和语法",
                "difficulty": "beginner"
            }
        ],
        "total": 1,
        "page": 1
    })

@course_simple_bp.route('/courses', methods=['POST'])
@swag_from({
    'tags': ['课程管理'],
    'summary': '创建新课程',
    'description': '创建一个新的课程',
    'security': [{'Bearer': []}],
    'parameters': [
        {
            'name': 'body',
            'in': 'body',
            'required': True,
            'schema': {
                'type': 'object',
                'required': ['name', 'description'],
                'properties': {
                    'name': {'type': 'string', 'example': 'Python高级编程'},
                    'description': {'type': 'string', 'example': '深入学习Python高级特性'},
                    'category': {'type': 'string', 'example': '计算机科学'},
                    'difficulty': {'type': 'string', 'enum': ['beginner', 'intermediate', 'advanced']}
                }
            }
        }
    ],
    'responses': {
        '201': {
            'description': '创建成功',
            'schema': {'$ref': '#/definitions/Course'}
        }
    }
})
def create_course_simple():
    """创建新课程"""
    data = request.get_json()
    
    return jsonify({
        "id": 2,
        "name": data.get('name'),
        "description": data.get('description'),
        "difficulty": data.get('difficulty', 'beginner')
    }), 201

@course_simple_bp.route('/courses/<int:course_id>', methods=['GET'])
@swag_from({
    'tags': ['课程管理'],
    'summary': '获取课程详情',
    'description': '根据课程ID获取详细信息',
    'parameters': [
        {
            'name': 'course_id',
            'in': 'path',
            'type': 'integer',
            'required': True,
            'description': '课程ID'
        }
    ],
    'responses': {
        '200': {
            'description': '获取成功',
            'schema': {'$ref': '#/definitions/Course'}
        },
        '404': {'description': '课程不存在'}
    }
})
def get_course_simple(course_id):
    """获取课程详情"""
    return jsonify({
        "id": course_id,
        "name": "示例课程",
        "description": "这是一个示例课程",
        "difficulty": "beginner"
    })
'''
        
        with open(course_file, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print(f"✅ 已生成课程文档版本: {course_file}")
        return course_file

def main():
    """主函数"""
    print("🚀 开始生成简单的API文档...")
    
    adder = SwaggerDocAdder()
    
    # 生成认证API文档
    auth_file = adder.generate_simple_docs_for_auth()
    
    # 生成课程API文档
    course_file = adder.generate_course_docs()
    
    print("\n📝 生成的文档文件:")
    print(f"  - {auth_file}")
    print(f"  - {course_file}")
    
    print("\n🔧 下一步:")
    print("1. 在 main.py 中注册新的蓝图")
    print("2. 重启Flask应用")
    print("3. 访问 http://localhost:5001/docs/ 查看文档")
    
    print("\n💡 注册蓝图的代码:")
    print("```python")
    print("from backend.api.auth_simple_docs import auth_simple_bp")
    print("from backend.api.course_simple_docs import course_simple_bp")
    print("app.register_blueprint(auth_simple_bp, url_prefix='/api/auth_simple')")
    print("app.register_blueprint(course_simple_bp, url_prefix='/api')")
    print("```")

if __name__ == "__main__":
    main()
