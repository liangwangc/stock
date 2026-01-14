#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
检查项目依赖是否安装

使用方法:
    python check_dependencies.py
"""

import sys
import os

# 设置 Windows 控制台编码为 UTF-8
if sys.platform == 'win32':
    try:
        import codecs
        sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer, 'strict')
        sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer, 'strict')
    except:
        # 如果设置失败，使用 ASCII 字符
        pass

REQUIRED_PACKAGES = {
    'pandas': 'pandas',
    'numpy': 'numpy',
    'akshare': 'akshare',
    'requests': 'requests',
    'beautifulsoup4': 'bs4',
    'lxml': 'lxml',
    'pymysql': 'pymysql',
    'flask': 'flask',
    'flask-socketio': 'flask_socketio',
    'schedule': 'schedule',
    'tqdm': 'tqdm',
    'python-dateutil': 'dateutil',
}

OPTIONAL_PACKAGES = {
    'scikit-learn': 'sklearn',
    'matplotlib': 'matplotlib',
    'seaborn': 'seaborn',
    'plotly': 'plotly',
    'dash': 'dash',
    'yfinance': 'yfinance',
    'jieba': 'jieba',
    'psutil': 'psutil',
    'pytest': 'pytest',
    'openpyxl': 'openpyxl',
}

def check_package(package_name, import_name):
    """检查包是否安装"""
    try:
        mod = __import__(import_name)
        version = getattr(mod, '__version__', '未知')
        return True, version
    except ImportError:
        return False, None

def main():
    # 使用 ASCII 兼容字符，避免 Windows 编码问题
    check_mark = '[OK]'
    cross_mark = '[X]'
    circle_mark = '[O]'
    error_mark = '[ERROR]'
    success_mark = '[SUCCESS]'
    tip_mark = '[TIP]'
    
    try:
        # 尝试使用 Unicode 字符
        check_mark = '✓'
        cross_mark = '✗'
        circle_mark = '○'
        error_mark = '❌'
        success_mark = '✅'
        tip_mark = '💡'
    except:
        pass
    
    print('=' * 60)
    print('项目依赖检查')
    print('=' * 60)
    
    print('\n[必需依赖]')
    print('-' * 60)
    missing_required = []
    for pkg_name, import_name in REQUIRED_PACKAGES.items():
        installed, version = check_package(pkg_name, import_name)
        if installed:
            print(f'{check_mark} {pkg_name:25s} - 版本: {version}')
        else:
            print(f'{cross_mark} {pkg_name:25s} - 未安装')
            missing_required.append(pkg_name)
    
    print('\n[可选依赖]')
    print('-' * 60)
    missing_optional = []
    for pkg_name, import_name in OPTIONAL_PACKAGES.items():
        installed, version = check_package(pkg_name, import_name)
        if installed:
            print(f'{check_mark} {pkg_name:25s} - 版本: {version}')
        else:
            print(f'{circle_mark} {pkg_name:25s} - 未安装（可选）')
            missing_optional.append(pkg_name)
    
    print('\n' + '=' * 60)
    if missing_required:
        print(f'\n{error_mark} 缺失必需依赖: {", ".join(missing_required)}')
        print(f'\n请运行以下命令安装:')
        print(f'pip install {" ".join(missing_required)}')
        print(f'\n或使用 requirements.txt:')
        print(f'pip install -r requirements.txt')
        return 1
    else:
        print(f'\n{success_mark} 所有必需依赖已安装！')
        if missing_optional:
            print(f'\n{tip_mark} 可选依赖未安装: {", ".join(missing_optional)}')
            print('这些包用于增强功能，不影响核心功能运行。')
            print(f'\n如需安装可选依赖，请运行:')
            print(f'pip install {" ".join(missing_optional)}')
        return 0

if __name__ == '__main__':
    sys.exit(main())
