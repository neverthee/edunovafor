"""
演示API - 带完整Swagger文档
用于演示Swagger文档功能
"""

from flask import Blueprint, request, jsonify
from flasgger import swag_from

demo_bp = Blueprint('demo', __name__)

@demo_bp.route('/demo/hello', methods=['GET'])
@swag_from({
    'tags': ['演示API'],
    'summary': '简单问候',
    'description': '返回简单的问候消息',
    'responses': {
        '200': {
            'description': '成功返回问候消息',
            'schema': {
                'type': 'object',
                'properties': {
                    'message': {
                        'type': 'string',
                        'example': 'Hello, EduNova!'
                    },
                    'timestamp': {
                        'type': 'string',
                        'format': 'date-time'
                    }
                }
            }
        }
    }
})
def hello():
    """简单问候接口"""
    from datetime import datetime
    return jsonify({
        'message': 'Hello, EduNova!',
        'timestamp': datetime.now().isoformat()
    })

@demo_bp.route('/demo/echo', methods=['POST'])
@swag_from({
    'tags': ['演示API'],
    'summary': '回声测试',
    'description': '返回发送的数据',
    'parameters': [
        {
            'name': 'body',
            'in': 'body',
            'required': True,
            'description': '要回声的数据',
            'schema': {
                'type': 'object',
                'properties': {
                    'message': {
                        'type': 'string',
                        'description': '消息内容',
                        'example': '这是一条测试消息'
                    },
                    'user': {
                        'type': 'string',
                        'description': '用户名',
                        'example': 'admin'
                    }
                }
            }
        }
    ],
    'responses': {
        '200': {
            'description': '成功返回回声数据',
            'schema': {
                'type': 'object',
                'properties': {
                    'echo': {
                        'type': 'object',
                        'description': '回声数据'
                    },
                    'received_at': {
                        'type': 'string',
                        'format': 'date-time'
                    }
                }
            }
        },
        '400': {
            'description': '请求数据格式错误',
            'schema': {
                'type': 'object',
                'properties': {
                    'error': {
                        'type': 'string',
                        'example': '请求体不能为空'
                    }
                }
            }
        }
    }
})
def echo():
    """回声测试接口"""
    from datetime import datetime
    
    data = request.get_json()
    
    if not data:
        return jsonify({'error': '请求体不能为空'}), 400
    
    return jsonify({
        'echo': data,
        'received_at': datetime.now().isoformat()
    })

@demo_bp.route('/demo/users/<int:user_id>', methods=['GET'])
@swag_from({
    'tags': ['演示API'],
    'summary': '获取用户信息',
    'description': '根据用户ID获取用户详细信息',
    'parameters': [
        {
            'name': 'user_id',
            'in': 'path',
            'type': 'integer',
            'required': True,
            'description': '用户ID',
            'example': 1
        },
        {
            'name': 'include_email',
            'in': 'query',
            'type': 'boolean',
            'default': False,
            'description': '是否包含邮箱信息'
        }
    ],
    'responses': {
        '200': {
            'description': '成功获取用户信息',
            'schema': {
                '$ref': '#/definitions/User'
            }
        },
        '404': {
            'description': '用户不存在',
            'schema': {
                'type': 'object',
                'properties': {
                    'error': {
                        'type': 'string',
                        'example': '用户不存在'
                    }
                }
            }
        }
    }
})
def get_user_demo(user_id):
    """获取用户信息演示接口"""
    include_email = request.args.get('include_email', 'false').lower() == 'true'
    
    if user_id > 100:  # 模拟用户不存在
        return jsonify({'error': '用户不存在'}), 404
    
    user_data = {
        'id': user_id,
        'username': f'user{user_id}',
        'full_name': f'用户{user_id}',
        'role': 'student',
        'is_active': True,
        'created_at': '2024-01-01T00:00:00',
        'updated_at': '2024-01-01T00:00:00'
    }
    
    if include_email:
        user_data['email'] = f'user{user_id}@example.com'
    
    return jsonify(user_data)

@demo_bp.route('/demo/courses', methods=['GET'])
@swag_from({
    'tags': ['演示API'],
    'summary': '获取课程列表',
    'description': '获取所有可用课程的分页列表',
    'parameters': [
        {
            'name': 'page',
            'in': 'query',
            'type': 'integer',
            'default': 1,
            'minimum': 1,
            'description': '页码'
        },
        {
            'name': 'per_page',
            'in': 'query',
            'type': 'integer',
            'default': 10,
            'minimum': 1,
            'maximum': 100,
            'description': '每页课程数量'
        },
        {
            'name': 'difficulty',
            'in': 'query',
            'type': 'string',
            'enum': ['beginner', 'intermediate', 'advanced'],
            'description': '难度筛选'
        }
    ],
    'responses': {
        '200': {
            'description': '成功获取课程列表',
            'schema': {
                'type': 'object',
                'properties': {
                    'courses': {
                        'type': 'array',
                        'items': {
                            '$ref': '#/definitions/Course'
                        }
                    },
                    'pagination': {
                        'type': 'object',
                        'properties': {
                            'page': {'type': 'integer'},
                            'per_page': {'type': 'integer'},
                            'total': {'type': 'integer'},
                            'pages': {'type': 'integer'}
                        }
                    }
                }
            }
        }
    }
})
def get_courses_demo():
    """获取课程列表演示接口"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    difficulty = request.args.get('difficulty')
    
    # 模拟课程数据
    all_courses = [
        {
            'id': 1,
            'name': 'Python编程基础',
            'description': '学习Python编程的基本概念和语法',
            'category': '计算机科学',
            'difficulty': 'beginner',
            'is_public': True,
            'teacher_id': 2,
            'created_at': '2024-01-01T00:00:00'
        },
        {
            'id': 2,
            'name': '数据结构与算法',
            'description': '掌握常见数据结构和算法',
            'category': '计算机科学',
            'difficulty': 'intermediate',
            'is_public': True,
            'teacher_id': 2,
            'created_at': '2024-01-02T00:00:00'
        },
        {
            'id': 3,
            'name': '机器学习入门',
            'description': '了解机器学习的基本原理和应用',
            'category': '人工智能',
            'difficulty': 'advanced',
            'is_public': True,
            'teacher_id': 2,
            'created_at': '2024-01-03T00:00:00'
        }
    ]
    
    # 按难度筛选
    if difficulty:
        courses = [c for c in all_courses if c['difficulty'] == difficulty]
    else:
        courses = all_courses
    
    # 分页
    total = len(courses)
    start = (page - 1) * per_page
    end = start + per_page
    courses_page = courses[start:end]
    
    return jsonify({
        'courses': courses_page,
        'pagination': {
            'page': page,
            'per_page': per_page,
            'total': total,
            'pages': (total + per_page - 1) // per_page
        }
    })



