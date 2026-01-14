#!/usr/bin/env python3
"""
模板测试脚本 - 验证Jinja2模板语法是否正确
"""

import os
import sys
from jinja2 import Environment, FileSystemLoader, TemplateSyntaxError

def test_template(template_name):
    """测试模板文件语法"""
    try:
        # 设置Jinja2环境
        template_dir = os.path.join(os.path.dirname(__file__), 'templates')
        env = Environment(loader=FileSystemLoader(template_dir))
        
        # 尝试加载模板
        template = env.get_template(template_name)
        print(f"✅ {template_name} - 模板语法正确")
        return True
        
    except TemplateSyntaxError as e:
        print(f"❌ {template_name} - 模板语法错误: {e}")
        print(f"   行号: {e.lineno}")
        print(f"   错误信息: {e.message}")
        return False
    except Exception as e:
        print(f"❌ {template_name} - 其他错误: {e}")
        return False

def main():
    """测试所有模板文件"""
    print("🧪 开始测试模板文件语法...")
    print("=" * 50)
    
    # 需要测试的模板文件
    templates = [
        'base.html',
        'view_file.html',
        'edit_file.html',
        'files.html',
        'new_file.html',
        'dashboard.html',
        'login.html',
        'users.html',
        'profile.html',
        'logs.html'
    ]
    
    success_count = 0
    total_count = len(templates)
    
    for template in templates:
        if test_template(template):
            success_count += 1
    
    print("=" * 50)
    print(f"📊 测试结果: {success_count}/{total_count} 个模板通过测试")
    
    if success_count == total_count:
        print("🎉 所有模板文件语法正确！")
        return True
    else:
        print("⚠️ 部分模板文件存在语法错误，请检查上面的错误信息。")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 