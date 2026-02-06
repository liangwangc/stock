#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""简单修复设置页面页签切换问题"""
import os

file_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'templates', 'settings.html')

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 直接替换这两行
old = """            event.target.classList.add('active');
            document.getElementById(`panel-${panelName}`).classList.add('active');"""

new = """            // 找到对应的菜单项并添加active状态
            const menuItems = document.querySelectorAll('.menu-item');
            menuItems.forEach(item => {
                const onclickAttr = item.getAttribute('onclick');
                if (onclickAttr && onclickAttr.includes(`'${panelName}'`)) {
                    item.classList.add('active');
                }
            });
            
            // 显示对应的面板
            const targetPanel = document.getElementById(`panel-${panelName}`);
            if (targetPanel) {
                targetPanel.classList.add('active');
            } else {
                console.error(`面板 panel-${panelName} 不存在`);
                return;
            }"""

if old in content:
    content = content.replace(old, new)
    print("找到并替换了 event.target 代码")
else:
    print("未找到 event.target 代码，可能已经修复")

# 添加其他面板的加载逻辑
if "// 如果切换到股票数据获取面板" in content and "// 如果切换到新闻抓取面板" not in content:
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
    
    if old_end in content:
        content = content.replace(old_end, new_end)
        print("添加了其他面板的加载逻辑")

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("修复完成！")
