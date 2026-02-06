#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""修复设置页面页签切换问题"""
import re
import os

# 读取文件
file_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'templates', 'settings.html')
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 替换 event.target 部分（使用正则表达式）
pattern = r'(\s+)event\.target\.classList\.add\(''active''\);\s+document\.getElementById\(`panel-\$\{panelName\}`\)\.classList\.add\(''active''\);'
replacement = r'''\1// 找到对应的菜单项并添加active状态
\1const menuItems = document.querySelectorAll('.menu-item');
\1menuItems.forEach(item => {
\1    const onclickAttr = item.getAttribute('onclick');
\1    if (onclickAttr && onclickAttr.includes(`'${panelName}'`)) {
\1        item.classList.add('active');
\1    }
\1});
\1
\1// 显示对应的面板
\1const targetPanel = document.getElementById(`panel-${panelName}`);
\1if (targetPanel) {
\1    targetPanel.classList.add('active');
\1} else {
\1    console.error(`面板 panel-${panelName} 不存在`);
\1    return;
\1}'''

content = re.sub(pattern, replacement, content)

# 添加其他面板的加载逻辑
old_end = """            // 如果切换到股票数据获取面板，加载任务列表
            if (panelName === 'stock-data') {
                setTimeout(() => {
                    refreshStockDataTasks();
                }, 100);
            }
        }"""

new_end = """            // 如果切换到股票数据获取面板，加载任务列表
            if (panelName === 'stock-data') {
                setTimeout(() => {
                    refreshStockDataTasks();
                }, 100);
            }
            
            // 如果切换到新闻抓取面板，加载任务列表
            if (panelName === 'news') {
                setTimeout(() => {
                    if (typeof refreshNewsTasks === 'function') {
                        refreshNewsTasks();
                    }
                }, 100);
            }
            
            // 如果切换到备份管理面板，加载备份列表
            if (panelName === 'backup') {
                setTimeout(() => {
                    if (typeof refreshBackupList === 'function') {
                        refreshBackupList();
                    }
                }, 100);
            }
            
            // 如果切换到任务管理面板，加载任务列表
            if (panelName === 'task') {
                setTimeout(() => {
                    if (typeof refreshTaskList === 'function') {
                        refreshTaskList();
                    }
                }, 100);
            }
        }"""

content = content.replace(old_end, new_end)

# 写回文件
with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("修复完成！")
