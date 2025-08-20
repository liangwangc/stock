#!/usr/bin/env python3
"""
稽核档案管理系统 - Web版本

使用Flask框架提供Web界面
"""

from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify, send_from_directory
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
import sys
import os
from datetime import datetime

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'audit_system'))

from audit_system.database import DatabaseManager
from audit_system.auth import AuthManager, PermissionManager

# 创建Flask应用
app = Flask(__name__)
app.secret_key = 'your-secret-key-here'  # 在生产环境中应该使用安全的密钥

# 文件上传配置
import os
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'uploads')
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx', 'zip', 'rar'}
MAX_FILE_SIZE = 16 * 1024 * 1024  # 16MB

# 确保上传目录存在
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = MAX_FILE_SIZE

# 初始化Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# 初始化数据库和认证管理器
db_manager = DatabaseManager()
auth_manager = AuthManager(db_manager)
permission_manager = PermissionManager(auth_manager)

@login_manager.user_loader
def load_user(user_id):
    """加载用户"""
    try:
        from audit_system.database import UserDAO
        user_dao = UserDAO(db_manager)
        user_data = user_dao.get_user_by_id(int(user_id))
        if user_data:
            return User(user_data)
        return None
    except:
        return None

class User:
    """用户类，用于Flask-Login"""
    def __init__(self, user_data):
        self.id = user_data['id']
        self.username = user_data['username']
        self.real_name = user_data['real_name']
        self.role = user_data['role']
        self.department = user_data['department']
        self.is_authenticated = True
        self.is_active = user_data['status'] == 'active'
        self.is_anonymous = False
    
    def get_id(self):
        return str(self.id)

# 文件上传辅助函数
def allowed_file(filename):
    """检查文件扩展名是否允许"""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def save_uploaded_file(file, file_id):
    """保存上传的文件"""
    if file and allowed_file(file.filename):
        # 生成安全的文件名
        import uuid
        import os
        from werkzeug.utils import secure_filename
        
        # 获取文件扩展名
        file_ext = os.path.splitext(file.filename)[1]
        # 生成唯一文件名
        unique_filename = f"{file_id}_{uuid.uuid4().hex}{file_ext}"
        # 保存文件
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], unique_filename)
        file.save(file_path)
        
        return {
            'filename': unique_filename,
            'original_name': file.filename,
            'file_path': file_path,
            'file_size': os.path.getsize(file_path),
            'file_type': file_ext[1:].upper()
        }
    return None

