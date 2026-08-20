"""
RAG AI助手API - 带Swagger文档
为AI助手和RAG功能添加API文档
"""

from flask import Blueprint, request, jsonify
from flasgger import swag_from

rag_docs_bp = Blueprint('rag_docs', __name__)

@rag_docs_bp.route('/chat', methods=['POST'])
@swag_from({
    'tags': ['AI助手'],
    'summary': 'AI智能问答',
    'description': '基于RAG的智能问答，结合课程材料回答用户问题',
    'security': [{'Bearer': []}],
    'parameters': [
        {
            'name': 'body',
            'in': 'body',
            'required': True,
            'schema': {
                'type': 'object',
                'required': ['message'],
                'properties': {
                    'message': {
                        'type': 'string',
                        'description': '用户问题',
                        'example': 'Python中的列表和元组有什么区别？'
                    },
                    'course_id': {
                        'type': 'integer',
                        'description': '课程ID（限制在特定课程内搜索）',
                        'example': 1
                    },
                    'conversation_id': {
                        'type': 'string',
                        'description': '会话ID（用于上下文理解）',
                        'example': 'conv_123456'
                    },
                    'temperature': {
                        'type': 'number',
                        'minimum': 0,
                        'maximum': 1,
                        'description': 'AI回答的创造性（0-1）',
                        'default': 0.7
                    }
                }
            }
        }
    ],
    'responses': {
        '200': {
            'description': 'AI回答成功',
            'schema': {
                'type': 'object',
                'properties': {
                    'response': {
                        'type': 'string',
                        'description': 'AI回答内容'
                    },
                    'sources': {
                        'type': 'array',
                        'items': {
                            'type': 'object',
                            'properties': {
                                'title': {'type': 'string'},
                                'content': {'type': 'string'},
                                'confidence': {'type': 'number'}
                            }
                        },
                        'description': '回答依据的资料来源'
                    },
                    'conversation_id': {
                        'type': 'string',
                        'description': '会话ID'
                    },
                    'timestamp': {
                        'type': 'string',
                        'format': 'date-time'
                    }
                }
            }
        },
        '400': {'description': '请求参数错误'},
        '401': {'description': '未授权'},
        '500': {'description': 'AI服务不可用'}
    }
})
def chat_with_ai_docs():
    """AI智能问答"""
    data = request.get_json()
    message = data.get('message')
    
    return jsonify({
        "response": f"关于'{message}'的问题，列表（list）是可变的数据结构，可以修改其内容；而元组（tuple）是不可变的，创建后无法修改。列表使用方括号[]，元组使用圆括号()。",
        "sources": [
            {
                "title": "Python数据结构教程",
                "content": "列表和元组的基本概念...",
                "confidence": 0.92
            }
        ],
        "conversation_id": "conv_123456",
        "timestamp": "2024-01-01T12:00:00Z"
    })

@rag_docs_bp.route('/knowledge/add', methods=['POST'])
@swag_from({
    'tags': ['AI助手'],
    'summary': '添加知识库文档',
    'description': '上传文档到知识库，支持PDF、Word、Markdown等格式',
    'security': [{'Bearer': []}],
    'consumes': ['multipart/form-data'],
    'parameters': [
        {
            'name': 'file',
            'in': 'formData',
            'type': 'file',
            'required': True,
            'description': '要上传的文档文件'
        },
        {
            'name': 'course_id',
            'in': 'formData',
            'type': 'integer',
            'required': True,
            'description': '所属课程ID'
        },
        {
            'name': 'title',
            'in': 'formData',
            'type': 'string',
            'description': '文档标题（可选，默认使用文件名）'
        },
        {
            'name': 'description',
            'in': 'formData',
            'type': 'string',
            'description': '文档描述'
        },
        {
            'name': 'process_immediately',
            'in': 'formData',
            'type': 'boolean',
            'default': False,
            'description': '是否立即处理（否则加入队列）'
        }
    ],
    'responses': {
        '200': {
            'description': '上传成功',
            'schema': {
                'type': 'object',
                'properties': {
                    'message': {'type': 'string'},
                    'file_id': {'type': 'string'},
                    'status': {
                        'type': 'string',
                        'enum': ['uploaded', 'processing', 'completed']
                    },
                    'queue_position': {'type': 'integer'},
                    'estimated_time': {'type': 'string'}
                }
            }
        },
        '400': {'description': '文件格式不支持或参数错误'},
        '413': {'description': '文件太大'},
        '403': {'description': '权限不足'}
    }
})
def add_knowledge_docs():
    """添加知识库文档"""
    return jsonify({
        "message": "文档上传成功，已加入处理队列",
        "file_id": "doc_123456",
        "status": "processing",
        "queue_position": 2,
        "estimated_time": "约5分钟"
    })

