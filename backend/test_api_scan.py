#!/usr/bin/env python3
"""
简单的API路由测试脚本
用于测试和调试API扫描功能
"""

import os
import sys

def test_directory_structure():
    """测试目录结构"""
    print("🔍 测试目录结构...")
    
    current_dir = os.path.dirname(os.path.abspath(__file__))
    print(f"当前脚本目录: {current_dir}")
    
    # 检查api目录
    api_dir = os.path.join(current_dir, "api")
    print(f"API目录: {api_dir}")
    print(f"API目录存在: {os.path.exists(api_dir)}")
    
    if os.path.exists(api_dir):
        files = os.listdir(api_dir)
        print(f"API文件: {files}")
        
        for file in files:
            if file.endswith('.py'):
                filepath = os.path.join(api_dir, file)
                print(f"  📄 {file} (大小: {os.path.getsize(filepath)} bytes)")

def simple_route_scan():
    """简单的路由扫描"""
    print("\n🔍 开始简单路由扫描...")
    
    current_dir = os.path.dirname(os.path.abspath(__file__))
    api_dir = os.path.join(current_dir, "api")
    
    if not os.path.exists(api_dir):
        print("❌ API目录不存在")
        return
    
    route_count = 0
    
    for filename in os.listdir(api_dir):
        if filename.endswith('.py') and filename != '__init__.py':
            filepath = os.path.join(api_dir, filename)
            print(f"\n📄 扫描文件: {filename}")
            
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    content = f.read()
                    
                # 简单搜索路由装饰器
                lines = content.split('\n')
                file_routes = 0
                
                for i, line in enumerate(lines):
                    if '@' in line and '.route(' in line:
                        file_routes += 1
                        route_count += 1
                        print(f"  第{i+1}行: {line.strip()}")
                
                print(f"  └─ 发现 {file_routes} 个路由")
                
            except Exception as e:
                print(f"  ❌ 读取文件失败: {e}")
    
    print(f"\n📊 总计发现 {route_count} 个路由")

def main():
    """主函数"""
    print("🚀 API扫描测试工具")
    print("=" * 40)
    
    test_directory_structure()
    simple_route_scan()
    
    print("\n✅ 测试完成")

if __name__ == "__main__":
    main()



