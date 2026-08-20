#!/usr/bin/env python3
"""
API文档生成器
自动扫描Flask路由并生成基础文档模板
"""

import os
import re
import ast
import json
from typing import Dict, List, Any

class APIDocumentationGenerator:
    """API文档生成器类"""
    
    def __init__(self, api_dir: str = None):
        if api_dir is None:
            # 自动检测api目录位置
            current_dir = os.path.dirname(os.path.abspath(__file__))
            self.api_dir = os.path.join(current_dir, "api")
            
            # 如果当前目录下没有api文件夹，尝试上级目录
            if not os.path.exists(self.api_dir):
                parent_dir = os.path.dirname(current_dir)
                self.api_dir = os.path.join(parent_dir, "backend", "api")
            
            # 如果还是找不到，使用相对路径
            if not os.path.exists(self.api_dir):
                self.api_dir = "api"
        else:
            self.api_dir = api_dir
            
        self.routes = []
        
    def scan_routes(self) -> List[Dict[str, Any]]:
        """扫描所有API路由"""
        routes = []
        
        print(f"📁 扫描目录: {os.path.abspath(self.api_dir)}")
        
        if not os.path.exists(self.api_dir):
            print(f"❌ 错误：目录不存在 {self.api_dir}")
            print("💡 请确保在正确的目录下运行脚本")
            return routes
        
        try:
            files = os.listdir(self.api_dir)
            print(f"📄 发现文件: {files}")
            
            for filename in files:
                if filename.endswith('.py') and filename != '__init__.py':
                    filepath = os.path.join(self.api_dir, filename)
                    print(f"🔍 解析文件: {filename}")
                    file_routes = self._parse_file_routes(filepath)
                    routes.extend(file_routes)
                    print(f"  └─ 找到 {len(file_routes)} 个路由")
        except Exception as e:
            print(f"❌ 扫描目录时出错: {e}")
        
        return routes
    
    def _parse_file_routes(self, filepath: str) -> List[Dict[str, Any]]:
        """解析单个文件中的路由"""
        routes = []
        
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 使用正则表达式查找路由装饰器
            route_pattern = r'@\w+\.route\([\'"]([^\'"]+)[\'"](?:,\s*methods=\[([^\]]+)\])?\)'
            function_pattern = r'def\s+(\w+)\([^)]*\):'
            
            lines = content.split('\n')
            
            for i, line in enumerate(lines):
                route_match = re.search(route_pattern, line)
                if route_match:
                    path = route_match.group(1)
                    methods_str = route_match.group(2)
                    
                    # 解析HTTP方法
                    methods = ['GET']  # 默认方法
                    if methods_str:
                        methods = [m.strip().strip('\'"') for m in methods_str.split(',')]
                    
                    # 查找对应的函数名
                    func_name = None
                    for j in range(i + 1, min(i + 5, len(lines))):
                        func_match = re.search(function_pattern, lines[j])
                        if func_match:
                            func_name = func_match.group(1)
                            break
                    
                    # 获取函数文档字符串
                    docstring = self._extract_docstring(content, func_name)
                    
                    route_info = {
                        'path': path,
                        'methods': methods,
                        'function': func_name,
                        'docstring': docstring,
                        'file': os.path.basename(filepath),
                        'line': i + 1
                    }
                    routes.append(route_info)
                    
        except Exception as e:
            print(f"解析文件 {filepath} 时出错: {e}")
        
        return routes
    
    def _extract_docstring(self, content: str, func_name: str) -> str:
        """提取函数的文档字符串"""
        if not func_name:
            return ""
            
        try:
            tree = ast.parse(content)
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef) and node.name == func_name:
                    if node.body and isinstance(node.body[0], ast.Expr) and isinstance(node.body[0].value, ast.Str):
                        return node.body[0].value.s
        except:
            pass
        
        return ""
    
    def generate_markdown_docs(self) -> str:
        """生成Markdown格式的API文档"""
        routes = self.scan_routes()
        
        # 按文件分组
        grouped_routes = {}
        for route in routes:
            file_name = route['file']
            if file_name not in grouped_routes:
                grouped_routes[file_name] = []
            grouped_routes[file_name].append(route)
        
        # 生成Markdown内容
        markdown = "# EduNova API 文档\n\n"
        markdown += "## 概述\n\n"
        markdown += "这是EduNova智能教学系统的API文档，包含所有可用的接口端点。\n\n"
        
        # 目录
        markdown += "## 目录\n\n"
        for file_name in sorted(grouped_routes.keys()):
            module_name = file_name.replace('.py', '').replace('_', ' ').title()
            markdown += f"- [{module_name}](#{file_name.replace('.py', '').replace('_', '-')})\n"
        markdown += "\n"
        
        # 详细文档
        for file_name in sorted(grouped_routes.keys()):
            module_name = file_name.replace('.py', '').replace('_', ' ').title()
            markdown += f"## {module_name}\n\n"
            markdown += f"文件: `{file_name}`\n\n"
            
            for route in grouped_routes[file_name]:
                markdown += f"### {route['function'] or 'Unknown'}\n\n"
                markdown += f"**路径**: `{route['path']}`\n\n"
                markdown += f"**方法**: {', '.join(route['methods'])}\n\n"
                
                if route['docstring']:
                    markdown += f"**描述**: {route['docstring']}\n\n"
                
                markdown += "**示例请求**:\n"
                markdown += "```bash\n"
                method = route['methods'][0] if route['methods'] else 'GET'
                markdown += f"curl -X {method} http://localhost:5001/api{route['path']}\n"
                markdown += "```\n\n"
                
                markdown += "---\n\n"
        
        return markdown
    
    def generate_openapi_spec(self) -> Dict[str, Any]:
        """生成OpenAPI 3.0规范"""
        routes = self.scan_routes()
        
        spec = {
            "openapi": "3.0.0",
            "info": {
                "title": "EduNova API",
                "description": "智能教学系统API",
                "version": "1.0.0"
            },
            "servers": [
                {
                    "url": "http://localhost:5001/api",
                    "description": "开发服务器"
                }
            ],
            "paths": {}
        }
        
        for route in routes:
            path = route['path']
            if path not in spec['paths']:
                spec['paths'][path] = {}
            
            for method in route['methods']:
                spec['paths'][path][method.lower()] = {
                    "summary": route['docstring'] or f"{route['function']}",
                    "description": route['docstring'] or f"来自 {route['file']} 的 {route['function']} 函数",
                    "responses": {
                        "200": {
                            "description": "成功响应"
                        }
                    }
                }
        
        return spec
    
    def save_documentation(self, output_dir: str = None):
        """保存文档到文件"""
        if output_dir is None:
            # 自动确定输出目录
            current_dir = os.path.dirname(os.path.abspath(__file__))
            # 尝试在项目根目录创建docs目录
            project_root = os.path.dirname(current_dir)
            output_dir = os.path.join(project_root, "docs", "api")
        
        os.makedirs(output_dir, exist_ok=True)
        print(f"📁 输出目录: {os.path.abspath(output_dir)}")
        
        # 生成Markdown文档
        markdown_content = self.generate_markdown_docs()
        with open(os.path.join(output_dir, "api_reference.md"), 'w', encoding='utf-8') as f:
            f.write(markdown_content)
        
        # 生成OpenAPI规范
        openapi_spec = self.generate_openapi_spec()
        with open(os.path.join(output_dir, "openapi.json"), 'w', encoding='utf-8') as f:
            json.dump(openapi_spec, f, indent=2, ensure_ascii=False)
        
        # 生成路由列表
        routes = self.scan_routes()
        with open(os.path.join(output_dir, "routes.json"), 'w', encoding='utf-8') as f:
            json.dump(routes, f, indent=2, ensure_ascii=False)
        
        print(f"📚 文档已保存到 {output_dir}/")
        print(f"  - Markdown文档: api_reference.md")
        print(f"  - OpenAPI规范: openapi.json")
        print(f"  - 路由列表: routes.json")

def main():
    """主函数"""
    print("🔍 开始扫描API路由...")
    
    generator = APIDocumentationGenerator()
    routes = generator.scan_routes()
    
    print(f"📊 发现 {len(routes)} 个API端点")
    
    # 显示路由统计
    file_stats = {}
    for route in routes:
        file_name = route['file']
        if file_name not in file_stats:
            file_stats[file_name] = 0
        file_stats[file_name] += 1
    
    print("\n📁 按文件分布:")
    for file_name, count in sorted(file_stats.items()):
        print(f"  {file_name}: {count} 个端点")
    
    # 保存文档
    generator.save_documentation()
    
    print("\n🎉 API文档生成完成!")
    print("\n💡 建议:")
    print("1. 安装Flasgger: pip install flasgger")
    print("2. 参考 backend/api/auth_documented.py 添加详细文档")
    print("3. 访问 http://localhost:5001/docs/ 查看交互式文档")

if __name__ == "__main__":
    main()