@rag_docs_bp.route('/knowledge/status', methods=['GET'])
@swag_from({
    'tags': ['AI助手'],
    'summary': '获取知识库状态',
    'description': '查看知识库处理状态和统计信息',
    'security': [{'Bearer': []}],
    'parameters': [
        {
            'name': 'course_id',
            'in': 'query',
            'type': 'integer',
            'description': '课程ID（查看特定课程的知识库状态）'
        }
    ],
    'responses': {
        '200': {
            'description': '获取成功',
            'schema': {
                'type': 'object',
                'properties': {
                    'total_documents': {'type': 'integer'},
                    'processed_documents': {'type': 'integer'},
                    'processing_queue': {'type': 'integer'},
                    'failed_documents': {'type': 'integer'},
                    'last_update': {'type': 'string', 'format': 'date-time'},
                    'storage_size': {'type': 'string'},
                    'supported_formats': {
                        'type': 'array',
                        'items': {'type': 'string'}
                    }
                }
            }
        }
    }
})
def get_knowledge_status_docs():
    """获取知识库状态"""
    return jsonify({
        "total_documents": 156,
        "processed_documents": 142,
        "processing_queue": 3,
        "failed_documents": 2,
        "last_update": "2024-01-01T12:00:00Z",
        "storage_size": "2.3 GB",
        "supported_formats": ["pdf", "docx", "doc", "txt", "md"]
    })

@rag_docs_bp.route('/generate-lesson-plan', methods=['POST'])
@swag_from({
    'tags': ['AI助手'],
    'summary': 'AI生成教案',
    'description': '基于课程内容自动生成教案和课程规划',
    'security': [{'Bearer': []}],
    'parameters': [
        {
            'name': 'body',
            'in': 'body',
            'required': True,
            'schema': {
                'type': 'object',
                'required': ['course_id', 'topic'],
                'properties': {
                    'course_id': {
                        'type': 'integer',
                        'description': '课程ID',
                        'example': 1
                    },
                    'topic': {
                        'type': 'string',
                        'description': '教案主题',
                        'example': 'Python函数和模块'
                    },
                    'duration': {
                        'type': 'integer',
                        'description': '课程时长（分钟）',
                        'example': 90,
                        'default': 60
                    },
                    'difficulty': {
                        'type': 'string',
                        'enum': ['beginner', 'intermediate', 'advanced'],
                        'description': '难度级别',
                        'example': 'intermediate'
                    },
                    'learning_objectives': {
                        'type': 'array',
                        'items': {'type': 'string'},
                        'description': '学习目标',
                        'example': ['理解函数的概念', '掌握模块的使用']
                    },
                    'include_exercises': {
                        'type': 'boolean',
                        'description': '是否包含练习题',
                        'default': True
                    }
                }
            }
        }
    ],
    'responses': {
        '200': {
            'description': '教案生成成功',
            'schema': {
                'type': 'object',
                'properties': {
                    'lesson_plan': {
                        'type': 'object',
                        'properties': {
                            'title': {'type': 'string'},
                            'duration': {'type': 'integer'},
                            'objectives': {
                                'type': 'array',
                                'items': {'type': 'string'}
                            },
                            'outline': {
                                'type': 'array',
                                'items': {
                                    'type': 'object',
                                    'properties': {
                                        'section': {'type': 'string'},
                                        'time': {'type': 'integer'},
                                        'content': {'type': 'string'},
                                        'activities': {
                                            'type': 'array',
                                            'items': {'type': 'string'}
                                        }
                                    }
                                }
                            },
                            'exercises': {
                                'type': 'array',
                                'items': {'type': 'object'}
                            },
                            'resources': {
                                'type': 'array',
                                'items': {'type': 'string'}
                            }
                        }
                    },
                    'generation_time': {'type': 'string'},
                    'model_used': {'type': 'string'}
                }
            }
        },
        '400': {'description': '请求参数错误'},
        '403': {'description': '权限不足'},
        '500': {'description': 'AI服务不可用'}
    }
})
def generate_lesson_plan_docs():
    """AI生成教案"""
    data = request.get_json()
    
    return jsonify({
        "lesson_plan": {
            "title": f"{data.get('topic')} - 教学计划",
            "duration": data.get('duration', 60),
            "objectives": [
                "理解函数的定义和调用",
                "掌握参数传递机制",
                "学会模块的导入和使用"
            ],
            "outline": [
                {
                    "section": "函数基础",
                    "time": 20,
                    "content": "介绍函数的概念、语法和基本用法",
                    "activities": ["讲解", "示例演示", "学生练习"]
                },
                {
                    "section": "模块系统",
                    "time": 25,
                    "content": "Python模块的导入和使用方法",
                    "activities": ["实践操作", "代码编写"]
                },
                {
                    "section": "综合练习",
                    "time": 15,
                    "content": "结合函数和模块的综合应用",
                    "activities": ["项目练习", "答疑"]
                }
            ],
            "exercises": [
                {
                    "type": "coding",
                    "question": "编写一个计算器函数模块",
                    "difficulty": "intermediate"
                }
            ],
            "resources": [
                "Python官方文档",
                "函数示例代码",
                "模块使用案例"
            ]
        },
        "generation_time": "3.2秒",
        "model_used": "GPT-4"
    })

