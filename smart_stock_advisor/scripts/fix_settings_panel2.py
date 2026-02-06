#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""修复设置页面页签切换问题 - 方法2"""
import os

# 读取文件
file_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'templates', 'settings.html')
with open(file_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

# 找到需要替换的行
new_lines = []
i = 0
while i < len(lines):
    line = lines[i]
    
    # 如果找到 event.target 行
    if 'event.target.classList.add' in line:
        # 替换这两行
        indent = '            '  # 12个空格
        new_lines.append(f'{indent}// 找到对应的菜单项并添加active状态\n')
        new_lines.append(f'{indent}const menuItems = document.querySelectorAll(\'.menu-item\');\n')
        new_lines.append(f'{indent}menuItems.forEach(item => {{\n')
        new_lines.append(f'{indent}    const onclickAttr = item.getAttribute(\'onclick\');\n')
        new_lines.append(f'{indent}    if (onclickAttr && onclickAttr.includes(`\'${{panelName}}\'`)) {{\n')
        new_lines.append(f'{indent}        item.classList.add(\'active\');\n')
        new_lines.append(f'{indent}    }}\n')
        new_lines.append(f'{indent}}});\n')
        new_lines.append(f'{indent}\n')
        new_lines.append(f'{indent}// 显示对应的面板\n')
        new_lines.append(f'{indent}const targetPanel = document.getElementById(`panel-${{panelName}}`);\n')
        new_lines.append(f'{indent}if (targetPanel) {{\n')
        new_lines.append(f'{indent}    targetPanel.classList.add(\'active\');\n')
        new_lines.append(f'{indent}}} else {{\n')
        new_lines.append(f'{indent}    console.error(`面板 panel-${{panelName}} 不存在`);\n')
        new_lines.append(f'{indent}    return;\n')
        new_lines.append(f'{indent}}}\n')
        # 跳过下一行（document.getElementById）
        i += 2
        continue
    
    new_lines.append(line)
    i += 1

# 添加其他面板的加载逻辑
content = ''.join(new_lines)

# 添加其他面板的加载逻辑
if "// 如果切换到股票数据获取面板" in content:
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