# 路由定义
@app.route('/')
def index():
    """首页"""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    """用户登录"""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if not username or not password:
            flash('用户名和密码不能为空', 'error')
            return render_template('login.html')
        
        # 执行登录
        result = auth_manager.login(username, password)
        
        if result['success']:
            # 创建用户对象并登录
            user_data = result['user']
            user = User({
                'id': user_data['id'],
                'username': user_data['username'],
                'real_name': user_data['real_name'],
                'role': user_data['role'],
                'department': user_data['department'],
                'status': 'active'
            })
            login_user(user)
            
            # 记录登录日志
            from audit_system.database import AuditLogDAO
            log_dao = AuditLogDAO(db_manager)
            log_dao.log_action(
                user.id, "web_login", "user", user.id,
                "用户通过Web界面登录", request.remote_addr, request.user_agent.string
            )
            
            flash('登录成功！', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash(result['message'], 'error')
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    """用户登出"""
    # 记录登出日志
    from audit_system.database import AuditLogDAO
    log_dao = AuditLogDAO(db_manager)
    log_dao.log_action(
        current_user.id, "web_logout", "user", current_user.id,
        "用户通过Web界面登出", request.remote_addr, request.user_agent.string
    )
    
    logout_user()
    flash('已成功登出', 'success')
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    """仪表板"""
    try:
        # 获取统计信息
        from audit_system.database import AuditFileDAO, UserDAO
        file_dao = AuditFileDAO(db_manager)
        user_dao = UserDAO(db_manager)
        
        # 档案统计
        total_files = len(file_dao.get_audit_files(limit=1000))
        pending_files = len(file_dao.get_audit_files(status='pending', limit=1000))
        completed_files = len(file_dao.get_audit_files(status='completed', limit=1000))
        
        # 用户统计
        total_users = len(user_dao.get_all_users())
        
        # 最近档案
        recent_files = file_dao.get_audit_files(limit=5)
        
        stats = {
            'total_files': total_files,
            'pending_files': pending_files,
            'completed_files': completed_files,
            'total_users': total_users,
            'recent_files': recent_files
        }
        
        from datetime import datetime
        return render_template('dashboard.html', stats=stats, moment=datetime.now())
    except Exception as e:
        flash(f'获取数据失败: {str(e)}', 'error')
        return render_template('dashboard.html', stats={})

@app.route('/files')
@login_required
def files():
    """档案列表"""
    try:
        from audit_system.database import AuditFileDAO
        file_dao = AuditFileDAO(db_manager)
        
        # 获取筛选参数
        status = request.args.get('status', '')
        category_id = request.args.get('category_id', '')
        department_id = request.args.get('department_id', '')
        
        # 获取档案列表
        files = file_dao.get_audit_files(
            status=status if status else None,
            category_id=int(category_id) if category_id else None,
            department_id=int(department_id) if department_id else None,
            limit=100
        )
        
        # 获取分类和部门信息用于筛选
        from audit_system.database import FileCategoryDAO, DepartmentDAO
        category_dao = FileCategoryDAO(db_manager)
        dept_dao = DepartmentDAO(db_manager)
        
        categories = category_dao.get_all_categories()
        departments = dept_dao.get_all_departments()
        
        return render_template('files.html', 
                             files=files, 
                             categories=categories, 
                             departments=departments,
                             current_filters={'status': status, 'category_id': category_id, 'department_id': department_id})
    except Exception as e:
        print(f"获取档案列表失败: {e}")
        flash(f'获取档案列表失败: {str(e)}', 'error')
        return render_template('files.html', files=[], categories=[], departments=[], current_filters={})

@app.route('/files/new', methods=['GET', 'POST'])
@login_required
def new_file():
    """创建新档案"""
    # 简化权限检查
    if current_user.role not in ['admin', 'auditor']:
        flash('权限不足，无法创建档案', 'error')
        return redirect(url_for('files'))
    
    if request.method == 'POST':
        try:
            from audit_system.database import AuditFileDAO
            file_dao = AuditFileDAO(db_manager)
            
            # 获取表单数据
            file_number = request.form.get('file_number')
            title = request.form.get('title')
            category_id = request.form.get('category_id')
            department_id = request.form.get('department_id')
            description = request.form.get('description')
            priority = request.form.get('priority')
            audit_date = request.form.get('audit_date')
            
            if not all([file_number, title, category_id, department_id]):
                flash('档案编号、标题、分类、部门为必填项', 'error')
                return render_template('new_file.html')
            
            # 创建档案
            file_id = file_dao.create_audit_file(
                file_number=file_number,
                title=title,
                category_id=int(category_id),
                department_id=int(department_id),
                auditor_id=current_user.id,
                description=description,
                priority=priority,
                audit_date=audit_date if audit_date else None
            )
            
            # 处理文件上传
            uploaded_files = []
            if 'attachments' in request.files:
                files = request.files.getlist('attachments')
                for file in files:
                    if file and file.filename:
                        file_info = save_uploaded_file(file, file_id)
                        if file_info:
                            # 保存附件信息到数据库
                            try:
                                from audit_system.database import FileAttachmentDAO
                                attachment_dao = FileAttachmentDAO(db_manager)
                                attachment_id = attachment_dao.create_attachment(
                                    file_id=file_id,
                                    filename=file_info['filename'],
                                    original_name=file_info['original_name'],
                                    file_path=file_info['file_path'],
                                    file_size=file_info['file_size'],
                                    file_type=file_info['file_type'],
                                    uploaded_by=current_user.id,
                                    description=request.form.get('file_description', '')
                                )
                                uploaded_files.append(file_info['original_name'])
                            except Exception as e:
                                print(f"保存附件信息失败: {e}")
                                # 删除已上传的文件
                                try:
                                    os.remove(file_info['file_path'])
                                except:
                                    pass
            
            if uploaded_files:
                flash(f'档案创建成功！已上传 {len(uploaded_files)} 个附件: {", ".join(uploaded_files)}', 'success')
            else:
                flash('档案创建成功！', 'success')
            
            return redirect(url_for('files'))
            
        except Exception as e:
            flash(f'创建档案失败: {str(e)}', 'error')
    
    # GET请求，显示创建表单
    try:
        from audit_system.database import FileCategoryDAO, DepartmentDAO
        category_dao = FileCategoryDAO(db_manager)
        dept_dao = DepartmentDAO(db_manager)
        
        categories = category_dao.get_all_categories()
        departments = dept_dao.get_all_departments()
        
        return render_template('new_file.html', categories=categories, departments=departments)
    except Exception as e:
        flash(f'获取数据失败: {str(e)}', 'error')
        return render_template('new_file.html', categories=[], departments=[])

@app.route('/files/<int:file_id>')
@login_required
def view_file(file_id):
    """查看档案详情"""
    try:
        from audit_system.database import AuditFileDAO
        file_dao = AuditFileDAO(db_manager)
        
        file_info = file_dao.get_audit_file_by_id(file_id)
        if not file_info:
            flash('档案不存在', 'error')
            return redirect(url_for('files'))
        
        return render_template('view_file.html', file=file_info)
    except Exception as e:
        flash(f'获取档案信息失败: {str(e)}', 'error')
        return redirect(url_for('files'))

@app.route('/files/<int:file_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_file(file_id):
    """编辑档案"""
    try:
        from audit_system.database import AuditFileDAO
        file_dao = AuditFileDAO(db_manager)
        
        file_info = file_dao.get_audit_file_by_id(file_id)
        if not file_info:
            flash('档案不存在', 'error')
            return redirect(url_for('files'))
        
        # 权限检查：只有管理员、稽核员或档案创建者可以编辑
        if current_user.role not in ['admin', 'auditor'] and file_info['created_by'] != current_user.id:
            flash('权限不足，无法编辑此档案', 'error')
            return redirect(url_for('view_file', file_id=file_id))
        
        if request.method == 'POST':
            try:
                # 获取表单数据
                file_number = request.form.get('file_number')
                title = request.form.get('title')
                category_id = request.form.get('category_id')
                department_id = request.form.get('department_id')
                description = request.form.get('description')
                priority = request.form.get('priority')
                status = request.form.get('status')
                audit_date = request.form.get('audit_date')
                notes = request.form.get('notes')
                
                if not all([file_number, title, category_id, department_id]):
                    flash('档案编号、标题、分类、部门为必填项', 'error')
                    return render_template('edit_file.html', file=file_info, categories=[], departments=[])
                
                # 更新档案
                update_result = file_dao.update_audit_file(
                    file_id=file_id,
                    file_number=file_number,
                    title=title,
                    category_id=int(category_id),
                    department_id=int(department_id),
                    description=description,
                    priority=priority,
                    status=status,
                    audit_date=audit_date if audit_date else None,
                    notes=notes
                )
                
                if update_result:
                    # 处理新上传的附件
                    uploaded_files = []
                    if 'attachments' in request.files:
                        files = request.files.getlist('attachments')
                        for file in files:
                            if file and file.filename:
                                file_info_upload = save_uploaded_file(file, file_id)
                                if file_info_upload:
                                    # 保存附件信息到数据库
                                    try:
                                        from audit_system.database import FileAttachmentDAO
                                        attachment_dao = FileAttachmentDAO(db_manager)
                                        attachment_id = attachment_dao.create_attachment(
                                            file_id=file_id,
                                            filename=file_info_upload['filename'],
                                            original_name=file_info_upload['original_name'],
                                            file_path=file_info_upload['file_path'],
                                            file_size=file_info_upload['file_size'],
                                            file_type=file_info_upload['file_type'],
                                            uploaded_by=current_user.id,
                                            description=request.form.get('file_description', '')
                                        )
                                        uploaded_files.append(file_info_upload['original_name'])
                                    except Exception as e:
                                        print(f"保存附件信息失败: {e}")
                                        # 删除已上传的文件
                                        try:
                                            os.remove(file_info_upload['file_path'])
                                        except:
                                            pass
                    
                    if uploaded_files:
                        flash(f'档案更新成功！已上传 {len(uploaded_files)} 个新附件: {", ".join(uploaded_files)}', 'success')
                    else:
                        flash('档案更新成功！', 'success')
                    
                    return redirect(url_for('view_file', file_id=file_id))
                else:
                    flash('档案更新失败', 'error')
                    
            except Exception as e:
                flash(f'更新档案失败: {str(e)}', 'error')
        
        # GET请求，显示编辑表单
        try:
            from audit_system.database import FileCategoryDAO, DepartmentDAO, FileAttachmentDAO
            category_dao = FileCategoryDAO(db_manager)
            dept_dao = DepartmentDAO(db_manager)
            
            categories = category_dao.get_all_categories()
            departments = dept_dao.get_all_departments()
            
            # 尝试获取附件信息，如果失败则使用空列表
            try:
                attachment_dao = FileAttachmentDAO(db_manager)
                attachments = attachment_dao.get_attachments_by_file_id(file_id)
                file_info['attachments'] = attachments
            except Exception as e:
                print(f"获取附件信息失败: {e}")
                file_info['attachments'] = []
            
            return render_template('edit_file.html', 
                                 file=file_info, 
                                 categories=categories, 
                                 departments=departments)
        except Exception as e:
            flash(f'获取数据失败: {str(e)}', 'error')
            return render_template('edit_file.html', 
                                 file=file_info, 
                                 categories=[], 
                                 departments=[])
            
    except Exception as e:
        flash(f'获取档案信息失败: {str(e)}', 'error')
        return redirect(url_for('files'))

@app.route('/users')
@login_required
def users():
    """用户管理"""
    if current_user.role != 'admin':
        flash('权限不足，无法访问用户管理', 'error')
        return redirect(url_for('dashboard'))
    
    try:
        from audit_system.database import UserDAO
        user_dao = UserDAO(db_manager)
        users = user_dao.get_all_users()
        
        # 为每个用户添加部门名称
        for user in users:
            if user.get('department'):
                user['department_name'] = user['department']
            else:
                user['department_name'] = '未设置'
        
        return render_template('users.html', users=users)
    except Exception as e:
        flash(f'获取用户列表失败: {str(e)}', 'error')
        return render_template('users.html', users=[])

@app.route('/users/new', methods=['GET', 'POST'])
@login_required
def new_user():
    """创建新用户"""
    if current_user.role != 'admin':
        flash('权限不足，无法创建用户', 'error')
        return redirect(url_for('users'))
    
    if request.method == 'POST':
        try:
            username = request.form.get('username')
            password = request.form.get('password')
            real_name = request.form.get('real_name')
            email = request.form.get('email')
            role = request.form.get('role')
            department = request.form.get('department')
            phone = request.form.get('phone')
            
            if not all([username, password, real_name, email]):
                flash('用户名、密码、真实姓名、邮箱为必填项', 'error')
                return render_template('new_user.html')
            
            result = auth_manager.create_user(
                username=username,
                password=password,
                real_name=real_name,
                email=email,
                role=role,
                department=department,
                phone=phone,
                creator_id=current_user.id
            )
            
            if result['success']:
                flash('用户创建成功！', 'success')
                return redirect(url_for('users'))
            else:
                flash(result['message'], 'error')
                
        except Exception as e:
            flash(f'创建用户失败: {str(e)}', 'error')
    
    return render_template('new_user.html')

@app.route('/users/<int:user_id>')
@login_required
def view_user(user_id):
    """查看用户详情"""
    if current_user.role != 'admin':
        flash('权限不足，无法查看用户详情', 'error')
        return redirect(url_for('users'))
    
    try:
        from audit_system.database import UserDAO
        user_dao = UserDAO(db_manager)
        user = user_dao.get_user_by_id(user_id)
        
        if not user:
            flash('用户不存在', 'error')
            return redirect(url_for('users'))
        
        return render_template('view_user.html', user=user)
    except Exception as e:
        flash(f'获取用户信息失败: {str(e)}', 'error')
        return redirect(url_for('users'))

@app.route('/users/<int:user_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_user(user_id):
    """编辑用户"""
    if current_user.role != 'admin':
        flash('权限不足，无法编辑用户', 'error')
        return redirect(url_for('users'))
    
    try:
        from audit_system.database import UserDAO, DepartmentDAO
        user_dao = UserDAO(db_manager)
        dept_dao = DepartmentDAO(db_manager)
        
        user = user_dao.get_user_by_id(user_id)
        if not user:
            flash('用户不存在', 'error')
            return redirect(url_for('users'))
        
        if request.method == 'POST':
            try:
                # 获取表单数据
                real_name = request.form.get('real_name')
                email = request.form.get('email')
                role = request.form.get('role')
                department = request.form.get('department')
                status = request.form.get('status')
                phone = request.form.get('phone')
                new_password = request.form.get('new_password')
                confirm_password = request.form.get('confirm_password')
                
                if not all([real_name, email, role, status]):
                    flash('真实姓名、邮箱、角色、状态为必填项', 'error')
                    return render_template('edit_user.html', user=user, departments=[])
                
                # 密码验证
                if new_password:
                    if new_password != confirm_password:
                        flash('两次输入的密码不匹配', 'error')
                        return render_template('edit_user.html', user=user, departments=[])
                    
                    if len(new_password) < 6:
                        flash('新密码长度不能少于6位', 'error')
                        return render_template('edit_user.html', user=user, departments=[])
                
                # 更新用户信息
                update_data = {
                    'real_name': real_name,
                    'email': email,
                    'role': role,
                    'department': department,
                    'status': status,
                    'phone': phone
                }
                
                if new_password:
                    update_data['password'] = new_password
                
                result = user_dao.update_user(user_id, **update_data)
                
                if result:
                    flash('用户信息更新成功！', 'success')
                    return redirect(url_for('view_user', user_id=user_id))
                else:
                    flash('用户信息更新失败', 'error')
                    
            except Exception as e:
                flash(f'更新用户信息失败: {str(e)}', 'error')
        
        # GET请求，显示编辑表单
        try:
            departments = dept_dao.get_all_departments()
            return render_template('edit_user.html', user=user, departments=departments)
        except Exception as e:
            flash(f'获取部门信息失败: {str(e)}', 'error')
            return render_template('edit_user.html', user=user, departments=[])
            
    except Exception as e:
        flash(f'获取用户信息失败: {str(e)}', 'error')
        return redirect(url_for('users'))

@app.route('/users/<int:user_id>/delete', methods=['DELETE'])
@login_required
def delete_user(user_id):
    """删除用户"""
    if current_user.role != 'admin':
        return jsonify({'success': False, 'message': '权限不足'}), 403
    
    if current_user.id == user_id:
        return jsonify({'success': False, 'message': '不能删除自己的账户'}), 400
    
    try:
        from audit_system.database import UserDAO
        user_dao = UserDAO(db_manager)
        
        # 检查用户是否存在
        user = user_dao.get_user_by_id(user_id)
        if not user:
            return jsonify({'success': False, 'message': '用户不存在'}), 404
        
        # 删除用户（软删除）
        result = user_dao.delete_user(user_id)
        
        if result:
            return jsonify({'success': True, 'message': '用户删除成功'})
        else:
            return jsonify({'success': False, 'message': '删除失败'}), 500
            
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/logs')
@login_required
def logs():
    """操作日志"""
    if current_user.role not in ['admin', 'auditor']:
        flash('权限不足，无法查看日志', 'error')
        return redirect(url_for('dashboard'))
    
    try:
        from audit_system.database import AuditLogDAO
        log_dao = AuditLogDAO(db_manager)
        
        # 获取筛选参数
        action = request.args.get('action', '')
        user_id = request.args.get('user_id', '')
        date_from = request.args.get('date_from', '')
        date_to = request.args.get('date_to', '')
        
        # 获取日志列表
        logs = log_dao.get_system_logs(
            action=action if action else None,
            user_id=int(user_id) if user_id else None,
            date_from=date_from if date_from else None,
            date_to=date_to if date_to else None,
            limit=100
        )
        
        return render_template('logs.html', logs=logs)
    except Exception as e:
        flash(f'获取日志失败: {str(e)}', 'error')
        return render_template('logs.html', logs=[])

@app.route('/profile')
@login_required
def profile():
    """用户资料"""
    return render_template('profile.html')

@app.route('/change_password', methods=['GET', 'POST'])
@login_required
def change_password():
    """修改密码"""
    if request.method == 'POST':
        old_password = request.form.get('old_password')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')
        
        if not all([old_password, new_password, confirm_password]):
            flash('所有密码字段都不能为空', 'error')
            return render_template('change_password.html')
        
        if new_password != confirm_password:
            flash('新密码与确认密码不匹配', 'error')
            return render_template('change_password.html')
        
        if len(new_password) < 6:
            flash('新密码长度不能少于6位', 'error')
            return render_template('change_password.html')
        
        result = auth_manager.change_password(
            current_user.id, old_password, new_password
        )
        
        if result['success']:
            flash('密码修改成功！', 'success')
            return redirect(url_for('profile'))
        else:
            flash(result['message'], 'error')
    
    return render_template('change_password.html')

# 错误处理
@app.errorhandler(404)
def not_found_error(error):
    return render_template('404.html'), 404

@app.route('/download/<filename>')
@login_required
def download_file(filename):
    """下载文件"""
    try:
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename, as_attachment=True)
    except Exception as e:
        flash('文件下载失败', 'error')
        return redirect(url_for('files'))

@app.route('/attachments/<int:file_id>')
@login_required
def view_attachments(file_id):
    """查看档案附件"""
    try:
        from audit_system.database import FileAttachmentDAO
        attachment_dao = FileAttachmentDAO(db_manager)
        attachments = attachment_dao.get_attachments_by_file_id(file_id)
        return jsonify({'attachments': attachments})
    except Exception as e:
        return jsonify({'error': str(e)}, 500)

@app.route('/attachments/<int:attachment_id>/delete', methods=['DELETE'])
@login_required
def delete_attachment(attachment_id):
    """删除附件"""
    try:
        from audit_system.database import FileAttachmentDAO, AuditFileDAO
        attachment_dao = FileAttachmentDAO(db_manager)
        file_dao = AuditFileDAO(db_manager)
        
        # 获取附件信息
        attachment = attachment_dao.get_attachment_by_id(attachment_id)
        if not attachment:
            return jsonify({'success': False, 'message': '附件不存在'}), 404
        
        # 权限检查：只有管理员、稽核员或档案创建者可以删除附件
        file_info = file_dao.get_audit_file_by_id(attachment['file_id'])
        if not file_info:
            return jsonify({'success': False, 'message': '档案不存在'}), 404
        
        if current_user.role not in ['admin', 'auditor'] and file_info['created_by'] != current_user.id:
            return jsonify({'success': False, 'message': '权限不足'}), 403
        
        # 删除文件
        try:
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], attachment['filename'])
            if os.path.exists(file_path):
                os.remove(file_path)
        except Exception as e:
            print(f"删除文件失败: {e}")
        
        # 删除数据库记录
        delete_result = attachment_dao.delete_attachment(attachment_id)
        
        if delete_result:
            return jsonify({'success': True, 'message': '附件删除成功'})
        else:
            return jsonify({'success': False, 'message': '删除失败'}), 500
            
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.errorhandler(500)
def internal_error(error):
    return render_template('500.html'), 500

if __name__ == '__main__':
    print("🚀 启动稽核档案管理系统Web版本...")
    print("🌐 请在浏览器中访问: http://localhost:5000")
    print("🔐 默认管理员账户: admin / admin123")
    app.run(debug=True, host='0.0.0.0', port=5000) 