@rag_docs_bp.route('/recommendations', methods=['GET'])
@swag_from({
    'tags': ['AI助手'],
    'summary': '获取学习推荐',
    'description': '基于学习记录和AI分析，为用户推荐学习内容',
    'security': [{'Bearer': []}],
    'parameters': [
        {
            'name': 'user_id',
            'in': 'query',
            'type': 'integer',
            'description': '用户ID（管理员可查看其他用户）'
        },
        {
            'name': 'course_id',
            'in': 'query',
            'type': 'integer',
            'description': '课程ID（限制在特定课程内推荐）'
        },
        {
            'name': 'type',
            'in': 'query',
            'type': 'string',
            'enum': ['content', 'exercise', 'review'],
            'description': '推荐类型'
        }
    ],
    'responses': {
        '200': {
            'description': '推荐获取成功',
            'schema': {
                'type': 'object',
                'properties': {
                    'recommendations': {
                        'type': 'array',
                        'items': {
                            'type': 'object',
                            'properties': {
                                'type': {'type': 'string'},
                                'title': {'type': 'string'},
                                'description': {'type': 'string'},
                                'confidence': {'type': 'number'},
                                'reason': {'type': 'string'},
                                'estimated_time': {'type': 'string'},
                                'difficulty': {'type': 'string'}
                            }
                        }
                    },
                    'learning_progress': {
                        'type': 'object',
                        'properties': {
                            'completed_topics': {'type': 'integer'},
                            'current_level': {'type': 'string'},
                            'next_milestone': {'type': 'string'}
                        }
                    }
                }
            }
        }
    }
})
def get_recommendations_docs():
    """获取学习推荐"""
    return jsonify({
        "recommendations": [
            {
                "type": "content",
                "title": "Python异常处理",
                "description": "学习try-except语句的使用",
                "confidence": 0.89,
                "reason": "基于您的学习进度，建议学习异常处理",
                "estimated_time": "30分钟",
                "difficulty": "intermediate"
            },
            {
                "type": "exercise",
                "title": "函数练习题",
                "description": "巩固函数定义和调用的知识",
                "confidence": 0.76,
                "reason": "您在函数相关题目中有一些错误",
                "estimated_time": "20分钟",
                "difficulty": "beginner"
            }
        ],
        "learning_progress": {
            "completed_topics": 8,
            "current_level": "intermediate",
            "next_milestone": "面向对象编程"
        }
    })



