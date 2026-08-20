"""
学习管理API - 带Swagger文档
为主要的学习管理功能添加API文档
"""

from flask import Blueprint, request, jsonify
from flasgger import swag_from

learning_docs_bp = Blueprint('learning_docs', __name__)

@learning_docs_bp.route('/courses', methods=['GET'])
@swag_from({
    'tags': ['课程管理'],
    'summary': '获取课程列表',
    'description': '获取所有可用课程的分页列表，支持筛选和搜索',
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
        },
        {
            'name': 'search',
            'in': 'query',
            'type': 'string',
            'description': '搜索关键词'
        },
        {
            'name': 'category',
            'in': 'query',
            'type': 'string',
            'description': '课程分类'
        },
        {
            'name': 'difficulty',
            'in': 'query',
            'type': 'string',
            'enum': ['beginner', 'intermediate', 'advanced'],
            'description': '难度级别'
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
                    'page': {'type': 'integer'},
                    'per_page': {'type': 'integer'},
                    'pages': {'type': 'integer'}
                }
            }
        }
    }
})
def get_courses_docs():
    """获取课程列表"""
    return jsonify({
        "courses": [
            {
                "id": 1,
                "name": "Python编程基础",
                "description": "学习Python编程的基本概念和语法",
                "category": "计算机科学",
                "difficulty": "beginner",
                "is_public": True,
                "teacher_id": 2
            }
        ],
        "total": 1,
        "page": 1,
        "per_page": 10,
        "pages": 1
    })

@learning_docs_bp.route('/courses', methods=['POST'])
@swag_from({
    'tags': ['课程管理'],
    'summary': '创建新课程',
    'description': '创建一个新的课程（需要教师或管理员权限）',
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
                    'name': {
                        'type': 'string',
                        'description': '课程名称',
                        'example': 'Python高级编程'
                    },
                    'description': {
                        'type': 'string',
                        'description': '课程描述',
                        'example': '深入学习Python高级特性和应用'
                    },
                    'category': {
                        'type': 'string',
                        'description': '课程分类',
                        'example': '计算机科学'
                    },
                    'difficulty': {
                        'type': 'string',
                        'enum': ['beginner', 'intermediate', 'advanced'],
                        'description': '难度级别',
                        'example': 'intermediate'
                    },
                    'is_public': {
                        'type': 'boolean',
                        'description': '是否公开',
                        'default': True
                    }
                }
            }
        }
    ],
    'responses': {
        '201': {
            'description': '创建成功',
            'schema': {'$ref': '#/definitions/Course'}
        },
        '400': {'description': '请求参数错误'},
        '401': {'description': '未授权'},
        '403': {'description': '权限不足'}
    }
})
def create_course_docs():
    """创建新课程"""
    data = request.get_json()
    return jsonify({
        "id": 2,
        "name": data.get('name'),
        "description": data.get('description'),
        "category": data.get('category'),
        "difficulty": data.get('difficulty', 'beginner'),
        "is_public": data.get('is_public', True),
        "teacher_id": 1,
        "created_at": "2024-01-01T00:00:00"
    }), 201

@learning_docs_bp.route('/courses/<int:course_id>', methods=['GET'])
@swag_from({
    'tags': ['课程管理'],
    'summary': '获取课程详情',
    'description': '根据课程ID获取详细信息，包括材料和评估',
    'parameters': [
        {
            'name': 'course_id',
            'in': 'path',
            'type': 'integer',
            'required': True,
            'description': '课程ID'
        },
        {
            'name': 'include_materials',
            'in': 'query',
            'type': 'boolean',
            'default': False,
            'description': '是否包含材料列表'
        },
        {
            'name': 'include_assessments',
            'in': 'query',
            'type': 'boolean',
            'default': False,
            'description': '是否包含评估列表'
        }
    ],
    'responses': {
        '200': {
            'description': '获取成功',
            'schema': {
                'type': 'object',
                'properties': {
                    'course': {'$ref': '#/definitions/Course'},
                    'materials': {
                        'type': 'array',
                        'items': {'type': 'object'}
                    },
                    'assessments': {
                        'type': 'array',
                        'items': {'$ref': '#/definitions/Assessment'}
                    }
                }
            }
        },
        '404': {'description': '课程不存在'}
    }
})
def get_course_docs(course_id):
    """获取课程详情"""
    return jsonify({
        "course": {
            "id": course_id,
            "name": "Python编程基础",
            "description": "学习Python编程的基本概念和语法",
            "category": "计算机科学",
            "difficulty": "beginner"
        },
        "materials": [],
        "assessments": []
    })

