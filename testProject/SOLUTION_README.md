# 稽核档案管理系统问题解决方案

## 问题描述
系统出现以下错误：
1. `获取数据失败: (1146, "Table 'nanan_data.file_attachments' doesn't exist")`
2. `获取档案信息失败: Unexpected end of template. Jinja was looking for the following tags: 'endblock'`

## 问题原因
1. **数据库表缺失**：`file_attachments` 表不存在
2. **模板渲染错误**：当数据库查询失败时，Jinja2模板无法正确渲染

## 解决方案

### 方案1：手动执行SQL（推荐）

1. **连接到MySQL数据库**
   ```bash
   mysql -h 192.168.0.215 -u root -p nanan_data
   ```

2. **执行SQL脚本**
   ```sql
   -- 创建file_attachments表
   CREATE TABLE file_attachments (
       id INT AUTO_INCREMENT PRIMARY KEY,
       file_id INT NOT NULL COMMENT '档案ID',
       filename VARCHAR(255) NOT NULL COMMENT '文件名',
       original_name VARCHAR(255) NOT NULL COMMENT '原始文件名',
       file_path VARCHAR(500) NOT NULL COMMENT '文件路径',
       file_size INT NOT NULL COMMENT '文件大小（字节）',
       file_type VARCHAR(100) COMMENT '文件类型',
       uploaded_by INT NOT NULL COMMENT '上传人ID',
       uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '上传时间',
       description TEXT COMMENT '文件描述',
       status ENUM('active', 'deleted') DEFAULT 'active' COMMENT '状态',
       created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
       updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
       INDEX idx_file_id (file_id),
       INDEX idx_uploaded_by (uploaded_by),
       INDEX idx_file_type (file_type)
   ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='档案附件表';
   
   -- 添加notes字段到audit_files表
   ALTER TABLE audit_files ADD COLUMN notes TEXT COMMENT '备注信息' AFTER recommendations;
   ```

3. **验证表创建成功**
   ```sql
   SHOW TABLES LIKE 'file_attachments';
   DESCRIBE audit_files;
   ```

### 方案2：使用提供的SQL文件

1. **使用 `create_tables_manual.sql` 文件**
   - 在MySQL客户端中执行该文件中的所有SQL命令

2. **或者使用 `fix_database_simple.sql` 文件**
   - 该文件包含完整的数据库修复脚本

### 方案3：Python脚本修复

1. **运行数据库修复脚本**
   ```bash
   py fix_database.py
   ```

2. **如果遇到权限问题，检查MySQL用户权限**
   ```sql
   SHOW GRANTS FOR 'root'@'%';
   ```

## 验证修复

### 1. 检查数据库表
```sql
USE nanan_data;
SHOW TABLES;
```

应该看到以下表：
- `audit_files` (包含notes字段)
- `file_attachments`
- `audit_logs`
- `notifications`
- `system_settings`

### 2. 重启Web应用
```bash
# 停止当前应用 (Ctrl+C)
# 重新启动
py web_app.py
```

### 3. 测试功能
1. 访问 http://localhost:5000
2. 登录系统 (admin/admin123)
3. 测试档案列表页面
4. 测试编辑档案功能

## 常见问题

### Q: 仍然出现模板错误怎么办？
A: 检查模板文件是否有语法错误，确保所有 `{% block %}` 都有对应的 `{% endblock %}`

### Q: 数据库连接失败怎么办？
A: 检查数据库配置、网络连接和用户权限

### Q: 表创建失败怎么办？
A: 检查MySQL版本兼容性，可能需要调整SQL语法

## 预防措施

1. **定期备份数据库**
2. **使用数据库迁移工具**
3. **在开发环境中测试所有SQL脚本**
4. **监控应用日志，及时发现错误**

## 联系支持

如果问题仍然存在，请提供：
1. 错误日志
2. MySQL版本信息
3. 数据库表结构
4. 应用启动日志 