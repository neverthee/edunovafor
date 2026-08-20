"""
API文档配置模块
使用Flasgger为Flask应用生成Swagger UI文档
"""

from flasgger import Swagger
from flask import Flask

def init_swagger(app: Flask) -> Swagger:
    """
    初始化Swagger文档配置
    
    Args:
        app: Flask应用实例
        
    Returns:
        Swagger实例
    """
    
    # Swagger配置
    swagger_config = {
        "headers": [],
        "specs": [
            {
                "endpoint": 'apispec_1',
                "route": '/apispec_1.json',
                "rule_filter": lambda rule: True,  # 包含所有路由
                "model_filter": lambda tag: True,  # 包含所有模型
            }
        ],
        "static_url_path": "/flasgger_static",
        "swagger_ui": True,
        "specs_route": "/docs/"  # API文档访问路径
    }

    # Swagger模板配置
    swagger_template = {
        "swagger": "2.0",
        "info": {
            "title": "EduNova 智能教学系统 API",
            "description": "基于Flask的智能教学系统API文档",
            "version": "1.0.0",
            "termsOfService": "",
            "contact": {
                "name": "EduNova开发团队",
                "email": "support@edunova.com"
            },
            "license": {
                "name": "MIT License",
                "url": "https://opensource.org/licenses/MIT"
            }
        },
        "host": "localhost:5001",
        "basePath": "/api",
        "schemes": ["http", "https"],
        "consumes": ["application/json"],
        "produces": ["application/json"],
        "securityDefinitions": {
            "Bearer": {
                "type": "apiKey",
                "name": "Authorization",
                "in": "header",
                "description": "JWT Token格式: Bearer <token>"
            }
        },
        "security": [
            {
                "Bearer": []
            }
        ],
        "definitions": {
            "User": {
                "type": "object",
                "properties": {
                    "id": {"type": "integer", "description": "用户ID"},
                    "username": {"type": "string", "description": "用户名"},
                    "email": {"type": "string", "description": "邮箱"},
                    "full_name": {"type": "string", "description": "全名"},
                    "role": {
                        "type": "string", 
                        "enum": ["admin", "teacher", "student"],
                        "description": "用户角色"
                    },
                    "is_active": {"type": "boolean", "description": "是否激活"},
                    "created_at": {"type": "string", "format": "date-time"},
                    "updated_at": {"type": "string", "format": "date-time"}
                }
            },
            "Course": {
                "type": "object",
                "properties": {
                    "id": {"type": "integer", "description": "课程ID"},
                    "name": {"type": "string", "description": "课程名称"},
                    "description": {"type": "string", "description": "课程描述"},
                    "category": {"type": "string", "description": "课程分类"},
                    "difficulty": {
                        "type": "string",
                        "enum": ["beginner", "intermediate", "advanced"],
                        "description": "难度级别"
                    },
                    "is_public": {"type": "boolean", "description": "是否公开"},
                    "teacher_id": {"type": "integer", "description": "教师ID"},
                    "created_at": {"type": "string", "format": "date-time"}
                }
            },
            "Assessment": {
                "type": "object",
                "properties": {
                    "id": {"type": "integer", "description": "评估ID"},
                    "title": {"type": "string", "description": "评估标题"},
                    "description": {"type": "string", "description": "评估描述"},
                    "type": {
                        "type": "string",
                        "enum": ["quiz", "exam", "assignment"],
                        "description": "评估类型"
                    },
                    "total_score": {"type": "number", "description": "总分"},
                    "duration": {"type": "integer", "description": "时长（分钟）"},
                    "is_published": {"type": "boolean", "description": "是否发布"}
                }
            },
            "ApiResponse": {
                "type": "object",
                "properties": {
                    "status": {"type": "string", "description": "响应状态"},
                    "message": {"type": "string", "description": "响应消息"},
                    "data": {"type": "object", "description": "响应数据"}
                }
            },
            "ErrorResponse": {
                "type": "object",
                "properties": {
                    "error": {"type": "string", "description": "错误信息"},
                    "status": {"type": "string", "description": "错误状态"}
                }
            }
        },
        "tags": [
            {
                "name": "认证",
                "description": "用户认证相关接口"
            },
            {
                "name": "用户管理",
                "description": "用户信息管理接口"
            },
            {
                "name": "课程管理",
                "description": "课程相关操作接口"
            },
            {
                "name": "评估系统",
                "description": "测验、考试、作业管理接口"
            },
            {
                "name": "AI助手",
                "description": "智能问答和RAG相关接口"
            },
            {
                "name": "学习分析",
                "description": "学习数据分析和统计接口"
            },
            {
                "name": "管理员",
                "description": "系统管理员专用接口"
            }
        ]
    }

    return Swagger(app, config=swagger_config, template=swagger_template)


def add_common_responses():
    """
    通用API响应格式定义
    """
    return {
        "400": {
            "description": "请求参数错误",
            "schema": {"$ref": "#/definitions/ErrorResponse"}
        },
        "401": {
            "description": "未授权访问",
            "schema": {"$ref": "#/definitions/ErrorResponse"}
        },
        "403": {
            "description": "权限不足",
            "schema": {"$ref": "#/definitions/ErrorResponse"}
        },
        "404": {
            "description": "资源不存在",
            "schema": {"$ref": "#/definitions/ErrorResponse"}
        },
        "500": {
            "description": "服务器内部错误",
            "schema": {"$ref": "#/definitions/ErrorResponse"}
        }
    }