@learning_docs_bp.route('/assessments', methods=['GET'])
@swag_from({
    'tags': ['评估系统'],
    'summary': '获取评估列表',
    'description': '获取用户可访问的评估列表',
    'security': [{'Bearer': []}],
    'parameters': [
        {
            'name': 'course_id',
            'in': 'query',
            'type': 'integer',
            'description': '课程ID筛选'
        },
        {
            'name': 'type',
            'in': 'query',
            'type': 'string',
            'enum': ['quiz', 'exam', 'assignment'],
            'description': '评估类型'
        },
        {
            'name': 'status',
            'in': 'query',
            'type': 'string',
            'enum': ['published', 'draft'],
            'description': '发布状态'
        }
    ],
    'responses': {
        '200': {
            'description': '获取成功',
            'schema': {
                'type': 'object',
                'properties': {
                    'assessments': {
                        'type': 'array',
                        'items': {'$ref': '#/definitions/Assessment'}
                    }
                }
            }
        }
    }
})
def get_assessments_docs():
    """获取评估列表"""
    return jsonify({
        "assessments": [
            {
                "id": 1,
                "title": "Python基础测验",
                "description": "测试Python基础知识掌握情况",
                "type": "quiz",
                "total_score": 100,
                "duration": 60,
                "is_published": True
            }
        ]
    })

@learning_docs_bp.route('/assessments', methods=['POST'])
@swag_from({
    'tags': ['评估系统'],
    'summary': '创建新评估',
    'description': '创建测验、考试或作业（需要教师权限）',
    'security': [{'Bearer': []}],
    'parameters': [
        {
            'name': 'body',
            'in': 'body',
            'required': True,
            'schema': {
                'type': 'object',
                'required': ['title', 'course_id', 'questions'],
                'properties': {
                    'title': {
                        'type': 'string',
                        'description': '评估标题',
                        'example': 'Python语法测验'
                    },
                    'description': {
                        'type': 'string',
                        'description': '评估描述',
                        'example': '测试Python基础语法知识'
                    },
                    'course_id': {
                        'type': 'integer',
                        'description': '所属课程ID',
                        'example': 1
                    },
                    'type': {
                        'type': 'string',
                        'enum': ['quiz', 'exam', 'assignment'],
                        'description': '评估类型',
                        'example': 'quiz'
                    },
                    'duration': {
                        'type': 'integer',
                        'description': '时长（分钟）',
                        'example': 60
                    },
                    'total_score': {
                        'type': 'number',
                        'description': '总分',
                        'example': 100
                    },
                    'questions': {
                        'type': 'string',
                        'description': 'JSON格式的题目数据',
                        'example': '[{"type":"choice","question":"Python是什么？","options":["编程语言","数据库","操作系统"],"answer":0}]'
                    }
                }
            }
        }
    ],
    'responses': {
        '201': {
            'description': '创建成功',
            'schema': {'$ref': '#/definitions/Assessment'}
        },
        '400': {'description': '请求参数错误'},
        '403': {'description': '权限不足'}
    }
})
def create_assessment_docs():
    """创建新评估"""
    data = request.get_json()
    return jsonify({
        "id": 2,
        "title": data.get('title'),
        "description": data.get('description'),
        "type": data.get('type', 'quiz'),
        "course_id": data.get('course_id'),
        "duration": data.get('duration'),
        "total_score": data.get('total_score', 100),
        "is_published": False,
        "created_at": "2024-01-01T00:00:00"
    }), 201

@learning_docs_bp.route('/materials/<int:material_id>', methods=['GET'])
@swag_from({
    'tags': ['课程管理'],
    'summary': '获取学习材料',
    'description': '获取指定材料的详细信息和内容',
    'parameters': [
        {
            'name': 'material_id',
            'in': 'path',
            'type': 'integer',
            'required': True,
            'description': '材料ID'
        }
    ],
    'responses': {
        '200': {
            'description': '获取成功',
            'schema': {
                'type': 'object',
                'properties': {
                    'id': {'type': 'integer'},
                    'title': {'type': 'string'},
                    'type': {'type': 'string', 'enum': ['pdf', 'video', 'document', 'link']},
                    'file_path': {'type': 'string'},
                    'content': {'type': 'string'},
                    'course_id': {'type': 'integer'},
                    'created_at': {'type': 'string', 'format': 'date-time'}
                }
            }
        },
        '404': {'description': '材料不存在'}
    }
})
def get_material_docs(material_id):
    """获取学习材料"""
    return jsonify({
        "id": material_id,
        "title": "Python基础教程",
        "type": "pdf",
        "file_path": "/uploads/materials/python_basics.pdf",
        "content": "Python编程基础内容...",
        "course_id": 1,
        "created_at": "2024-01-01T00:00:00"
    })



