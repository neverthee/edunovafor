"""
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
