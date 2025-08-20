# 稽核档案管理系统编辑功能修复说明

## 问题描述
原系统中所有编辑功能都无法点击使用，主要原因是：
1. 缺少编辑档案的后端路由
2. 缺少编辑档案的前端模板
3. 前端编辑按钮链接指向 `#`，没有实际功能
4. 缺少附件管理相关的数据库操作方法

## 已修复的内容

### 1. 后端路由修复
在 `web_app.py` 中添加了以下路由：
- `GET/POST /files/<int:file_id>/edit` - 编辑档案
- `DELETE /attachments/<int:attachment_id>/delete` - 删除附件

### 2. 前端模板修复
- 创建了 `edit_file.html` 模板文件
- 修复了 `files.html` 中编辑按钮的链接

### 3. 数据库操作修复
在 `database.py` 中添加了 `FileAttachmentDAO` 类，包含：
- `create_attachment()` - 创建附件
- `get_attachments_by_file_id()` - 获取档案附件
- `get_attachment_by_id()` - 根据ID获取附件
- `delete_attachment()` - 删除附件（软删除）
- `update_attachment()` - 更新附件信息

### 4. 数据库结构更新
- 在 `audit_files` 表中添加了 `notes` 字段
- 在 `file_attachments` 表中添加了 `status`、`created_at`、`updated_at` 字段

## 需要执行的数据库更新

### 1. 添加notes字段到audit_files表
```sql
ALTER TABLE audit_files ADD COLUMN notes TEXT COMMENT '备注信息' AFTER recommendations;
```

### 2. 添加字段到file_attachments表
```sql
ALTER TABLE file_attachments 
ADD COLUMN status ENUM('active', 'deleted') DEFAULT 'active' COMMENT '状态' AFTER description,
ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间' AFTER status,
ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间' AFTER created_at;
```

## 功能特性

### 编辑档案功能
- 支持编辑档案的基本信息（标题、分类、部门、优先级、状态等）
- 支持编辑档案描述和备注
- 支持添加新的附件
- 支持删除现有附件
- 权限控制：只有管理员、稽核员或档案创建者可以编辑

### 附件管理功能
- 支持上传多个附件
- 支持查看、下载附件
- 支持删除附件
- 文件类型限制和大小限制

## 使用方法

1. 在档案列表页面，点击"编辑"按钮进入编辑页面
2. 修改需要更新的字段
3. 可以添加新的附件
4. 可以删除现有附件
5. 点击"保存修改"提交更改

## 注意事项

1. 编辑功能需要相应的权限
2. 附件删除是软删除，不会立即从磁盘删除文件
3. 建议定期清理已删除的附件文件
4. 编辑操作会记录在系统日志中

## 测试建议

1. 测试不同角色用户的编辑权限
2. 测试附件上传和删除功能
3. 测试各种字段的编辑功能
4. 测试错误处理和验证 