"""
股票预测系统 Web 应用
提供Web界面，支持用户登录、设置、实时数据展示等功能
"""
from flask import Flask, render_template, request, jsonify, session, redirect, url_for, send_from_directory
from flask_socketio import SocketIO, emit
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import os
import sys
import json
import threading
import queue
import traceback
import secrets
from typing import Dict, List, Any
from concurrent.futures import ThreadPoolExecutor, as_completed
import pandas as pd

# 添加项目根目录到路径
project_root = os.path.dirname(os.path.abspath(__file__))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# 导入项目模块
from utils.logger import get_logger

logger = get_logger(__name__)

# 导入配置
try:
    from config import BATCH_ANALYSIS_CONFIG
except ImportError:
    logger.warning("无法导入BATCH_ANALYSIS_CONFIG，使用默认配置")
    BATCH_ANALYSIS_CONFIG = {
        "max_workers": 3,
        "enable_parallel": True
    }

# 导入其他模块（使用try-except处理导入错误）
try:
    from utils.stock_prediction_db import StockPredictionDB
except ImportError as e:
    logger.warning(f"导入StockPredictionDB失败: {str(e)}")
    StockPredictionDB = None

try:
    from utils.db_connection import DatabaseConnection
except ImportError as e:
    logger.warning(f"导入DatabaseConnection失败: {str(e)}")
    DatabaseConnection = None

# 尝试导入新闻模块（可选）
try:
    from utils.news_task_manager import NewsTaskManager
    from utils.news_storage import NewsStorage
    NEWS_MODULE_AVAILABLE = True
except ImportError as e:
    NEWS_MODULE_AVAILABLE = False
    NewsTaskManager = None
    NewsStorage = None
    logger.warning(f"新闻模块导入失败: {str(e)}，新闻功能将不可用")

# 导入预测参数配置管理器
PredictionConfigManager = None
try:
    from utils.prediction_config_manager import PredictionConfigManager
    logger.info("PredictionConfigManager 导入成功")
except ImportError as e:
    logger.warning(f"导入PredictionConfigManager失败: {str(e)}，预测参数配置功能将不可用")

# 导入模型学习模块
ModelPerformanceEvaluator = None
ModelOptimizer = None
ModelParameterUpdater = None
BacktestEngine = None
BacktestVisualizer = None
try:
    from utils.model_performance_evaluator import ModelPerformanceEvaluator
    from utils.model_optimizer import ModelOptimizer
    from utils.model_parameter_updater import ModelParameterUpdater
    from utils.backtest_engine import BacktestEngine
    from visualizer.backtest_visualizer import BacktestVisualizer
    MODEL_LEARNING_AVAILABLE = True
    logger.info("模型学习模块导入成功")
except ImportError as e:
    MODEL_LEARNING_AVAILABLE = False
    logger.warning(f"导入模型学习模块失败: {str(e)}，模型学习功能将不可用")

# 导入数据源和预测模块（使用多种方式尝试导入）
import importlib.util

StockDataSource = None
try:
    # 方法1: 尝试普通导入
    from data_source.stock_data_source import StockDataSource
    logger.info("StockDataSource 导入成功（方法1：普通导入）")
except Exception as e1:
    try:
        # 方法2: 使用importlib导入（类似于main.py的方式）
        data_source_path = os.path.join(project_root, "data_source", "stock_data_source.py")
        if not os.path.exists(data_source_path):
            raise ImportError(f"文件不存在: {data_source_path}")
        
        data_source_spec = importlib.util.spec_from_file_location(
            "stock_data_source",
            data_source_path
        )
        if data_source_spec and data_source_spec.loader:
            data_source_module = importlib.util.module_from_spec(data_source_spec)
            data_source_spec.loader.exec_module(data_source_module)
            StockDataSource = data_source_module.StockDataSource
            logger.info("StockDataSource 导入成功（方法2：importlib导入）")
        else:
            raise ImportError("无法创建模块规范")
    except Exception as e2:
        logger.error(f"导入StockDataSource失败:")
        logger.error(f"  方法1（普通导入）错误: {type(e1).__name__}: {str(e1)}")
        logger.error(f"  方法2（importlib导入）错误: {type(e2).__name__}: {str(e2)}")
        logger.error(f"  详细错误信息:")
        logger.error(traceback.format_exc())
        StockDataSource = None

StockPredictor = None
try:
    # 方法1: 尝试普通导入
    from predictor.stock_predictor import StockPredictor
    logger.info("StockPredictor 导入成功（方法1：普通导入）")
except Exception as e1:
    try:
        # 方法2: 使用importlib导入
        predictor_path = os.path.join(project_root, "predictor", "stock_predictor.py")
        if not os.path.exists(predictor_path):
            raise ImportError(f"文件不存在: {predictor_path}")
        
        predictor_spec = importlib.util.spec_from_file_location(
            "stock_predictor",
            predictor_path
        )
        if predictor_spec and predictor_spec.loader:
            predictor_module = importlib.util.module_from_spec(predictor_spec)
            predictor_spec.loader.exec_module(predictor_module)
            StockPredictor = predictor_module.StockPredictor
            logger.info("StockPredictor 导入成功（方法2：importlib导入）")
        else:
            raise ImportError("无法创建模块规范")
    except Exception as e2:
        logger.error(f"导入StockPredictor失败:")
        logger.error(f"  方法1（普通导入）错误: {type(e1).__name__}: {str(e1)}")
        logger.error(f"  方法2（importlib导入）错误: {type(e2).__name__}: {str(e2)}")
        logger.error(f"  详细错误信息:")
        logger.error(traceback.format_exc())
        StockPredictor = None

PredictionVisualizer = None
try:
    # 方法1: 尝试普通导入
    from visualizer.prediction_visualizer import PredictionVisualizer
    logger.info("PredictionVisualizer 导入成功（方法1：普通导入）")
except Exception as e1:
    try:
        # 方法2: 使用importlib导入
        visualizer_path = os.path.join(project_root, "visualizer", "prediction_visualizer.py")
        if not os.path.exists(visualizer_path):
            raise ImportError(f"文件不存在: {visualizer_path}")
        
        visualizer_spec = importlib.util.spec_from_file_location(
            "prediction_visualizer",
            visualizer_path
        )
        if visualizer_spec and visualizer_spec.loader:
            visualizer_module = importlib.util.module_from_spec(visualizer_spec)
            visualizer_spec.loader.exec_module(visualizer_module)
            PredictionVisualizer = visualizer_module.PredictionVisualizer
            logger.info("PredictionVisualizer 导入成功（方法2：importlib导入）")
        else:
            raise ImportError("无法创建模块规范")
    except Exception as e2:
        logger.error(f"导入PredictionVisualizer失败:")
        logger.error(f"  方法1（普通导入）错误: {type(e1).__name__}: {str(e1)}")
        logger.error(f"  方法2（importlib导入）错误: {type(e2).__name__}: {str(e2)}")
        logger.error(f"  详细错误信息:")
        logger.error(traceback.format_exc())
        PredictionVisualizer = None

try:
    from predictor.realtime_trading_advisor import RealtimeTradingAdvisor
except ImportError as e:
    logger.warning(f"导入RealtimeTradingAdvisor失败: {str(e)}")
    RealtimeTradingAdvisor = None

try:
    from config import PREDICTION_CONFIG, TRADING_CONFIG
except ImportError as e:
    logger.warning(f"导入配置失败: {str(e)}")
    PREDICTION_CONFIG = {}
    TRADING_CONFIG = {}

try:
    from config_db import USE_DATABASE
except ImportError:
    USE_DATABASE = False

app = Flask(__name__, template_folder='templates', static_folder='static')

# 从环境变量读取SECRET_KEY，如果没有则生成随机密钥（生产环境必须设置）
SECRET_KEY = os.getenv('FLASK_SECRET_KEY')
if not SECRET_KEY:
    SECRET_KEY = secrets.token_hex(32)
    logger.warning("⚠️  使用随机生成的SECRET_KEY，生产环境请设置FLASK_SECRET_KEY环境变量")
else:
    logger.info("✅ 从环境变量读取SECRET_KEY")

app.config['SECRET_KEY'] = SECRET_KEY
app.config['SESSION_PERMANENT'] = False
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=24)

# CORS配置：从环境变量读取允许的来源（生产环境应限制）
cors_origins_env = os.getenv('CORS_ALLOWED_ORIGINS', '*')
if cors_origins_env == '*':
    logger.warning("⚠️  CORS允许所有来源，生产环境请设置CORS_ALLOWED_ORIGINS环境变量限制来源")
    allowed_origins = '*'
else:
    allowed_origins = [origin.strip() for origin in cors_origins_env.split(',')]
    logger.info(f"✅ CORS允许的来源: {allowed_origins}")

socketio = SocketIO(app, cors_allowed_origins=allowed_origins, async_mode='threading')

# 导入统一错误处理模块
try:
    from utils.exceptions import BaseAPIException
    from utils.error_handler import handle_api_error
    ERROR_HANDLER_AVAILABLE = True
except ImportError as e:
    logger.warning(f"导入错误处理模块失败: {str(e)}，将使用默认错误处理")
    ERROR_HANDLER_AVAILABLE = False
    BaseAPIException = Exception  # 使用基础Exception作为后备
    handle_api_error = lambda f: f  # 空装饰器


# 注册全局错误处理器
if ERROR_HANDLER_AVAILABLE:
    @app.errorhandler(BaseAPIException)
    def handle_base_api_exception(error):
        """处理自定义API异常"""
        logger.warning(f"API异常: {error.error_code} - {error.message}")
        return jsonify(error.to_dict()), error.status_code


@app.errorhandler(404)
def handle_not_found(error):
    """处理404错误"""
    if request.path.startswith('/api/'):
        return jsonify({
            'success': False,
            'error_code': 'NOT_FOUND',
            'message': '请求的资源不存在'
        }), 404
    return error


@app.errorhandler(500)
def handle_internal_error(error):
    """处理500错误"""
    logger.error(f"服务器内部错误: {str(error)}")
    logger.error(traceback.format_exc())
    
    if request.path.startswith('/api/'):
        return jsonify({
            'success': False,
            'error_code': 'INTERNAL_ERROR',
            'message': '服务器内部错误，请稍后重试'
        }), 500
    return error

# 用户管理器（延迟初始化）
user_manager = None

def get_user_manager():
    """获取用户管理器（延迟初始化）"""
    global user_manager
    if user_manager is None:
        try:
            from utils.user_manager import UserManager
            user_manager = UserManager()
            # 如果数据库启用且没有admin用户，创建默认admin用户（密码：admin@123）
            if USE_DATABASE:
                admin_user = user_manager.get_user_by_username('admin')
                if admin_user is None:
                    user_manager.create_user('admin', 'admin@123', 'admin')
                    logger.info("创建默认admin用户（密码：admin@123）")
                else:
                    # 如果admin用户已存在，更新密码为admin@123
                    user_manager.update_user(admin_user['id'], password='admin@123')
                    logger.info("已更新admin用户密码为：admin@123")
        except Exception as e:
            logger.warning(f"初始化用户管理器失败: {str(e)}")
            user_manager = None
    return user_manager

# 兼容性：保留USERS字典作为后备（如果数据库未启用）
USERS = {
    'admin': {
        'password_hash': generate_password_hash('admin123'),
        'username': 'admin',
        'role': 'admin'
    }
}

# 任务管理
task_queue = queue.Queue()
running_tasks = {}
task_lock = threading.Lock()
task_stop_flags = {}  # 任务停止标志 {task_id: bool}

# 新闻任务管理（延迟初始化，避免导入错误）
news_task_manager = None
news_storage = None

# 定时任务管理（延迟初始化，避免导入错误）
scheduled_task_manager = None

try:
    from utils.scheduled_task_manager import ScheduledTaskManager
    SCHEDULED_TASK_MANAGER_AVAILABLE = True
except ImportError as e:
    logger.warning(f"定时任务管理器模块不可用: {str(e)}")
    SCHEDULED_TASK_MANAGER_AVAILABLE = False
    ScheduledTaskManager = None

# 预测参数配置管理器（延迟初始化）
prediction_config_manager = None
PREDICTION_CONFIG_MANAGER_AVAILABLE = False
try:
    from utils.prediction_config_manager import PredictionConfigManager
    PREDICTION_CONFIG_MANAGER_AVAILABLE = True
except ImportError as e:
    logger.warning(f"预测参数配置管理器模块不可用: {str(e)}")
    PREDICTION_CONFIG_MANAGER_AVAILABLE = False
    PredictionConfigManager = None

def get_scheduled_task_manager():
    """获取定时任务管理器（延迟初始化）"""
    global scheduled_task_manager
    if not SCHEDULED_TASK_MANAGER_AVAILABLE:
        return None
    if scheduled_task_manager is None:
        try:
            scheduled_task_manager = ScheduledTaskManager()
        except Exception as e:
            logger.warning(f"初始化定时任务管理器失败: {str(e)}")
            scheduled_task_manager = None
    return scheduled_task_manager

def get_prediction_config_manager():
    """获取预测参数配置管理器（延迟初始化）"""
    global prediction_config_manager
    if not PREDICTION_CONFIG_MANAGER_AVAILABLE:
        return None
    if prediction_config_manager is None:
        try:
            prediction_config_manager = PredictionConfigManager()
        except Exception as e:
            logger.warning(f"初始化预测参数配置管理器失败: {str(e)}")
            prediction_config_manager = None
    return prediction_config_manager

def get_news_task_manager():
    """获取新闻任务管理器（延迟初始化）"""
    global news_task_manager
    if not NEWS_MODULE_AVAILABLE:
        return None
    if news_task_manager is None:
        try:
            news_task_manager = NewsTaskManager()
        except Exception as e:
            logger.warning(f"初始化新闻任务管理器失败: {str(e)}")
            news_task_manager = None
    return news_task_manager

# 新闻推送通知管理器（延迟初始化）
news_notification_manager = None
try:
    from utils.news_notification import NewsNotification
    NEWS_NOTIFICATION_AVAILABLE = True
except ImportError:
    NEWS_NOTIFICATION_AVAILABLE = False
    NewsNotification = None

def get_news_notification_manager():
    """获取新闻推送通知管理器（延迟初始化）"""
    global news_notification_manager
    if not NEWS_NOTIFICATION_AVAILABLE:
        return None
    if news_notification_manager is None:
        try:
            news_notification_manager = NewsNotification()
        except Exception as e:
            logger.warning(f"初始化新闻推送通知管理器失败: {str(e)}")
            news_notification_manager = None
    return news_notification_manager

# 备份管理器（延迟初始化）
backup_manager = None

def get_backup_manager():
    """获取备份管理器（延迟初始化）"""
    global backup_manager
    if backup_manager is None:
        try:
            from utils.backup_manager import BackupManager
            backup_manager = BackupManager()
        except Exception as e:
            logger.warning(f"初始化备份管理器失败: {str(e)}")
            backup_manager = None
    return backup_manager

def get_news_storage():
    """获取新闻存储管理器（延迟初始化）"""
    global news_storage
    if not NEWS_MODULE_AVAILABLE:
        return None
    if news_storage is None:
        try:
            news_storage = NewsStorage()
        except Exception as e:
            logger.warning(f"初始化新闻存储管理器失败: {str(e)}")
            news_storage = None
    return news_storage


@app.before_request
def check_session():
    """在每个请求前检查会话有效性（实现单点登录）"""
    # 排除不需要验证的端点
    excluded_endpoints = ['login', 'static', 'favicon']
    if request.endpoint and any(excluded in request.endpoint for excluded in excluded_endpoints):
        return None
    
    if 'user_id' in session and 'session_id' in session:
        um = get_user_manager()
        if um and USE_DATABASE:
            try:
                # 验证会话是否有效
                session_info = um.validate_session(session.get('session_id'))
                if not session_info:
                    # 会话无效，清除session
                    session.clear()
                    # 对于API请求，返回JSON响应
                    if request.path.startswith('/api/'):
                        return jsonify({'success': False, 'message': '请先登录', 'redirect': url_for('login')}), 401
                    # 对于页面请求，重定向到登录页
                    if request.endpoint and request.endpoint != 'login':
                        return redirect(url_for('login'))
            except Exception as e:
                # 如果验证过程出错（如数据库错误、表不存在等），记录错误但不清除session
                # 避免因数据库问题导致所有用户被踢出
                logger.error(f"会话验证过程出错: {str(e)}")
                logger.error(traceback.format_exc())
                # 如果表不存在，可以考虑自动创建，但不强制验证
                # 这里先记录错误，让用户继续访问（降级处理）
                pass


@app.route('/')
def index():
    """首页重定向到股票列表"""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return redirect(url_for('stock_list'))


# 导入限流器和审计日志
try:
    from utils.rate_limiter import get_rate_limiter
    from utils.audit_log import get_audit_logger
    from utils.system_monitor import get_system_monitor
    from utils.automated_backtest import get_automated_backtest
    RATE_LIMITER_AVAILABLE = True
    AUDIT_LOGGER_AVAILABLE = True
    SYSTEM_MONITOR_AVAILABLE = True
    AUTOMATED_BACKTEST_AVAILABLE = True
except ImportError as e:
    logger.warning(f"导入限流器/审计日志/系统监控模块失败: {str(e)}")
    RATE_LIMITER_AVAILABLE = False
    AUDIT_LOGGER_AVAILABLE = False
    SYSTEM_MONITOR_AVAILABLE = False
    AUTOMATED_BACKTEST_AVAILABLE = False

# 全局限流器和审计日志实例
rate_limiter = get_rate_limiter() if RATE_LIMITER_AVAILABLE else None
audit_logger = get_audit_logger() if AUDIT_LOGGER_AVAILABLE else None
system_monitor = get_system_monitor() if SYSTEM_MONITOR_AVAILABLE else None
automated_backtest = get_automated_backtest() if AUTOMATED_BACKTEST_AVAILABLE else None

# API限流装饰器
def rate_limit(max_per_minute: int = 60):
    """API访问频率限制装饰器"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            if rate_limiter:
                # 获取用户ID或IP地址作为限制key
                user_id = session.get('user_id', 'anonymous')
                ip_address = request.remote_addr
                limit_key = f"{user_id}_{ip_address}"
                
                # 检查是否超过限制
                allowed, info = rate_limiter.check_rate_limit(limit_key, limit=max_per_minute, window=60)
                
                if not allowed:
                    logger.warning(f"API访问频率超限: user_id={user_id}, ip={ip_address}, limit={max_per_minute}/min")
                    return jsonify({
                        'success': False,
                        'message': f'访问频率过快，请稍后再试。限制: {max_per_minute}次/分钟',
                        'rate_limit_info': info
                    }), 429  # Too Many Requests
                
                # 记录请求
                if audit_logger:
                    try:
                        audit_logger.log_operation(
                            user_id=user_id if user_id != 'anonymous' else 0,
                            operation_type='api_access',
                            resource_type=func.__name__,
                            ip_address=ip_address,
                            user_agent=request.headers.get('User-Agent'),
                            success=True
                        )
                    except:
                        pass
            
            return func(*args, **kwargs)
        wrapper.__name__ = func.__name__
        return wrapper
    return decorator


@app.route('/login', methods=['GET', 'POST'])
def login():
    """用户登录"""
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        um = get_user_manager()
        
        # 优先使用数据库用户管理
        if um and USE_DATABASE:
            if um.verify_password(username, password):
                user = um.get_user_by_username(username)
                if user:
                    # 生成唯一的session ID
                    session_id = secrets.token_urlsafe(32)
                    
                    # 创建会话（会自动使其他会话失效，实现单点登录）
                    ip_address = request.remote_addr
                    user_agent = request.headers.get('User-Agent', '')
                    um.create_session(user['id'], session_id, ip_address, user_agent)
                    
                    # 设置session
                    session['user_id'] = user['id']
                    session['username'] = username
                    session['session_id'] = session_id
                    session['role'] = user.get('role', 'user')
                    
                    # 记录登录审计日志
                    if audit_logger:
                        try:
                            audit_logger.log_operation(
                                user_id=user['id'],
                                operation_type='login',
                                resource_type='user',
                                resource_id=str(user['id']),
                                ip_address=request.remote_addr,
                                user_agent=request.headers.get('User-Agent'),
                                success=True
                            )
                        except Exception as e:
                            logger.debug(f"记录登录审计日志失败: {str(e)}")
                    
                    # 启动系统监控（如果未启动）
                    if system_monitor and not system_monitor._monitoring:
                        try:
                            system_monitor.start_monitoring(interval=300)  # 每5分钟监控一次
                            logger.info("系统监控已启动")
                        except Exception as e:
                            logger.warning(f"启动系统监控失败: {str(e)}")
                    
                    return jsonify({'success': True, 'message': '登录成功', 'redirect': url_for('stock_list')})
            
            return jsonify({'success': False, 'message': '用户名或密码错误'})
        else:
            # 后备：使用内存中的USERS字典
            if username in USERS and check_password_hash(USERS[username]['password_hash'], password):
                session['user_id'] = username
                session['username'] = username
                session['role'] = USERS[username].get('role', 'user')
                
                # 记录登录审计日志（后备模式）
                if audit_logger:
                    try:
                        audit_logger.log_operation(
                            user_id=0,  # 后备模式没有用户ID
                            operation_type='login',
                            resource_type='user',
                            ip_address=request.remote_addr,
                            user_agent=request.headers.get('User-Agent'),
                            success=True,
                            details={'mode': 'fallback', 'username': username}
                        )
                    except Exception as e:
                        logger.debug(f"记录登录审计日志失败: {str(e)}")
                
                return jsonify({'success': True, 'message': '登录成功', 'redirect': url_for('stock_list')})
            else:
                return jsonify({'success': False, 'message': '用户名或密码错误'})
    
    return render_template('login.html')


@app.route('/logout')
def logout():
    """用户退出"""
    # 记录退出审计日志
    user_id = session.get('user_id', 0)
    if audit_logger and user_id:
        try:
            audit_logger.log_operation(
                user_id=user_id if isinstance(user_id, int) else 0,
                operation_type='logout',
                resource_type='user',
                ip_address=request.remote_addr,
                user_agent=request.headers.get('User-Agent'),
                success=True
            )
        except Exception as e:
            logger.debug(f"记录退出审计日志失败: {str(e)}")
    
    # 使会话失效
    if 'session_id' in session:
        um = get_user_manager()
        if um and USE_DATABASE:
            um.invalidate_session(session.get('session_id'))
    
    session.clear()
    return redirect(url_for('login'))


@app.route('/stock_list')
def stock_list():
    """股票列表页面（主页面）"""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    # 读取stock_list.html并返回
    html_file = os.path.join(project_root, 'stock_list.html')
    if os.path.exists(html_file):
        with open(html_file, 'r', encoding='utf-8') as f:
            content = f.read()
        return content
    else:
        return "股票列表页面不存在", 404


@app.route('/settings')
def settings():
    """设置页面"""
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    # 检查是否为管理员，如果不是，重定向到股票列表
    role = session.get('role', 'user')
    if role != 'admin':
        return redirect(url_for('stock_list'))
    
    return render_template('settings.html')


@app.route('/api/user/info', methods=['GET'])
def api_get_user_info():
    """获取当前用户信息"""
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': '未登录'}), 401
    
    return jsonify({
        'success': True,
        'data': {
            'user_id': session.get('user_id'),
            'username': session.get('username'),
            'role': session.get('role', 'user')
        }
    })


# ==================== 用户管理API ====================

@app.route('/api/users', methods=['GET'])
def api_get_users():
    """获取用户列表（仅管理员）"""
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': '未登录'}), 401
    
    # 检查是否为管理员
    role = session.get('role', 'user')
    if role != 'admin':
        return jsonify({'success': False, 'message': '权限不足'}), 403
    
    try:
        um = get_user_manager()
        if not um or not USE_DATABASE:
            return jsonify({'success': False, 'message': '用户管理功能未启用'})
        
        users = um.get_all_users()
        # 移除敏感信息
        for user in users:
            if 'password_hash' in user:
                del user['password_hash']
        
        return jsonify({'success': True, 'data': users})
    except Exception as e:
        logger.error(f"获取用户列表失败: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/api/users', methods=['POST'])
def api_create_user():
    """创建新用户（仅管理员）"""
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': '未登录'}), 401
    
    # 检查是否为管理员
    role = session.get('role', 'user')
    if role != 'admin':
        return jsonify({'success': False, 'message': '权限不足'}), 403
    
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'message': '请求数据不能为空'}), 400
        
        # 安全地获取和清理数据
        username_raw = data.get('username')
        username = (username_raw if username_raw else '').strip() if isinstance(username_raw, str) else str(username_raw or '')
        
        password_raw = data.get('password')
        password = (password_raw if password_raw else '').strip() if isinstance(password_raw, str) else str(password_raw or '')
        
        role_raw = data.get('role', 'user')
        if isinstance(role_raw, str):
            role = role_raw.strip()
        else:
            role = 'user'
        
        email_raw = data.get('email')
        if email_raw is None:
            email = None
        elif isinstance(email_raw, str):
            email = email_raw.strip() or None
        else:
            email = None
        
        if not username or not password:
            return jsonify({'success': False, 'message': '用户名和密码不能为空'}), 400
        
        if len(password) < 6:
            return jsonify({'success': False, 'message': '密码长度至少6位'}), 400
        
        if role not in ['admin', 'user']:
            return jsonify({'success': False, 'message': '角色必须是admin或user'}), 400
        
        um = get_user_manager()
        if not um or not USE_DATABASE:
            return jsonify({'success': False, 'message': '用户管理功能未启用'})
        
        user_id = um.create_user(username, password, role, email)
        if user_id:
            return jsonify({'success': True, 'message': '用户创建成功', 'user_id': user_id})
        else:
            return jsonify({'success': False, 'message': '用户创建失败，用户名可能已存在'}), 400
            
    except Exception as e:
        logger.error(f"创建用户失败: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/api/users/<int:user_id>', methods=['PUT'])
def api_update_user(user_id):
    """更新用户信息（仅管理员）"""
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': '未登录'}), 401
    
    # 检查是否为管理员
    role = session.get('role', 'user')
    if role != 'admin':
        return jsonify({'success': False, 'message': '权限不足'}), 403
    
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'message': '请求数据不能为空'}), 400
        
        updates = {}
        
        if 'password' in data and data['password']:
            password = (data['password'] or '').strip()
            if password and len(password) < 6:
                return jsonify({'success': False, 'message': '密码长度至少6位'}), 400
            if password:
                updates['password'] = password
        
        if 'role' in data:
            role_raw = data['role']
            role = (role_raw if role_raw else 'user').strip() if isinstance(role_raw, str) else 'user'
            if role not in ['admin', 'user']:
                return jsonify({'success': False, 'message': '角色必须是admin或user'}), 400
            updates['role'] = role
        
        if 'email' in data:
            email_raw = data['email']
            if email_raw:
                email = (email_raw if isinstance(email_raw, str) else '').strip() or None
            else:
                email = None
            updates['email'] = email
        
        if 'is_active' in data:
            updates['is_active'] = bool(data['is_active'])
        
        if not updates:
            return jsonify({'success': False, 'message': '没有要更新的字段'}), 400
        
        um = get_user_manager()
        if not um or not USE_DATABASE:
            return jsonify({'success': False, 'message': '用户管理功能未启用'})
        
        if um.update_user(user_id, **updates):
            return jsonify({'success': True, 'message': '用户更新成功'})
        else:
            return jsonify({'success': False, 'message': '用户更新失败'}), 400
            
    except Exception as e:
        logger.error(f"更新用户失败: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/api/users/<int:user_id>', methods=['DELETE'])
def api_delete_user(user_id):
    """删除用户（仅管理员）"""
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': '未登录'}), 401
    
    # 检查是否为管理员
    role = session.get('role', 'user')
    if role != 'admin':
        return jsonify({'success': False, 'message': '权限不足'}), 403
    
    # 不能删除自己
    current_user_id = session.get('user_id')
    if isinstance(current_user_id, int) and current_user_id == user_id:
        return jsonify({'success': False, 'message': '不能删除自己的账户'}), 400
    
    try:
        um = get_user_manager()
        if not um or not USE_DATABASE:
            return jsonify({'success': False, 'message': '用户管理功能未启用'})
        
        if um.delete_user(user_id):
            return jsonify({'success': True, 'message': '用户删除成功'})
        else:
            return jsonify({'success': False, 'message': '用户删除失败'}), 400
            
    except Exception as e:
        logger.error(f"删除用户失败: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/api/stocks', methods=['GET'])
@rate_limit(max_per_minute=120)  # 每分钟最多120次请求
def api_get_stocks():
    """获取股票列表API（只返回当日预测数据）"""
    try:
        # 获取预测类型参数（after_close=收盘-明日，before_close=未收盘-明天）
        prediction_type = request.args.get('prediction_type', 'after_close')
        
        # 获取搜索条件参数
        prediction_direction = request.args.get('prediction_direction', '')  # 预测类型：上涨、下跌、震荡
        confidence_min = request.args.get('confidence_min', '')  # 最小置信度（0-1之间）
        search_keyword = request.args.get('search', '')  # 搜索关键词（股票代码或名称）
        
        # 获取分页参数
        page = int(request.args.get('page', 1))  # 页码，从1开始
        page_size = int(request.args.get('page_size', 100))  # 每页数量，默认100
        
        db = StockPredictionDB()
        
        # 获取今天的日期和明天的日期
        today = datetime.now().strftime('%Y-%m-%d')
        tomorrow = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')
        
        # 对于 before_close 类型，不去重，返回所有当日的预测记录（不需要根据target_date过滤）
        if prediction_type == 'before_close':
            # 直接获取所有当日的 before_close 类型预测记录（不去重）
            records = db.get_predictions(symbol=None, limit=1000, order_by='prediction_time DESC', prediction_type='before_close')
            # 过滤：只保留当日的 before_close 类型记录（根据prediction_date，不是target_date）
            filtered_records = []
            for record in records:
                # 检查预测日期（prediction_date），只保留当日的预测
                prediction_date = record.get('prediction_date', '')
                if prediction_date:
                    if isinstance(prediction_date, (datetime, pd.Timestamp)):
                        prediction_date_str = prediction_date.strftime('%Y-%m-%d')
                    else:
                        prediction_date_str = str(prediction_date)
                        if ' ' in prediction_date_str:
                            prediction_date_str = prediction_date_str.split(' ')[0]
                    
                    if prediction_date_str != today:
                        continue
                
                filtered_records.append(record)
            
            unique_records = filtered_records
        else:
            # 对于 after_close 类型（收盘-明日）：
            # 1. 需要去重（每个股票只保留最新的一条）
            # 2. 只显示 target_date 为明日的预测
            # 3. 如果没有明日的数据则不显示
            
            # 获取所有 after_close 类型的预测记录
            records = db.get_predictions(symbol=None, limit=1000, order_by='prediction_time DESC', prediction_type='after_close')
            
            # 过滤：只保留 target_date 为明日的记录
            tomorrow_records = []
            for record in records:
                target_date = record.get('target_date', '')
                if target_date:
                    # 如果是 datetime 对象，转换为字符串
                    if isinstance(target_date, (datetime, pd.Timestamp)):
                        target_date_str = target_date.strftime('%Y-%m-%d')
                    else:
                        target_date_str = str(target_date)
                        # 如果是其他格式，尝试提取日期部分
                        if ' ' in target_date_str:
                            target_date_str = target_date_str.split(' ')[0]
                    
                    # 只保留目标日期为明日的记录
                    if target_date_str != tomorrow:
                        continue
                
                tomorrow_records.append(record)
            
            # 去重：每个股票只保留最新的一条（按prediction_time排序，取最新的）
            symbol_to_latest = {}
            for record in tomorrow_records:
                symbol = str(record.get('symbol', '')).strip().zfill(6)
                if not symbol:
                    continue
                
                prediction_time = record.get('prediction_time', '')
                if symbol not in symbol_to_latest:
                    symbol_to_latest[symbol] = record
                else:
                    # 比较prediction_time，保留最新的
                    existing_time = symbol_to_latest[symbol].get('prediction_time', '')
                    if prediction_time and existing_time:
                        # 转换为datetime比较
                        try:
                            if isinstance(prediction_time, str):
                                pred_dt = datetime.strptime(prediction_time, '%Y-%m-%d %H:%M:%S')
                            else:
                                pred_dt = prediction_time
                            
                            if isinstance(existing_time, str):
                                exist_dt = datetime.strptime(existing_time, '%Y-%m-%d %H:%M:%S')
                            else:
                                exist_dt = existing_time
                            
                            if pred_dt > exist_dt:
                                symbol_to_latest[symbol] = record
                        except:
                            # 如果时间解析失败，保留现有的
                            pass
            
            unique_records = list(symbol_to_latest.values())
        
        # 应用搜索条件过滤
        filtered_records = []
        for record in unique_records:
            # 搜索关键词过滤（股票代码或名称）
            if search_keyword:
                symbol = str(record.get('symbol', '')).strip()
                name = str(record.get('name', '')).strip()
                keyword = search_keyword.strip().upper()
                if keyword not in symbol.upper() and keyword not in name.upper():
                    continue
            
            # 预测类型过滤（上涨、下跌、震荡）
            if prediction_direction:
                record_prediction = str(record.get('prediction', '')).strip()
                if record_prediction != prediction_direction:
                    continue
            
            # 置信度过滤
            if confidence_min:
                try:
                    min_confidence = float(confidence_min)
                    record_confidence = float(record.get('confidence', 0) or 0)
                    if record_confidence < min_confidence:
                        continue
                except (ValueError, TypeError):
                    pass
            
            filtered_records.append(record)
        
        # 计算分页
        total_count = len(filtered_records)
        total_pages = (total_count + page_size - 1) // page_size  # 向上取整
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        paged_records = filtered_records[start_idx:end_idx]
        
        # 转换为前端需要的格式
        stocks = []
        for record in paged_records:
            # 转换文件路径为相对路径
            png_file = record.get('png_file', '')
            interactive_html = record.get('interactive_html', '')
            full_report_html = record.get('full_report_html', '')
            
            # 如果是绝对路径，提取文件名
            if png_file and os.path.isabs(png_file):
                png_file = os.path.basename(png_file)
            if interactive_html and os.path.isabs(interactive_html):
                interactive_html = os.path.basename(interactive_html)
            if full_report_html and os.path.isabs(full_report_html):
                full_report_html = os.path.basename(full_report_html)
            
            # 格式化日期字段，确保返回 YYYY-MM-DD 格式
            prediction_date = record.get('prediction_date', '')
            target_date = record.get('target_date', '')
            
            # 如果是 datetime 对象，转换为字符串
            if prediction_date and isinstance(prediction_date, (datetime, pd.Timestamp)):
                prediction_date = prediction_date.strftime('%Y-%m-%d')
            elif prediction_date:
                prediction_date = str(prediction_date)
                # 如果是其他格式，尝试提取日期部分
                if ' ' in prediction_date:
                    prediction_date = prediction_date.split(' ')[0]
            
            if target_date and isinstance(target_date, (datetime, pd.Timestamp)):
                target_date = target_date.strftime('%Y-%m-%d')
            elif target_date:
                target_date = str(target_date)
                # 如果是其他格式，尝试提取日期部分
                if ' ' in target_date:
                    target_date = target_date.split(' ')[0]
            
            stocks.append({
                'symbol': record.get('symbol', ''),
                'name': record.get('name', ''),
                'prediction_date': prediction_date,
                'target_date': target_date,
                'current_price': float(record.get('current_price', 0)) if record.get('current_price') else 0,
                'predicted_close_price': float(record.get('predicted_close_price', 0)) if record.get('predicted_close_price') else None,
                'predicted_change_pct': float(record.get('predicted_change_pct', 0)) if record.get('predicted_change_pct') is not None else None,
                'prediction': record.get('prediction', '震荡'),
                'up_probability': float(record.get('up_probability', 0)) if record.get('up_probability') else 0,
                'down_probability': float(record.get('down_probability', 0)) if record.get('down_probability') else 0,
                'confidence': float(record.get('confidence', 0)) if record.get('confidence') else 0,
                'prediction_time': str(record.get('prediction_time', '')),
                'png_file': png_file,
                'interactive_html': interactive_html,  # 交互式图表路径
                'full_report_html': full_report_html,
                'summary': record.get('summary', '')
            })
        
        return jsonify({
            'success': True, 
            'data': stocks, 
            'total': total_count,
            'page': page,
            'page_size': page_size,
            'total_pages': total_pages
        })
    except Exception as e:
        logger.error(f"获取股票列表失败: {str(e)}")
        return jsonify({'success': False, 'message': str(e), 'data': [], 'total': 0})


def is_market_open():
    """
    判断A股市场是否开盘
    
    Returns:
        dict: {
            'is_open': bool,  # 是否开盘
            'is_trading': bool,  # 是否在交易时段（排除午休）
            'message': str  # 状态描述
        }
    """
    now = datetime.now()
    current_time = now.time()
    
    # A股交易时间：上午 9:30-11:30，下午 13:00-15:00
    morning_start = datetime.strptime('09:30', '%H:%M').time()
    morning_end = datetime.strptime('11:30', '%H:%M').time()
    afternoon_start = datetime.strptime('13:00', '%H:%M').time()
    afternoon_end = datetime.strptime('15:00', '%H:%M').time()
    
    # 判断是否为交易日（简单判断：周一到周五）
    weekday = now.weekday()  # 0=Monday, 6=Sunday
    
    if weekday >= 5:  # 周六、周日
        return {
            'is_open': False,
            'is_trading': False,
            'message': '周末休市'
        }
    
    # 判断是否在交易时段
    if morning_start <= current_time <= morning_end:
        return {
            'is_open': True,
            'is_trading': True,
            'message': '交易中'
        }
    elif afternoon_start <= current_time <= afternoon_end:
        return {
            'is_open': True,
            'is_trading': True,
            'message': '交易中'
        }
    elif current_time < morning_start:
        return {
            'is_open': False,
            'is_trading': False,
            'message': '未开盘'
        }
    elif morning_end < current_time < afternoon_start:
        return {
            'is_open': False,
            'is_trading': False,
            'message': '午间休市'
        }
    else:  # current_time > afternoon_end
        return {
            'is_open': False,
            'is_trading': False,
            'message': '已收盘'
        }


@app.route('/api/market/index', methods=['GET'])
def api_get_market_index():
    """获取大盘指数实时数据（使用Tushare）"""
    # 检查用户是否已登录
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': '请先登录', 'data': {}})
    
    # 检查市场是否开盘
    market_status = is_market_open()
    is_closed = not market_status['is_trading']
    
    try:
        # 尝试导入Tushare
        try:
            import tushare as ts
        except ImportError:
            logger.error("Tushare库未安装，请运行: pip install tushare")
            return jsonify({'success': False, 'message': 'Tushare库未安装', 'data': {}})
        
        # 获取Tushare token
        try:
            from config import TUSHARE_TOKEN
            if not TUSHARE_TOKEN:
                logger.error("Tushare token未配置")
                return jsonify({'success': False, 'message': 'Tushare token未配置', 'data': {}})
            ts.set_token(TUSHARE_TOKEN)
            pro = ts.pro_api()
        except Exception as e:
            logger.error(f"Tushare初始化失败: {str(e)}")
            return jsonify({'success': False, 'message': f'Tushare初始化失败: {str(e)}', 'data': {}})
        
        # 定义要获取的指数列表（使用Tushare格式）
        # 注释掉中证500(000905.SH)，因为权限不足
        indices = {
            '000001.SH': '上证指数',
            '399001.SZ': '深证成指',
            '000300.SH': '沪深300',
            # '000905.SH': '中证500',  # 已注释：权限不足，无法获取
            '399006.SZ': '创业板指'
        }
        
        market_data = {}
        trade_date = datetime.now().strftime('%Y%m%d')
        
        for tushare_code, name in indices.items():
            try:
                # 使用Tushare获取指数实时行情
                # 先尝试获取今天的数据
                try:
                    df = pro.index_daily(ts_code=tushare_code, trade_date=trade_date)
                    if df is None or df.empty:
                        df = None
                except Exception as e:
                    # 如果今天没有数据（非交易日或数据未更新），获取最近的数据
                    logger.debug(f"获取指数 {name}({tushare_code}) 当天数据失败: {str(e)}")
                    df = None
                
                # 如果当天数据不存在，获取最近交易日数据
                if df is None or df.empty:
                    df = pro.index_daily(ts_code=tushare_code, limit=2)
                    if df is None or df.empty:
                        logger.warning(f"无法获取指数 {name}({tushare_code}) 的数据")
                        continue
                    # 使用最新一条数据
                    latest = df.iloc[0]
                    # 如果有两条数据，用前一条计算涨跌
                    prev = df.iloc[1] if len(df) > 1 else latest
                else:
                    latest = df.iloc[0]
                    # 获取前一个交易日数据用于计算涨跌
                    try:
                        prev_df = pro.index_daily(ts_code=tushare_code, limit=2)
                        if prev_df is not None and not prev_df.empty and len(prev_df) > 1:
                            prev = prev_df.iloc[1]
                        else:
                            prev = latest
                    except:
                        prev = latest
                
                # 计算涨跌
                current = float(latest['close'])
                prev_close = float(prev['close']) if prev is not None and 'close' in prev else current
                change = current - prev_close
                change_pct = (change / prev_close * 100) if prev_close > 0 else 0
                
                market_data[tushare_code] = {
                    'name': name,
                    'current': current,
                    'change': change,
                    'change_pct': change_pct,
                    'volume': float(latest.get('vol', 0)),
                    'amount': float(latest.get('amount', 0))
                }
                
            except Exception as e:
                error_msg = str(e)
                # 屏蔽中证500的错误提示（权限不足）
                if tushare_code == '000905.SH':
                    # 中证500权限不足，静默跳过
                    continue
                
                # 屏蔽权限相关的错误提示
                if '权限' in error_msg or 'permission' in error_msg.lower() or '访问权限' in error_msg or '接口访问权限' in error_msg:
                    logger.debug(f"获取指数 {name}({tushare_code}) 数据失败（权限问题，已屏蔽）")
                    continue
                
                # 其他指数的错误才记录警告
                logger.warning(f"获取指数 {name}({tushare_code}) 数据失败: {error_msg}")
                # 如果Tushare失败，尝试使用akshare作为备用
                try:
                    if StockDataSource is not None:
                        data_source = StockDataSource()
                        # 转换Tushare代码格式到akshare格式
                        akshare_code = tushare_code.replace('.SH', '').replace('.SZ', '')
                        if tushare_code.endswith('.SH'):
                            akshare_code = 'sh' + akshare_code
                        else:
                            akshare_code = 'sz' + akshare_code
                        
                        index_data = data_source.get_market_index_data(akshare_code, days=2)
                        if not index_data.empty:
                            last_row = index_data.iloc[-1]
                            prev_row = index_data.iloc[-2] if len(index_data) > 1 else last_row
                            change = last_row['close'] - prev_row['close']
                            change_pct = (change / prev_row['close']) * 100 if prev_row['close'] > 0 else 0
                            market_data[tushare_code] = {
                                'name': name,
                                'current': float(last_row['close']),
                                'change': float(change),
                                'change_pct': float(change_pct),
                                'volume': float(last_row.get('volume', 0)),
                                'amount': 0
                            }
                except Exception as e2:
                    logger.warning(f"备用方法获取指数 {name} 数据也失败: {str(e2)}")
        
        # 返回数据，如果收盘则标记为已收盘
        return jsonify({
            'success': True, 
            'data': market_data,
            'market_closed': is_closed,
            'message': market_status['message'] if is_closed else None
        })
    except Exception as e:
        logger.error(f"获取大盘指数数据失败: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({'success': False, 'message': str(e), 'data': {}})


@app.route('/api/tasks/start', methods=['POST'])
def api_start_task():
    """启动股票分析任务"""
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': '请先登录'})
    
    # 检查必需的模块是否已导入
    if StockDataSource is None:
        logger.error("StockDataSource 模块未导入，无法启动任务")
        return jsonify({'success': False, 'message': 'StockDataSource 模块未导入，无法启动任务。请检查模块导入错误。'})
    
    if StockPredictor is None:
        logger.error("StockPredictor 模块未导入，无法启动任务")
        return jsonify({'success': False, 'message': 'StockPredictor 模块未导入，无法启动任务。请检查模块导入错误。'})
    
    if PredictionVisualizer is None:
        logger.error("PredictionVisualizer 模块未导入，无法启动任务")
        return jsonify({'success': False, 'message': 'PredictionVisualizer 模块未导入，无法启动任务。请检查模块导入错误。'})
    
    try:
        data = request.get_json()
        if not data:
            return jsonify({'success': False, 'message': '请求数据不能为空'}), 400
        
        # 获取分析类型
        analysis_type = data.get('analysis_type', 'by_count')  # 'by_count' 或 'by_symbols'
        
        # 根据分析类型获取和验证参数
        limit = None
        sort_type = 'turnover'
        symbols = None
        
        if analysis_type == 'by_count':
            # 按数量模式
            limit = data.get('limit')  # None表示全部，否则为具体数量
            sort_type = data.get('sort_type', 'turnover')  # 'turnover' 或 'random'
            
            # 验证参数
            if limit is not None:
                try:
                    limit = int(limit)
                    if limit < 0 or limit > 10000:
                        return jsonify({'success': False, 'message': '分析数量必须在0-10000之间'}), 400
                    if limit == 0:
                        limit = None  # 0表示全部
                except (ValueError, TypeError):
                    return jsonify({'success': False, 'message': '分析数量必须是有效的数字'}), 400
            
            if sort_type not in ['turnover', 'random']:
                return jsonify({'success': False, 'message': '排序方式必须是turnover或random'}), 400
        elif analysis_type == 'by_symbols':
            # 按股票模式
            symbols = data.get('symbols')
            if not symbols or not isinstance(symbols, list):
                return jsonify({'success': False, 'message': '股票代码列表不能为空'}), 400
            
            if len(symbols) > 50:
                return jsonify({'success': False, 'message': '最多只能输入50个股票代码'}), 400
            
            # 验证股票代码格式（6位数字）
            invalid_symbols = [s for s in symbols if not isinstance(s, str) or not s.isdigit() or len(s) != 6]
            if invalid_symbols:
                return jsonify({'success': False, 'message': f'以下股票代码格式不正确（应为6位数字）：{", ".join(invalid_symbols[:5])}'}), 400
        else:
            return jsonify({'success': False, 'message': '分析类型必须是by_count或by_symbols'}), 400
        
        # 创建任务
        task_id = f"task_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        start_time = datetime.now()
        
        # 获取当前用户信息
        user_id = session.get('user_id')
        username = session.get('username', '未知')
        
        # 记录任务创建信息
        if analysis_type == 'by_count':
            limit_text = f"{limit}只" if limit else "全部"
            sort_text = "随机排序" if sort_type == 'random' else "按交易量排序"
            logger.info(f"【API请求】创建股票分析任务（按数量）")
            logger.info(f"  - 任务ID: {task_id}")
            logger.info(f"  - 执行人: {username} (ID: {user_id})")
            logger.info(f"  - 分析数量: {limit_text}")
            logger.info(f"  - 排序方式: {sort_text}")
        else:
            logger.info(f"【API请求】创建股票分析任务（按股票）")
            logger.info(f"  - 任务ID: {task_id}")
            logger.info(f"  - 执行人: {username} (ID: {user_id})")
            logger.info(f"  - 股票代码: {', '.join(symbols)}")
            logger.info(f"  - 股票数量: {len(symbols)}只")
        logger.info(f"  - 启动时间: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        
        # 在新线程中运行任务
        thread = threading.Thread(
            target=run_stock_analysis_task,
            args=(task_id, limit, sort_type, symbols),
            daemon=True,
            name=f"StockAnalysis-{task_id}"
        )
        thread.start()
        
        with task_lock:
            running_tasks[task_id] = {
                'id': task_id,
                'user_id': user_id,
                'username': username,
                'analysis_type': analysis_type,
                'limit': limit,
                'sort_type': sort_type,
                'symbols': symbols,
                'status': 'running',
                'progress': 0,
                'total': 0,  # 将在任务开始时更新
                'success_count': 0,
                'fail_count': 0,
                'start_time': start_time.isoformat(),
                'current_stock': None
            }
            task_stop_flags[task_id] = False  # 初始化停止标志
        
        logger.info(f"【API请求】任务已启动，线程名称: StockAnalysis-{task_id}")
        socketio.emit('task_started', {'task_id': task_id}, namespace='/')
        
        return jsonify({'success': True, 'task_id': task_id})
    except Exception as e:
        logger.error(f"启动任务失败: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({'success': False, 'message': str(e)})


@app.route('/api/tasks/<task_id>', methods=['GET'])
def api_get_task_status(task_id):
    """获取任务状态"""
    with task_lock:
        task = running_tasks.get(task_id)
        if task:
            return jsonify({'success': True, 'data': task})
        else:
            return jsonify({'success': False, 'message': '任务不存在'})


@app.route('/api/tasks', methods=['GET'])
def api_get_all_tasks():
    """获取所有任务列表（运行中的任务）"""
    with task_lock:
        tasks = list(running_tasks.values())
        return jsonify({'success': True, 'data': tasks})


@app.route('/api/tasks/<task_id>/stop', methods=['POST'])
def api_stop_task(task_id):
    """停止指定的分析任务"""
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': '请先登录'})
    
    try:
        with task_lock:
            if task_id not in running_tasks:
                return jsonify({'success': False, 'message': '任务不存在或已结束'})
            
            task = running_tasks[task_id]
            if task['status'] not in ['running']:
                return jsonify({'success': False, 'message': f"任务状态为 {task['status']}，无法停止"})
            
            # 设置停止标志
            task_stop_flags[task_id] = True
            task['status'] = 'cancelled'
            
            logger.info(f"【任务停止】任务 {task_id} 收到停止请求")
        
        socketio.emit('task_stopped', {'task_id': task_id}, namespace='/')
        
        return jsonify({'success': True, 'message': '任务停止请求已发送'})
    except Exception as e:
        logger.error(f"停止任务失败: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({'success': False, 'message': str(e)})


@app.route('/api/tasks/history', methods=['GET'])
def api_get_task_history():
    """获取任务历史记录列表"""
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': '请先登录'})
    
    try:
        from utils.db_connection import DatabaseConnection
        from config_db import USE_DATABASE, DB_CONFIG
        
        if not USE_DATABASE:
            return jsonify({'success': False, 'message': '数据库未启用', 'data': [], 'total': 0})
        
        # 检查并创建 analysis_tasks 表（如果不存在）
        try:
            check_table_sql = """
                SELECT COUNT(*) as count 
                FROM information_schema.tables 
                WHERE table_schema = %s AND table_name = 'analysis_tasks'
            """
            result = DatabaseConnection.execute_query(check_table_sql, (DB_CONFIG.get('database', 'stock_data'),))
            table_exists = result and len(result) > 0 and result[0].get('count', 0) > 0
            
            if not table_exists:
                logger.warning("analysis_tasks 表不存在，正在自动创建...")
                create_table_sql = """
                    CREATE TABLE IF NOT EXISTS `analysis_tasks` (
                        `id` BIGINT AUTO_INCREMENT PRIMARY KEY,
                        `task_id` VARCHAR(100) NOT NULL COMMENT '任务ID',
                        `user_id` INT DEFAULT NULL COMMENT '执行用户ID',
                        `username` VARCHAR(50) DEFAULT NULL COMMENT '执行用户名',
                        `analysis_type` VARCHAR(20) DEFAULT 'by_count' COMMENT '分析类型（by_count=按数量, by_symbols=按股票）',
                        `limit_count` INT DEFAULT NULL COMMENT '分析数量（NULL表示全部，仅在按数量模式时使用）',
                        `sort_type` VARCHAR(20) DEFAULT NULL COMMENT '排序方式（turnover/random，仅在按数量模式时使用）',
                        `symbols` TEXT DEFAULT NULL COMMENT '股票代码列表（JSON格式，仅在按股票模式时使用）',
                        `status` VARCHAR(20) DEFAULT NULL COMMENT '任务状态（running/completed/cancelled/failed）',
                        `total_stocks` INT DEFAULT 0 COMMENT '总股票数',
                        `success_count` INT DEFAULT 0 COMMENT '成功数量',
                        `fail_count` INT DEFAULT 0 COMMENT '失败数量',
                        `progress` INT DEFAULT 0 COMMENT '当前进度',
                        `start_time` DATETIME DEFAULT NULL COMMENT '开始时间',
                        `end_time` DATETIME DEFAULT NULL COMMENT '结束时间',
                        `duration_seconds` INT DEFAULT NULL COMMENT '耗时（秒）',
                        `error_message` TEXT DEFAULT NULL COMMENT '错误信息',
                        `created_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
                        `updated_at` TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
                        UNIQUE KEY `uk_task_id` (`task_id`),
                        INDEX `idx_user_id` (`user_id`),
                        INDEX `idx_start_time` (`start_time`),
                        INDEX `idx_status` (`status`)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='股票分析任务历史表'
                """
                # 执行创建表语句（CREATE TABLE 是 DDL，不需要参数化查询）
                conn = DatabaseConnection.get_connection()
                if conn:
                    try:
                        with conn.cursor() as cursor:
                            cursor.execute(create_table_sql)
                        # 确保提交
                        conn.commit()
                        logger.info("analysis_tasks 表创建成功")
                    except Exception as create_error:
                        error_msg = str(create_error)
                        # 如果是表已存在的错误，不算失败
                        if 'already exists' in error_msg.lower() or 'Duplicate table' in error_msg:
                            logger.info("analysis_tasks 表已存在，跳过创建")
                        else:
                            logger.error(f"创建 analysis_tasks 表时出错: {error_msg}")
                            raise
                else:
                    logger.error("无法获取数据库连接，无法创建表")
            
            # 检查并更新表结构（如果表已存在但缺少新字段）
            try:
                conn = DatabaseConnection.get_connection()
                if conn:
                    with conn.cursor() as cursor:
                        # 检查现有列
                        cursor.execute("SHOW COLUMNS FROM analysis_tasks")
                        existing_columns = [row[0] for row in cursor.fetchall()]
                        
                        # 需要添加的字段列表
                        columns_to_add = []
                        
                        if 'analysis_type' not in existing_columns:
                            columns_to_add.append("""
                                ALTER TABLE `analysis_tasks` 
                                ADD COLUMN `analysis_type` VARCHAR(20) DEFAULT 'by_count' 
                                COMMENT '分析类型（by_count=按数量, by_symbols=按股票）' 
                                AFTER `username`
                            """)
                        
                        if 'symbols' not in existing_columns:
                            columns_to_add.append("""
                                ALTER TABLE `analysis_tasks` 
                                ADD COLUMN `symbols` TEXT DEFAULT NULL 
                                COMMENT '股票代码列表（JSON格式，仅在按股票模式时使用）' 
                                AFTER `sort_type`
                            """)
                        
                        # 执行添加字段的SQL
                        for alter_sql in columns_to_add:
                            try:
                                cursor.execute(alter_sql)
                                conn.commit()
                                logger.info(f"成功添加字段到 analysis_tasks 表")
                            except Exception as alter_error:
                                error_msg = str(alter_error)
                                # 如果字段已存在，忽略错误
                                if 'Duplicate column' in error_msg or 'already exists' in error_msg.lower():
                                    logger.debug(f"字段可能已存在，跳过: {error_msg}")
                                else:
                                    logger.warning(f"添加字段时出错（可能已存在）: {error_msg}")
            except Exception as alter_error:
                logger.warning(f"检查或更新 analysis_tasks 表结构时出错: {str(alter_error)}")
                # 继续执行，不影响主流程
        except Exception as e:
            logger.error(f"检查或创建 analysis_tasks 表失败: {str(e)}")
            # 继续执行，让后续查询暴露具体错误
        
        # 获取查询参数
        limit = request.args.get('limit', 50, type=int)
        offset = request.args.get('offset', 0, type=int)
        
        # 查询任务历史（按开始时间倒序）
        sql = """
            SELECT 
                task_id, user_id, username, analysis_type, limit_count, sort_type, symbols, status,
                total_stocks, success_count, fail_count, progress,
                start_time, end_time, duration_seconds, error_message,
                created_at, updated_at
            FROM analysis_tasks
            ORDER BY start_time DESC, created_at DESC
            LIMIT %s OFFSET %s
        """
        tasks = DatabaseConnection.execute_query(sql, (limit, offset))
        
        # 确保返回的数据格式正确
        if tasks:
            logger.debug(f"查询到 {len(tasks)} 条任务历史记录")
            logger.debug(f"第一条记录示例: task_id={tasks[0].get('task_id')}, status={tasks[0].get('status')}, success={tasks[0].get('success_count')}, fail={tasks[0].get('fail_count')}")
        
        # 查询总数
        count_sql = "SELECT COUNT(*) as total FROM analysis_tasks"
        total_result = DatabaseConnection.execute_query(count_sql)
        # 处理 COUNT(*) 返回的结果
        total = 0
        if total_result and len(total_result) > 0:
            result_dict = total_result[0]
            # 尝试多种可能的键名
            if 'total' in result_dict:
                total = int(result_dict['total'])
            elif 'COUNT(*)' in result_dict:
                total = int(result_dict['COUNT(*)'])
            elif len(result_dict) > 0:
                # 取第一个值
                first_value = list(result_dict.values())[0]
                total = int(first_value) if first_value is not None else 0
        
        logger.info(f"【API】获取任务历史成功: 总数={total}, 返回={len(tasks)}条")
        if tasks and len(tasks) > 0:
            logger.info(f"【API】第一条任务: task_id={tasks[0].get('task_id')}, status={tasks[0].get('status')}, success={tasks[0].get('success_count')}, fail={tasks[0].get('fail_count')}")
        
        return jsonify({
            'success': True,
            'data': tasks,
            'total': total,
            'limit': limit,
            'offset': offset
        })
    except Exception as e:
        logger.error(f"获取任务历史失败: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({'success': False, 'message': str(e), 'data': [], 'total': 0})


@socketio.on('connect')
def handle_connect():
    """WebSocket连接"""
    emit('connected', {'message': '连接成功'})


def run_stock_analysis_task(task_id: str, limit: int = None, sort_type: str = 'turnover', symbols: List[str] = None):
    """在后台运行股票分析任务
    
    Args:
        task_id: 任务ID
        limit: 分析数量限制，None表示分析全部（仅在按数量模式时使用）
        sort_type: 排序方式，'turnover'表示按交易量排序，'random'表示随机排序（仅在按数量模式时使用）
        symbols: 股票代码列表（仅在按股票模式时使用）
    """
    try:
        # 记录任务启动信息
        if symbols is not None:
            logger.info("=" * 80)
            logger.info(f"【任务启动】任务ID: {task_id}")
            logger.info(f"【任务启动】分析模式: 按股票代码")
            logger.info(f"【任务启动】股票代码: {', '.join(symbols)}")
            logger.info(f"【任务启动】股票数量: {len(symbols)}只")
            logger.info("=" * 80)
        else:
            limit_text = f"{limit}只" if limit else "全部"
            sort_text = "随机排序" if sort_type == 'random' else "按交易量排序"
            logger.info("=" * 80)
            logger.info(f"【任务启动】任务ID: {task_id}")
            logger.info(f"【任务启动】分析模式: 按数量")
            logger.info(f"【任务启动】分析数量: {limit_text}")
            logger.info(f"【任务启动】排序方式: {sort_text}")
            logger.info("=" * 80)
        
        with task_lock:
            if task_id not in running_tasks:
                logger.warning(f"任务 {task_id} 不在运行列表中，退出")
                return
            task = running_tasks[task_id]
        
        # 检查必需的模块是否已导入
        if StockDataSource is None:
            error_msg = "StockDataSource 模块未导入，无法执行分析任务"
            logger.error(f"【错误】{error_msg}")
            with task_lock:
                if task_id in running_tasks:
                    running_tasks[task_id]['status'] = 'failed'
                    running_tasks[task_id]['error'] = error_msg
            return
        
        if StockPredictor is None:
            error_msg = "StockPredictor 模块未导入，无法执行分析任务"
            logger.error(f"【错误】{error_msg}")
            with task_lock:
                if task_id in running_tasks:
                    running_tasks[task_id]['status'] = 'failed'
                    running_tasks[task_id]['error'] = error_msg
            return
        
        if PredictionVisualizer is None:
            error_msg = "PredictionVisualizer 模块未导入，无法执行分析任务"
            logger.error(f"【错误】{error_msg}")
            with task_lock:
                if task_id in running_tasks:
                    running_tasks[task_id]['status'] = 'failed'
                    running_tasks[task_id]['error'] = error_msg
            return
        
        logger.info(f"【初始化】正在初始化数据源、预测器和可视化器...")
        data_source = StockDataSource()
        predictor = StockPredictor()
        visualizer = PredictionVisualizer()
        logger.info(f"【初始化】组件初始化完成")
        
        # 获取股票列表
        if symbols is not None:
            # 按股票代码模式：直接使用提供的股票代码列表
            logger.info(f"【获取股票列表】使用指定的股票代码列表，共 {len(symbols)} 只股票")
            # 将股票代码列表转换为字典格式（包含symbol和name）
            stock_list = []
            for symbol in symbols:
                # 尝试获取股票名称
                stock_info = data_source.get_stock_info(symbol, skip_pe_pb=True)
                stock_name = stock_info.get('name') or stock_info.get('股票简称') or symbol
                stock_list.append({'symbol': symbol, 'name': stock_name})
            total_count = len(stock_list)
            logger.info(f"【获取股票列表】成功准备 {total_count} 只股票")
        else:
            # 按数量模式：从API获取股票列表
            logger.info(f"【获取股票列表】正在获取股票列表（limit={limit}, sort_type={sort_type}）...")
            sort_by_turnover = (sort_type == 'turnover')
            stock_list = data_source.get_all_stock_list(limit=limit, sort_by_turnover=sort_by_turnover, random_sort=(sort_type == 'random'))
            total_count = len(stock_list) if stock_list else 0
            logger.info(f"【获取股票列表】成功获取 {total_count} 只股票")
        
        if total_count == 0:
            logger.error(f"【错误】未获取到任何股票，任务终止")
            with task_lock:
                if task_id in running_tasks:
                    running_tasks[task_id]['status'] = 'failed'
                    running_tasks[task_id]['error'] = '未获取到任何股票'
            return
        
        with task_lock:
            task['total'] = total_count
        
        socketio.emit('task_progress', {
            'task_id': task_id,
            'total': total_count,
            'progress': 0
        }, namespace='/')
        
        success_count = 0
        fail_count = 0
        completed_count = 0
        success_count_lock = threading.Lock()
        fail_count_lock = threading.Lock()
        completed_count_lock = threading.Lock()
        
        # 获取并行配置
        enable_parallel = BATCH_ANALYSIS_CONFIG.get('enable_parallel', True)
        max_workers = BATCH_ANALYSIS_CONFIG.get('max_workers', 3)
        
        logger.info(f"【开始分析】准备分析 {total_count} 只股票")
        
        def analyze_single_stock_thread(stock_info, index):
            """分析单只股票的线程函数（只保存到数据库，不生成文件）"""
            nonlocal success_count, fail_count, completed_count
            
            # 检查停止标志
            with task_lock:
                if task_stop_flags.get(task_id, False):
                    return False
            
            symbol = str(stock_info.get('symbol', '')).strip()
            stock_name = stock_info.get('name', '未知')
            if not symbol:
                return False
            
            # 每个线程创建独立的实例，避免资源竞争
            thread_predictor = StockPredictor()
            thread_visualizer = PredictionVisualizer()
            
            try:
                logger.info("-" * 80)
                logger.info(f"【分析进度】[{index}/{total_count}] 开始分析: {symbol} ({stock_name})")
                
                # 再次检查停止标志
                with task_lock:
                    if task_stop_flags.get(task_id, False):
                        return False
                
                # 执行预测（指标分析已在predict内部并行执行）
                logger.info(f"【预测分析】正在执行预测分析: {symbol}")
                result = thread_predictor.predict(symbol)
                
                # 如果result中没有name，从stock_info中获取并添加到result
                if 'name' not in result or not result.get('name') or result.get('name') == '未知':
                    result['name'] = stock_name
                
                if result.get('success', False):
                    prediction = result.get('prediction', '未知')
                    confidence = result.get('confidence', 0)
                    up_prob = result.get('up_probability', 0)
                    down_prob = result.get('down_probability', 0)
                    final_score = result.get('final_score', 0)
                    
                    logger.info(f"【预测结果】{symbol} 预测完成: {prediction} | 置信度: {confidence:.2%} | 上涨概率: {up_prob:.2%} | 下跌概率: {down_prob:.2%} | 综合得分: {final_score:.4f}")
                    
                    # 只保存到数据库，不生成PNG/HTML/CSV文件
                    try:
                        # 明确设置预测类型为 'after_close'（设置页面的预测）
                        result['prediction_type'] = 'after_close'
                        logger.info(f"【保存记录】正在保存预测记录到数据库: {symbol}")
                        thread_visualizer.save_stock_record(symbol, result, None, None, None)
                        logger.info(f"【保存记录】预测记录保存成功: {symbol}")
                        
                        # 更新成功计数
                        with success_count_lock:
                            success_count += 1
                        success = True
                    except Exception as e:
                        logger.error(f"【错误】保存预测记录失败 {symbol}: {str(e)}")
                        logger.error(traceback.format_exc())
                        with fail_count_lock:
                            fail_count += 1
                        success = False
                else:
                    error_msg = result.get('message', '未知错误')
                    logger.warning(f"【预测失败】股票 {symbol} 预测失败: {error_msg}")
                    with fail_count_lock:
                        fail_count += 1
                    success = False
                
                # 更新进度
                with completed_count_lock:
                    completed_count += 1
                    current_progress = completed_count
                
                # 更新任务状态（线程安全）
                with progress_lock:
                    with task_lock:
                        if task_id in running_tasks:
                            running_tasks[task_id]['progress'] = current_progress
                            running_tasks[task_id]['success_count'] = success_count
                            running_tasks[task_id]['fail_count'] = fail_count
                            # 更新当前股票
                            running_tasks[task_id]['current_stock'] = symbol
                
                # 发送进度更新
                socketio.emit('task_progress', {
                    'task_id': task_id,
                    'total': total_count,
                    'progress': current_progress,
                    'current_stock': symbol,
                    'success_count': success_count,
                    'fail_count': fail_count
                }, namespace='/')
                
                progress_pct = (current_progress / total_count * 100) if total_count > 0 else 0
                logger.info(f"【分析完成】{symbol} 分析完成 (进度: {current_progress}/{total_count} ({progress_pct:.1f}%), 成功: {success_count}, 失败: {fail_count})")
                
                return success
                
            except Exception as e:
                logger.error(f"【错误】分析股票 {symbol} 时发生异常: {str(e)}")
                logger.error(traceback.format_exc())
                with fail_count_lock:
                    fail_count += 1
                with completed_count_lock:
                    completed_count += 1
                return False
        
        # 根据配置选择多线程或单线程模式
        progress_lock = threading.Lock()
        
        if enable_parallel and max_workers > 1:
            # 多线程并行分析模式
            logger.info(f"【分析模式】使用多线程并行分析（并发数: {max_workers}）")
            
            # 使用线程池并行执行
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                # 提交所有任务
                future_to_stock = {
                    executor.submit(analyze_single_stock_thread, stock_info, idx + 1): (stock_info, idx + 1)
                    for idx, stock_info in enumerate(stock_list)
                }
                
                # 等待所有任务完成（同时检查停止标志）
                for future in as_completed(future_to_stock):
                    # 检查停止标志
                    with task_lock:
                        if task_stop_flags.get(task_id, False):
                            logger.info(f"【任务停止】任务 {task_id} 收到停止信号，取消剩余任务")
                            # 取消未完成的任务
                            for f in future_to_stock:
                                if not f.done():
                                    f.cancel()
                            task['status'] = 'cancelled'
                            break
                    
                    try:
                        future.result()
                    except Exception as e:
                        stock_info, index = future_to_stock[future]
                        symbol = str(stock_info.get('symbol', '')).strip()
                        logger.error(f"【执行异常】股票 {symbol} (索引 {index}) 执行异常: {str(e)}")
        else:
            # 单线程顺序分析模式（移除文件生成）
            logger.info(f"【分析模式】使用单线程顺序分析")
            
            for idx, stock_info in enumerate(stock_list):
                # 检查停止标志
                with task_lock:
                    if task_stop_flags.get(task_id, False):
                        logger.info(f"【任务停止】任务 {task_id} 收到停止信号，停止分析")
                        task['status'] = 'cancelled'
                        break
                
                symbol = str(stock_info.get('symbol', '')).strip()
                stock_name = stock_info.get('name', '未知')
                if not symbol:
                    continue
                
                current_num = idx + 1
                progress_pct = (current_num / total_count * 100) if total_count > 0 else 0
                
                logger.info("-" * 80)
                logger.info(f"【分析进度】[{current_num}/{total_count}] ({progress_pct:.1f}%) 开始分析: {symbol} ({stock_name})")
                
                try:
                    # 再次检查停止标志
                    with task_lock:
                        if task_stop_flags.get(task_id, False):
                            logger.info(f"【任务停止】任务 {task_id} 收到停止信号，停止当前股票分析")
                            task['status'] = 'cancelled'
                            break
                        task['progress'] = current_num
                        task['current_stock'] = symbol
                    
                    socketio.emit('task_progress', {
                        'task_id': task_id,
                        'total': total_count,
                        'progress': current_num,
                        'current_stock': symbol,
                        'success_count': success_count,
                        'fail_count': fail_count
                    }, namespace='/')
                    
                    # 执行预测（指标分析已在predict内部并行执行）
                    logger.info(f"【预测分析】正在执行预测分析: {symbol}")
                    result = predictor.predict(symbol)
                    
                    # 如果result中没有name，从stock_info中获取并添加到result
                    if 'name' not in result or not result.get('name') or result.get('name') == '未知':
                        result['name'] = stock_name
                    
                    if result.get('success', False):
                        prediction = result.get('prediction', '未知')
                        confidence = result.get('confidence', 0)
                        up_prob = result.get('up_probability', 0)
                        down_prob = result.get('down_probability', 0)
                        final_score = result.get('final_score', 0)
                        
                        logger.info(f"【预测结果】{symbol} 预测完成: {prediction} | 置信度: {confidence:.2%} | 上涨概率: {up_prob:.2%} | 下跌概率: {down_prob:.2%} | 综合得分: {final_score:.4f}")
                        
                        # 只保存到数据库，不生成PNG/HTML/CSV文件
                        try:
                            # 明确设置预测类型为 'after_close'（设置页面的预测）
                            result['prediction_type'] = 'after_close'
                            logger.info(f"【保存记录】正在保存预测记录到数据库: {symbol}")
                            visualizer.save_stock_record(symbol, result, None, None, None)
                            logger.info(f"【保存记录】预测记录保存成功: {symbol}")
                            
                            success_count += 1
                            logger.info(f"【分析完成】{symbol} 分析成功完成 (成功: {success_count}, 失败: {fail_count})")
                        except Exception as e:
                            logger.error(f"【错误】保存预测记录失败 {symbol}: {str(e)}")
                            logger.error(traceback.format_exc())
                            fail_count += 1
                    else:
                        error_msg = result.get('message', '未知错误')
                        logger.warning(f"【预测失败】股票 {symbol} 预测失败: {error_msg}")
                        fail_count += 1
                    
                    with task_lock:
                        task['success_count'] = success_count
                        task['fail_count'] = fail_count
                    
                except Exception as e:
                    logger.error(f"【错误】分析股票 {symbol} 时发生异常: {str(e)}")
                    logger.error(traceback.format_exc())
                    fail_count += 1
                    with task_lock:
                        task['fail_count'] = fail_count
        
        # 检查是否为停止状态
        was_cancelled = False
        with task_lock:
            if task_stop_flags.get(task_id, False) or task.get('status') == 'cancelled':
                was_cancelled = True
                task['status'] = 'cancelled'
        
        # 不再生成HTML页面，所有数据都从数据库读取（页面由前端通过API动态获取）
        # 移除HTML页面生成逻辑
        
        # 任务完成或取消
        end_time = datetime.now()
        final_status = 'cancelled' if was_cancelled else 'completed'
        
        with task_lock:
            if task_id in running_tasks:
                task['status'] = final_status
                task['progress'] = success_count + fail_count  # 实际完成的股票数
                task['current_stock'] = None
                task['end_time'] = end_time.isoformat()
        
        # 计算任务耗时
        start_time_str = task.get('start_time', '')
        duration_seconds = None
        duration_str = "未知"
        if start_time_str:
            try:
                start_time = datetime.fromisoformat(start_time_str)
                duration = (end_time - start_time).total_seconds()
                duration_seconds = int(duration)
                hours = int(duration // 3600)
                minutes = int((duration % 3600) // 60)
                seconds = int(duration % 60)
                duration_str = f"{hours}小时{minutes}分钟{seconds}秒" if hours > 0 else f"{minutes}分钟{seconds}秒"
            except:
                pass
        
        # 计算成功率
        success_rate = (success_count / total_count * 100) if total_count > 0 else 0
        
        logger.info("=" * 80)
        logger.info(f"【任务完成】任务ID: {task_id}")
        logger.info(f"【任务完成】任务状态: {final_status}")
        logger.info(f"【任务完成】总股票数: {total_count}")
        logger.info(f"【任务完成】成功: {success_count} ({success_rate:.1f}%)")
        logger.info(f"【任务完成】失败: {fail_count} ({(100-success_rate):.1f}%)")
        logger.info(f"【任务完成】耗时: {duration_str}")
        logger.info("=" * 80)
        
        # 保存任务历史到数据库
        try:
            from utils.task_history_db import save_task_history
            logger.info(f"【任务历史】准备保存任务历史: {task_id}")
            logger.info(f"  - 用户ID: {task.get('user_id')}")
            logger.info(f"  - 用户名: {task.get('username')}")
            logger.info(f"  - 状态: {final_status}")
            logger.info(f"  - 成功: {success_count}, 失败: {fail_count}")
            logger.info(f"  - 开始时间: {start_time_str}")
            logger.info(f"  - 结束时间: {end_time.isoformat()}")
            
            # 获取任务类型和股票代码列表
            analysis_type = task.get('analysis_type', 'by_count')
            symbols = task.get('symbols')
            symbols_json = json.dumps(symbols, ensure_ascii=False) if symbols else None
            
            result = save_task_history(
                task_id=task_id,
                user_id=task.get('user_id'),
                username=task.get('username'),
                analysis_type=analysis_type,
                limit_count=limit,
                sort_type=sort_type,
                symbols=symbols_json,
                status=final_status,
                total_stocks=total_count,
                success_count=success_count,
                fail_count=fail_count,
                progress=success_count + fail_count,
                start_time=start_time_str,
                end_time=end_time.isoformat(),
                duration_seconds=duration_seconds,
                error_message=task.get('error')
            )
            if result:
                logger.info(f"【任务历史】任务历史已成功保存到数据库: {task_id}")
            else:
                logger.warning(f"【任务历史】任务历史保存失败: {task_id} (可能数据库未启用或保存失败)")
        except Exception as e:
            logger.error(f"【错误】保存任务历史失败: {str(e)}")
            logger.error(traceback.format_exc())
        
        # 发送完成事件
        if was_cancelled:
            socketio.emit('task_cancelled', {
                'task_id': task_id,
                'success_count': success_count,
                'fail_count': fail_count
            }, namespace='/')
        else:
            socketio.emit('task_completed', {
                'task_id': task_id,
                'success_count': success_count,
                'fail_count': fail_count
            }, namespace='/')
        
    except Exception as e:
        logger.error("=" * 80)
        logger.error(f"【任务失败】任务ID: {task_id}")
        logger.error(f"【任务失败】错误信息: {str(e)}")
        logger.error(f"【任务失败】错误详情:")
        logger.error(traceback.format_exc())
        logger.error("=" * 80)
        with task_lock:
            if task_id in running_tasks:
                running_tasks[task_id]['status'] = 'failed'
                running_tasks[task_id]['error'] = str(e)


@app.route('/reports/<path:filename>')
def reports(filename):
    """提供reports目录下的文件访问"""
    reports_dir = os.path.join(project_root, 'reports')
    return send_from_directory(reports_dir, filename)


@app.route('/static/<path:filename>')
def static_files(filename):
    """提供static目录下的文件访问"""
    static_dir = os.path.join(project_root, 'static')
    return send_from_directory(static_dir, filename)


@app.route('/graph_report')
def graph_report():
    """图形报告页面"""
    symbol = request.args.get('symbol', '')
    name = request.args.get('name', '')
    return render_template('graph_report.html', symbol=symbol, name=name)

@app.route('/text_detail')
def text_detail():
    """文字详情页面"""
    symbol = request.args.get('symbol', '')
    name = request.args.get('name', '')
    return render_template('text_detail.html', symbol=symbol, name=name)

@app.route('/history')
def history():
    """历史预测页面"""
    symbol = request.args.get('symbol', '')
    name = request.args.get('name', '')
    return render_template('history.html', symbol=symbol, name=name)

@app.route('/realtime_strategy')
def realtime_strategy():
    """实时策略页面"""
    symbol = request.args.get('symbol', '')
    name = request.args.get('name', '')
    return render_template('realtime_strategy.html', symbol=symbol, name=name)


@app.route('/api/graph_report', methods=['GET'])
def api_get_graph_report():
    """获取图形报告数据"""
    try:
        symbol = request.args.get('symbol', '').strip()
        if not symbol:
            return jsonify({'success': False, 'message': '股票代码不能为空'})
        
        symbol = str(symbol).zfill(6)
        
        # 从数据库获取预测数据
        if StockPredictionDB is None:
            return jsonify({'success': False, 'message': '数据库模块未加载'})
        
        db = StockPredictionDB()
        
        # 获取最新的预测记录
        predictions = db.get_predictions(symbol=symbol, limit=1)
        if not predictions:
            return jsonify({'success': False, 'message': '未找到该股票的预测数据'})
        
        prediction = predictions[0]
        
        # 获取预测因子数据
        factors_data = {}
        if DatabaseConnection:
            try:
                db_conn = DatabaseConnection()
                sql = """
                    SELECT * FROM prediction_factors 
                    WHERE symbol = %s 
                    ORDER BY timestamp DESC 
                    LIMIT 1
                """
                factors_records = db_conn.execute_query(sql, (symbol,))
                if factors_records:
                    factors_record = factors_records[0]
                    factors_data = {
                        'technical': {
                            'score': float(factors_record.get('technical_score', 0) or 0),
                            'weight': float(factors_record.get('technical_weight', 0) or 0),
                            'trend': factors_record.get('technical_trend', 'neutral')
                        },
                        'news': {
                            'score': float(factors_record.get('news_score', 0) or 0),
                            'weight': float(factors_record.get('news_weight', 0) or 0),
                            'sentiment': factors_record.get('news_sentiment', 'neutral')
                        },
                        'market': {
                            'score': float(factors_record.get('market_score', 0) or 0),
                            'weight': float(factors_record.get('market_weight', 0) or 0),
                            'trend': factors_record.get('market_trend', 'neutral')
                        },
                        'history': {
                            'score': float(factors_record.get('history_score', 0) or 0),
                            'weight': float(factors_record.get('history_weight', 0) or 0),
                            'pattern': factors_record.get('history_pattern', 'unknown')
                        },
                        'us_sector': {
                            'score': float(factors_record.get('us_sector_score', 0) or 0),
                            'weight': float(factors_record.get('us_sector_weight', 0) or 0),
                            'sector': factors_record.get('us_sector', 'unknown')
                        },
                        'capital_flow': {
                            'score': float(factors_record.get('capital_flow_score', 0) or 0),
                            'weight': float(factors_record.get('capital_flow_weight', 0) or 0),
                            'trend': factors_record.get('capital_flow_trend', 'neutral')
                        },
                        'sector_rotation': {
                            'score': float(factors_record.get('sector_rotation_score', 0) or 0),
                            'weight': float(factors_record.get('sector_rotation_weight', 0) or 0),
                            'trend': factors_record.get('sector_rotation_trend', 'neutral')
                        },
                        'valuation': {
                            'score': float(factors_record.get('valuation_score', 0) or 0),
                            'weight': float(factors_record.get('valuation_weight', 0) or 0),
                            'pe_ratio': float(factors_record.get('pe_ratio', 0) or 0) if factors_record.get('pe_ratio') else None,
                            'pb_ratio': float(factors_record.get('pb_ratio', 0) or 0) if factors_record.get('pb_ratio') else None
                        }
                    }
            except Exception as e:
                logger.warning(f"获取预测因子数据失败: {str(e)}")
                # 如果获取失败，使用默认值
                factors_data = {}
        
        # 获取趋势数据（30天）
        trend_data = []
        if StockDataSource:
            try:
                data_source = StockDataSource()
                stock_data = data_source.get_daily_data(symbol, days=30)
                if not stock_data.empty:
                    for _, row in stock_data.iterrows():
                        trend_data.append({
                            'date': row['date'].strftime('%Y-%m-%d') if hasattr(row['date'], 'strftime') else str(row['date']),
                            'close': float(row.get('close', 0)),
                            'volume': float(row.get('volume', 0))
                        })
            except Exception as e:
                logger.warning(f"获取趋势数据失败: {str(e)}")
        
        # 构建返回数据
        result_data = {
            'symbol': prediction.get('symbol', symbol),
            'name': prediction.get('name', ''),
            'prediction_date': str(prediction.get('prediction_date', '')) if prediction.get('prediction_date') else '',
            'target_date': str(prediction.get('target_date', '')) if prediction.get('target_date') else '',
            'current_price': float(prediction.get('current_price', 0) or 0),
            'prediction': prediction.get('prediction', '震荡'),
            'up_probability': float(prediction.get('up_probability', 0) or 0),
            'down_probability': float(prediction.get('down_probability', 0) or 0),
            'confidence': float(prediction.get('confidence', 0) or 0),
            'final_score': float(prediction.get('final_score', 0) or 0),
            'factors': factors_data,
            'trend_data': trend_data
        }
        
        return jsonify({'success': True, 'data': result_data})
        
    except Exception as e:
        logger.error(f"获取图形报告数据失败: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({'success': False, 'message': str(e)})


@app.route('/api/text_detail', methods=['GET'])
def api_get_text_detail():
    """获取文字详情数据"""
    try:
        symbol = request.args.get('symbol', '').strip()
        if not symbol:
            return jsonify({'success': False, 'message': '股票代码不能为空'})
        
        symbol = str(symbol).zfill(6)
        
        # 从数据库获取预测数据
        if StockPredictionDB is None:
            return jsonify({'success': False, 'message': '数据库模块未加载'})
        
        db = StockPredictionDB()
        
        # 获取最新的预测记录
        predictions = db.get_predictions(symbol=symbol, limit=1)
        if not predictions:
            return jsonify({'success': False, 'message': '未找到该股票的预测数据'})
        
        prediction = predictions[0]
        
        # 获取预测因子数据
        factors_data = {}
        market_overall = {}
        trading_suggestions = {}
        cost_distribution = {}
        realtime_data = {}
        
        if DatabaseConnection:
            try:
                db_conn = DatabaseConnection()
                
                # 获取预测因子数据
                sql = """
                    SELECT * FROM prediction_factors 
                    WHERE symbol = %s 
                    ORDER BY timestamp DESC 
                    LIMIT 1
                """
                factors_records = db_conn.execute_query(sql, (symbol,))
                if factors_records:
                    factors_record = factors_records[0]
                    factors_data = {
                        'technical': {
                            'score': float(factors_record.get('technical_score', 0) or 0),
                            'weight': float(factors_record.get('technical_weight', 0) or 0),
                            'trend': factors_record.get('technical_trend', 'neutral'),
                            'signals': {}  # 信号数据需要从其他地方获取或计算
                        },
                        'news': {
                            'score': float(factors_record.get('news_score', 0) or 0),
                            'weight': float(factors_record.get('news_weight', 0) or 0),
                            'sentiment': factors_record.get('news_sentiment', 'neutral'),
                            'news_count': 0,  # 需要从news_sentiment表获取
                            'direct_news_count': 0,
                            'industry_news_count': 0,
                            'positive_count': 0,
                            'negative_count': 0,
                            'weight_multiplier': 1.0
                        },
                        'market': {
                            'score': float(factors_record.get('market_score', 0) or 0),
                            'weight': float(factors_record.get('market_weight', 0) or 0),
                            'trend': factors_record.get('market_trend', 'neutral')
                        },
                        'history': {
                            'score': float(factors_record.get('history_score', 0) or 0),
                            'weight': float(factors_record.get('history_weight', 0) or 0),
                            'pattern': factors_record.get('history_pattern', 'unknown')
                        },
                        'us_sector': {
                            'score': float(factors_record.get('us_sector_score', 0) or 0),
                            'weight': float(factors_record.get('us_sector_weight', 0) or 0),
                            'sector': factors_record.get('us_sector_name', 'unknown'),
                            'change_pct': float(factors_record.get('us_sector_change_pct', 0) or 0),
                            'trend': 'neutral'
                        },
                        'capital_flow': {
                            'score': float(factors_record.get('capital_flow_score', 0) or 0),
                            'weight': float(factors_record.get('capital_flow_weight', 0) or 0),
                            'trend': factors_record.get('capital_flow_trend', 'neutral')
                        },
                        'sector_rotation': {
                            'score': float(factors_record.get('sector_rotation_score', 0) or 0),
                            'weight': float(factors_record.get('sector_rotation_weight', 0) or 0),
                            'trend': factors_record.get('sector_rotation_trend', 'neutral')
                        },
                        'valuation': {
                            'score': float(factors_record.get('valuation_score', 0) or 0),
                            'weight': float(factors_record.get('valuation_weight', 0) or 0),
                            'pe_ratio': float(factors_record.get('pe_ratio', 0) or 0) if factors_record.get('pe_ratio') else None,
                            'pb_ratio': float(factors_record.get('pb_ratio', 0) or 0) if factors_record.get('pb_ratio') else None,
                            'valuation': '未知'
                        }
                    }
                
                # 尝试获取新闻情感详细数据
                try:
                    news_sql = """
                        SELECT * FROM news_sentiment 
                        WHERE symbol = %s 
                        ORDER BY timestamp DESC 
                        LIMIT 1
                    """
                    news_records = db_conn.execute_query(news_sql, (symbol,))
                    if news_records and factors_data.get('news'):
                        news_record = news_records[0]
                        factors_data['news']['news_count'] = int(news_record.get('news_count', 0) or 0)
                        factors_data['news']['direct_news_count'] = int(news_record.get('direct_news_count', 0) or 0)
                        factors_data['news']['industry_news_count'] = int(news_record.get('industry_news_count', 0) or 0)
                        factors_data['news']['positive_count'] = int(news_record.get('positive_count', 0) or 0)
                        factors_data['news']['negative_count'] = int(news_record.get('negative_count', 0) or 0)
                        factors_data['news']['weight_multiplier'] = float(news_record.get('weight_multiplier', 1.0) or 1.0)
                except Exception as e:
                    logger.debug(f"获取新闻情感详细数据失败: {str(e)}")
                
            except Exception as e:
                logger.warning(f"获取预测因子数据失败: {str(e)}")
        
        # 尝试从数据库获取成本分布数据（优先使用数据库）
        try:
            from utils.stock_history_storage import StockHistoryStorage
            history_storage = StockHistoryStorage()
            today = datetime.now().strftime('%Y-%m-%d')
            
            # 获取当天的历史数据
            today_data = history_storage.get_stock_history_data(
                symbol=symbol,
                start_date=today,
                end_date=today,
                limit=1
            )
            
            if today_data:
                record = today_data[0]
                # 从数据库获取成本分布数据
                if record.get('cost_distribution_history'):
                    try:
                        history_cost = record['cost_distribution_history']
                        if isinstance(history_cost, str):
                            import json
                            history_cost = json.loads(history_cost)
                    except:
                        history_cost = None
                else:
                    history_cost = None
                
                if record.get('cost_distribution_intraday'):
                    try:
                        intraday_cost = record['cost_distribution_intraday']
                        if isinstance(intraday_cost, str):
                            import json
                            intraday_cost = json.loads(intraday_cost)
                    except:
                        intraday_cost = None
                else:
                    intraday_cost = None
                
                if history_cost or intraday_cost:
                    cost_distribution = {
                        'history': history_cost,
                        'intraday': intraday_cost
                    }
                
                # 从数据库获取实时行情数据（如果当天已收盘）
                if record.get('close_price'):
                    # 构建实时行情数据
                    realtime_quote = {
                        'current_price': float(record.get('close_price', 0) or 0),
                        'open_price': float(record.get('open_price', 0) or 0) if record.get('open_price') else None,
                        'high_price': float(record.get('high_price', 0) or 0) if record.get('high_price') else None,
                        'low_price': float(record.get('low_price', 0) or 0) if record.get('low_price') else None,
                        'pre_close': float(record.get('pre_close', 0) or 0) if record.get('pre_close') else None,
                        'volume': float(record.get('volume', 0) or 0) if record.get('volume') else None,
                        'amount': float(record.get('amount', 0) or 0) if record.get('amount') else None,
                        'change_pct': float(record.get('change_pct', 0) or 0) if record.get('change_pct') else None,
                        'change_amount': float(record.get('change_amount', 0) or 0) if record.get('change_amount') else None,
                        'turnover_rate': float(record.get('turnover_rate', 0) or 0) if record.get('turnover_rate') else None,
                        'amplitude': float(record.get('amplitude', 0) or 0) if record.get('amplitude') else None,
                        'timestamp': str(record.get('trade_date', today))
                    }
                    
                    # 从数据库获取资金流向数据
                    capital_flow = {}
                    if record.get('main_net_inflow') is not None:
                        capital_flow['main_net_inflow'] = float(record.get('main_net_inflow', 0) or 0)
                    if record.get('super_large_inflow') is not None:
                        capital_flow['super_large_inflow'] = float(record.get('super_large_inflow', 0) or 0)
                    if record.get('large_inflow') is not None:
                        capital_flow['large_inflow'] = float(record.get('large_inflow', 0) or 0)
                    if record.get('medium_inflow') is not None:
                        capital_flow['medium_inflow'] = float(record.get('medium_inflow', 0) or 0)
                    if record.get('small_inflow') is not None:
                        capital_flow['small_inflow'] = float(record.get('small_inflow', 0) or 0)
                    
                    # 计算总净流入
                    if capital_flow:
                        total_net = sum([
                            capital_flow.get('main_net_inflow', 0),
                            capital_flow.get('super_large_inflow', 0),
                            capital_flow.get('large_inflow', 0),
                            capital_flow.get('medium_inflow', 0),
                            capital_flow.get('small_inflow', 0)
                        ])
                        capital_flow['total_net_inflow'] = total_net
                        
                        # 判断资金流向趋势
                        if total_net > 0:
                            capital_flow['flow_trend'] = '资金流入'
                        elif total_net < 0:
                            capital_flow['flow_trend'] = '资金流出'
                        else:
                            capital_flow['flow_trend'] = '资金平衡'
                        
                        capital_flow['symbol'] = symbol
                        capital_flow['timestamp'] = str(record.get('trade_date', today))
                    
                    if realtime_quote or capital_flow:
                        # 判断是否在交易时间
                        trading_time = {}
                        if StockDataSource:
                            try:
                                data_source = StockDataSource()
                                trading_time = data_source.is_trading_time()
                            except:
                                trading_time = {'is_trading': False, 'message': '无法判断交易时间'}
                        
                        # 如果市场开盘，获取实时交易决策（包含涨跌停板策略和T+1优化）
                        decision_data = None
                        limit_up_strategy = None
                        limit_down_strategy = None
                        holding_period_optimization = None
                        if trading_time.get('is_trading', False):
                            try:
                                from predictor.realtime_trading_advisor import RealtimeTradingAdvisor
                                advisor = RealtimeTradingAdvisor()
                                decision_result = advisor.get_realtime_decision(symbol=symbol)
                                if decision_result and decision_result.get('success'):
                                    decision_data = decision_result.get('decision', {})
                                    limit_up_strategy = decision_result.get('limit_up_strategy')
                                    limit_down_strategy = decision_result.get('limit_down_strategy')
                                    holding_period_optimization = decision_result.get('holding_period_optimization')
                                    auction_strategy = decision_result.get('auction_strategy')
                                    suspension_info = decision_result.get('suspension_info')
                                    st_info = decision_result.get('st_info')
                                    dragon_tiger_analysis = decision_result.get('dragon_tiger_analysis')
                                    restricted_shares_info = decision_result.get('restricted_shares_info')
                            except Exception as e:
                                logger.debug(f"获取实时交易决策失败: {str(e)}")
                        
                        realtime_data = {
                            'quote': realtime_quote if realtime_quote.get('current_price') else None,
                            'capital_flow': capital_flow if capital_flow else None,
                            'trading_time': trading_time,
                            'decision': decision_data,
                            'limit_up_strategy': limit_up_strategy,
                            'limit_down_strategy': limit_down_strategy,
                            'holding_period_optimization': holding_period_optimization,
                            'auction_strategy': auction_strategy,
                            'suspension_info': suspension_info if 'suspension_info' in locals() else None,
                            'st_info': st_info if 'st_info' in locals() else None,
                            'dragon_tiger_analysis': dragon_tiger_analysis if 'dragon_tiger_analysis' in locals() else None,
                            'restricted_shares_info': restricted_shares_info if 'restricted_shares_info' in locals() else None
                        }
        except Exception as e:
            logger.debug(f"从数据库获取成本分布和实时数据失败: {str(e)}")
        
        # 如果数据库没有成本分布数据，尝试从API获取（降级方案）
        if not cost_distribution and StockDataSource:
            try:
                data_source = StockDataSource()
                history_cost = data_source.get_cost_distribution(symbol)
                intraday_cost = data_source.get_intraday_cost_distribution(symbol)
                if history_cost or intraday_cost:
                    cost_distribution = {
                        'history': history_cost,
                        'intraday': intraday_cost
                    }
            except Exception as e:
                logger.debug(f"从API获取成本分布数据失败: {str(e)}")
        
        # 如果数据库没有实时数据，且市场开盘，尝试从API获取（降级方案）
        if not realtime_data and StockDataSource:
            try:
                data_source = StockDataSource()
                trading_time = data_source.is_trading_time()
                # 只有在交易时间才获取实时数据
                if trading_time.get('is_trading', False):
                    realtime_quote = data_source.get_realtime_quote(symbol)
                    capital_flow = data_source.get_realtime_capital_flow(symbol)
                    
                    if realtime_quote or capital_flow:
                        realtime_data = {
                            'quote': realtime_quote,
                            'capital_flow': capital_flow,
                            'trading_time': trading_time
                        }
            except Exception as e:
                logger.debug(f"从API获取实时数据失败: {str(e)}")
        
        # 构建返回数据
        result_data = {
            'symbol': prediction.get('symbol', symbol),
            'name': prediction.get('name', ''),
            'prediction_date': str(prediction.get('prediction_date', '')) if prediction.get('prediction_date') else '',
            'target_date': str(prediction.get('target_date', '')) if prediction.get('target_date') else '',
            'prediction_time': str(prediction.get('prediction_time', '')) if prediction.get('prediction_time') else '',
            'current_price': float(prediction.get('current_price', 0) or 0),
            'predicted_close_price': float(prediction.get('predicted_close_price', 0)) if prediction.get('predicted_close_price') else None,
            'predicted_change_pct': float(prediction.get('predicted_change_pct', 0)) if prediction.get('predicted_change_pct') is not None else None,
            'prediction': prediction.get('prediction', '震荡'),
            'up_probability': float(prediction.get('up_probability', 0) or 0),
            'down_probability': float(prediction.get('down_probability', 0) or 0),
            'confidence': float(prediction.get('confidence', 0) or 0),
            'final_score': float(prediction.get('final_score', 0) or 0),
            'summary': prediction.get('summary', ''),
            'factors': factors_data,
            'market_overall': market_overall,
            'trading_suggestions': trading_suggestions,
            'cost_distribution': cost_distribution,
            'realtime_data': realtime_data
        }
        
        return jsonify({'success': True, 'data': result_data})
        
    except Exception as e:
        logger.error(f"获取文字详情数据失败: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({'success': False, 'message': str(e)})


@app.route('/api/history', methods=['GET'])
def api_get_history():
    """获取历史预测数据"""
    try:
        symbol = request.args.get('symbol', '').strip()
        if not symbol:
            return jsonify({'success': False, 'message': '股票代码不能为空'})
        
        symbol = str(symbol).zfill(6)
        
        # 从数据库获取历史预测记录
        if StockPredictionDB is None:
            return jsonify({'success': False, 'message': '数据库模块未加载'})
        
        db = StockPredictionDB()
        
        # 在获取数据前，先更新历史预测的实际数据（确保数据是最新的）
        try:
            from visualizer.prediction_visualizer import PredictionVisualizer
            visualizer = PredictionVisualizer()
            visualizer._update_historical_actual_data()
        except Exception as e:
            logger.warning(f"更新历史实际数据失败: {str(e)}")
            # 不影响数据获取，继续执行
        
        # 获取该股票的所有预测记录（按预测时间倒序）
        predictions = db.get_predictions(symbol=symbol, limit=1000, order_by='prediction_time DESC')
        
        if not predictions:
            return jsonify({
                'success': True, 
                'data': {
                    'symbol': symbol,
                    'name': '',
                    'records': []
                }
            })
        
        # 获取第一条记录的股票名称
        stock_name = predictions[0].get('name', '')
        
        # 处理每条记录，获取因子数据
        records = []
        if DatabaseConnection:
            db_conn = DatabaseConnection()
            
            for pred in predictions:
                record = {
                    'id': pred.get('id'),
                    'symbol': pred.get('symbol', symbol),
                    'name': pred.get('name', stock_name),
                    'prediction_date': str(pred.get('prediction_date', '')) if pred.get('prediction_date') else '',
                    'target_date': str(pred.get('target_date', '')) if pred.get('target_date') else '',
                    'prediction_time': str(pred.get('prediction_time', '')) if pred.get('prediction_time') else '',
                    'current_price': float(pred.get('current_price', 0) or 0),
                    'predicted_close_price': float(pred.get('predicted_close_price', 0)) if pred.get('predicted_close_price') else None,
                    'predicted_change_pct': float(pred.get('predicted_change_pct', 0)) if pred.get('predicted_change_pct') is not None else None,
                    'prediction': pred.get('prediction', '震荡'),
                    'up_probability': float(pred.get('up_probability', 0) or 0),
                    'down_probability': float(pred.get('down_probability', 0) or 0),
                    'confidence': float(pred.get('confidence', 0) or 0),
                    'final_score': float(pred.get('final_score', 0) or 0),
                    'summary': pred.get('summary', ''),
                    'actual_price': float(pred.get('actual_price', 0) or 0) if pred.get('actual_price') else None,
                    'actual_change_pct': float(pred.get('actual_change_pct', 0) or 0) if pred.get('actual_change_pct') is not None else None,
                    'actual_direction': pred.get('actual_direction', ''),
                    'prediction_hit': pred.get('prediction_hit', ''),
                    'factors': {}
                }
                
                # 尝试获取该预测对应的因子数据
                try:
                    # 使用target_date和symbol查找对应的因子数据
                    target_date = pred.get('target_date')
                    if target_date:
                        factors_sql = """
                            SELECT * FROM prediction_factors 
                            WHERE symbol = %s AND date = %s 
                            ORDER BY timestamp DESC 
                            LIMIT 1
                        """
                        factors_records = db_conn.execute_query(factors_sql, (symbol, str(target_date)))
                        if factors_records:
                            factors_record = factors_records[0]
                            record['factors'] = {
                                'technical': {
                                    'score': float(factors_record.get('technical_score', 0) or 0),
                                    'weight': float(factors_record.get('technical_weight', 0) or 0),
                                    'trend': factors_record.get('technical_trend', 'neutral')
                                },
                                'news': {
                                    'score': float(factors_record.get('news_score', 0) or 0),
                                    'weight': float(factors_record.get('news_weight', 0) or 0),
                                    'sentiment': factors_record.get('news_sentiment', 'neutral'),
                                    'news_count': 0
                                },
                                'market': {
                                    'score': float(factors_record.get('market_score', 0) or 0),
                                    'weight': float(factors_record.get('market_weight', 0) or 0),
                                    'trend': factors_record.get('market_trend', 'neutral')
                                },
                                'history': {
                                    'score': float(factors_record.get('history_score', 0) or 0),
                                    'weight': float(factors_record.get('history_weight', 0) or 0),
                                    'pattern': factors_record.get('history_pattern', 'unknown')
                                }
                            }
                except Exception as e:
                    logger.debug(f"获取因子数据失败: {str(e)}")
                
                records.append(record)
        
        return jsonify({
            'success': True,
            'data': {
                'symbol': symbol,
                'name': stock_name,
                'records': records
            }
        })
        
    except Exception as e:
        logger.error(f"获取历史预测数据失败: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({'success': False, 'message': str(e)})


@app.route('/api/realtime_strategy', methods=['GET'])
def api_get_realtime_strategy():
    """获取实时策略数据"""
    try:
        symbol = request.args.get('symbol', '').strip()
        if not symbol:
            return jsonify({'success': False, 'message': '股票代码不能为空'})
        
        symbol = str(symbol).zfill(6)
        
        # 获取持仓信息
        holding = request.args.get('holding', 'false').lower() == 'true'
        cost_price = None
        try:
            cost_price_str = request.args.get('cost_price', '').strip()
            if cost_price_str:
                cost_price = float(cost_price_str)
        except (ValueError, TypeError):
            cost_price = None
        
        # 导入实时交易决策顾问
        RealtimeTradingAdvisor = None
        try:
            import importlib.util
            advisor_path = os.path.join(project_root, "predictor", "realtime_trading_advisor.py")
            if os.path.exists(advisor_path):
                advisor_spec = importlib.util.spec_from_file_location(
                    "realtime_trading_advisor",
                    advisor_path
                )
                advisor_module = importlib.util.module_from_spec(advisor_spec)
                advisor_spec.loader.exec_module(advisor_module)
                RealtimeTradingAdvisor = advisor_module.RealtimeTradingAdvisor
        except Exception as e:
            logger.warning(f"导入RealtimeTradingAdvisor失败: {str(e)}")
        
        if RealtimeTradingAdvisor is None:
            return jsonify({'success': False, 'message': '实时交易决策模块未加载'})
        
        # 获取股票名称
        stock_name = ''
        if StockDataSource:
            try:
                data_source = StockDataSource()
                stock_info = data_source.get_stock_info(symbol)
                stock_name = stock_info.get('name', '') if stock_info else ''
            except Exception as e:
                logger.debug(f"获取股票名称失败: {str(e)}")
        
        # 创建实时交易决策顾问实例
        advisor = RealtimeTradingAdvisor()
        
        # 导入风险控制器（如果可用）
        RiskController = None
        try:
            from utils.risk_controller import RiskController
        except Exception as e:
            logger.debug(f"导入RiskController失败: {str(e)}")
        
        # 获取实时交易决策
        decision_result = advisor.get_realtime_decision(
            symbol=symbol,
            holding=holding,
            cost_price=cost_price,
            mode="realtime"
        )
        
        if not decision_result.get('success', False):
            return jsonify({
                'success': False,
                'message': decision_result.get('message', '获取实时决策失败')
            })
        
        # 获取分时数据
        intraday_data = []
        if StockDataSource:
            try:
                data_source = StockDataSource()
                intraday_df = data_source.get_intraday_data(symbol)
                if not intraday_df.empty:
                    for _, row in intraday_df.iterrows():
                        intraday_data.append({
                            'time': str(row.get('time', '')),
                            'price': float(row.get('price', row.get('close', 0)) or 0),
                            'volume': float(row.get('volume', 0) or 0)
                        })
            except Exception as e:
                logger.warning(f"获取分时数据失败: {str(e)}")
        
        # 计算风险控制数据（如果启用）
        risk_control_data = None
        if RiskController:
            try:
                from config import TRADING_CONFIG
                risk_config = {
                    'max_total_position_pct': TRADING_CONFIG.get('max_total_position_pct', 80.0),
                    'max_single_position_pct': TRADING_CONFIG.get('max_single_position_pct', 30.0),
                    'max_correlation': TRADING_CONFIG.get('max_correlation', 0.8),
                    'enable_risk_control': TRADING_CONFIG.get('enable_risk_control', True),
                }
                risk_controller = RiskController(risk_config)
                
                # 模拟当前持仓（实际应该从数据库或用户配置获取）
                # 这里仅作为示例，实际应该获取真实的持仓数据
                current_positions = {}  # {symbol: position_pct}
                if holding and cost_price:
                    # 假设当前股票占10%仓位（实际应该从数据库获取）
                    current_positions[symbol] = 10.0
                
                # 计算组合风险
                risk_metrics = risk_controller.calculate_portfolio_risk(current_positions)
                risk_control_data = {
                    'risk_score': risk_metrics.get('risk_score', 0.0),
                    'total_position_pct': risk_metrics.get('total_position_pct', 0.0),
                    'position_count': risk_metrics.get('position_count', 0),
                    'max_single_position_pct': risk_metrics.get('max_single_position_pct', 0.0),
                    'position_concentration': risk_metrics.get('position_concentration', 0.0),
                    'warnings': risk_metrics.get('warnings', []),
                    'advice': risk_controller.get_risk_advice(risk_metrics)
                }
            except Exception as e:
                logger.debug(f"计算风险控制数据失败: {str(e)}")
        
        # 构建返回数据
        result_data = {
            'symbol': symbol,
            'name': stock_name,
            'timestamp': decision_result.get('timestamp', datetime.now().strftime('%Y-%m-%d %H:%M:%S')),
            'holding': holding,
            'cost_price': cost_price if cost_price and cost_price > 0 else None,
            'realtime_quote': decision_result.get('realtime_quote', {}),
            'decision': decision_result.get('decision', {}),
            'prediction': decision_result.get('prediction', {}),
            'capital_flow': decision_result.get('capital_flow', {}),
            'intraday_data': intraday_data,
            'data_quality': decision_result.get('data_quality', {}),  # 数据质量信息
            'risk_control': risk_control_data  # 风险控制信息
        }
        
        return jsonify({'success': True, 'data': result_data})
        
    except Exception as e:
        logger.error(f"获取实时策略数据失败: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({'success': False, 'message': str(e)})


# ========== 新闻抓取任务API ==========

@app.route('/api/news/tasks', methods=['GET'])
def api_get_news_tasks():
    """获取所有新闻抓取任务"""
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': '请先登录'})
    
    try:
        manager = get_news_task_manager()
        if manager is None:
            return jsonify({'success': False, 'message': '新闻任务管理器不可用', 'data': []})
        tasks = manager.get_all_tasks()
        return jsonify({'success': True, 'data': tasks})
    except Exception as e:
        logger.error(f"获取新闻任务列表失败: {str(e)}")
        return jsonify({'success': False, 'message': str(e), 'data': []})


@app.route('/api/news/tasks', methods=['POST'])
def api_create_news_task():
    """创建新闻抓取任务"""
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': '请先登录'})
    
    try:
        manager = get_news_task_manager()
        if manager is None:
            # 检查为什么管理器不可用
            if not NEWS_MODULE_AVAILABLE:
                return jsonify({'success': False, 'message': '新闻模块未启用，请检查系统配置'})
            else:
                return jsonify({'success': False, 'message': '新闻任务管理器初始化失败，请检查日志'})
        
        data = request.get_json()
        task_name = data.get('task_name', '未命名任务')
        task_type = data.get('task_type', 'market')  # market/stock/all
        schedule_type = data.get('schedule_type', 'interval')  # daily/hourly/interval
        schedule_time = data.get('schedule_time')  # 每日执行时间（HH:MM格式）
        interval_minutes = data.get('interval_minutes', 10)
        symbol = data.get('symbol')
        sources = data.get('sources', [])
        
        # 处理interval_minutes（可能是小数）
        if isinstance(interval_minutes, (int, float)):
            interval_minutes = float(interval_minutes)
        else:
            try:
                interval_minutes = float(interval_minutes)
            except (ValueError, TypeError):
                interval_minutes = 10.0
        
        # 验证间隔时间（对于时和分，最小0.1）
        if schedule_type in ['hourly', 'interval']:
            if interval_minutes < 0.1:
                return jsonify({'success': False, 'message': '间隔时间不能少于0.1'})
        else:
            # 每日执行不需要验证间隔
            pass
        
        task_id = manager.create_task(
            task_name=task_name,
            task_type=task_type,
            schedule_type=schedule_type,
            schedule_time=schedule_time,
            interval_minutes=interval_minutes,
            symbol=symbol,
            sources=sources
        )
        
        if task_id:
            return jsonify({'success': True, 'task_id': task_id})
        else:
            return jsonify({'success': False, 'message': '创建任务失败，请检查日志'})
    except Exception as e:
        logger.error(f"创建新闻任务失败: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({'success': False, 'message': f'创建任务失败: {str(e)}'})


@app.route('/api/news/tasks/<int:task_id>/start', methods=['POST'])
def api_start_news_task(task_id):
    """启动新闻抓取任务"""
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': '请先登录'})
    
    try:
        manager = get_news_task_manager()
        if manager is None:
            return jsonify({'success': False, 'message': '新闻任务管理器不可用'})
        success = manager.start_task(task_id)
        if success:
            return jsonify({'success': True, 'message': '任务已启动'})
        else:
            return jsonify({'success': False, 'message': '启动任务失败'})
    except Exception as e:
        logger.error(f"启动新闻任务失败: {str(e)}")
        return jsonify({'success': False, 'message': str(e)})


@app.route('/api/news/tasks/<int:task_id>/stop', methods=['POST'])
def api_stop_news_task(task_id):
    """停止新闻抓取任务"""
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': '请先登录'})
    
    try:
        manager = get_news_task_manager()
        if manager is None:
            return jsonify({'success': False, 'message': '新闻任务管理器不可用'})
        success = manager.stop_task(task_id)
        if success:
            return jsonify({'success': True, 'message': '任务已停止'})
        else:
            return jsonify({'success': False, 'message': '停止任务失败'})
    except Exception as e:
        logger.error(f"停止新闻任务失败: {str(e)}")
        return jsonify({'success': False, 'message': str(e)})


@app.route('/api/news/tasks/<int:task_id>', methods=['GET'])
def api_get_news_task(task_id):
    """获取新闻任务信息"""
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': '请先登录'})
    
    try:
        manager = get_news_task_manager()
        if manager is None:
            return jsonify({'success': False, 'message': '新闻任务管理器不可用'})
        task = manager.get_task(task_id)
        if task:
            stats = manager.get_task_statistics(task_id)
            return jsonify({'success': True, 'data': {**task, **stats}})
        else:
            return jsonify({'success': False, 'message': '任务不存在'})
    except Exception as e:
        logger.error(f"获取新闻任务失败: {str(e)}")
        return jsonify({'success': False, 'message': str(e)})


@app.route('/api/news/tasks/<int:task_id>', methods=['PUT'])
def api_update_news_task(task_id):
    """更新新闻任务"""
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': '请先登录'})
    
    try:
        manager = get_news_task_manager()
        if manager is None:
            return jsonify({'success': False, 'message': '新闻任务管理器不可用'})
        data = request.get_json()
        success = manager.update_task(task_id, **data)
        if success:
            return jsonify({'success': True, 'message': '任务已更新'})
        else:
            return jsonify({'success': False, 'message': '更新任务失败'})
    except Exception as e:
        logger.error(f"更新新闻任务失败: {str(e)}")
        return jsonify({'success': False, 'message': str(e)})


@app.route('/api/news/tasks/<int:task_id>', methods=['DELETE'])
def api_delete_news_task(task_id):
    """删除新闻任务"""
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': '请先登录'})
    
    try:
        manager = get_news_task_manager()
        if manager is None:
            return jsonify({'success': False, 'message': '新闻任务管理器不可用'})
        success = manager.delete_task(task_id)
        if success:
            return jsonify({'success': True, 'message': '任务已删除'})
        else:
            return jsonify({'success': False, 'message': '删除任务失败'})
    except Exception as e:
        logger.error(f"删除新闻任务失败: {str(e)}")
        return jsonify({'success': False, 'message': str(e)})


# ==================== 备份管理 API ====================

@app.route('/api/backup/info', methods=['GET'])
def api_get_backup_info():
    """获取备份信息"""
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': '请先登录'})
    
    try:
        manager = get_backup_manager()
        if manager is None:
            return jsonify({'success': False, 'message': '备份管理器不可用'})
        
        info = manager.get_backup_info()
        return jsonify({'success': True, 'data': info})
    except Exception as e:
        logger.error(f"获取备份信息失败: {str(e)}")
        return jsonify({'success': False, 'message': str(e)})


@app.route('/api/backup/list', methods=['GET'])
def api_list_backups():
    """列出所有备份"""
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': '请先登录'})
    
    try:
        manager = get_backup_manager()
        if manager is None:
            return jsonify({'success': False, 'message': '备份管理器不可用'})
        
        limit = request.args.get('limit', 50, type=int)
        backups = manager.list_backups(limit=limit)
        return jsonify({'success': True, 'data': backups})
    except Exception as e:
        logger.error(f"列出备份失败: {str(e)}")
        return jsonify({'success': False, 'message': str(e)})


@app.route('/api/backup/create', methods=['POST'])
def api_create_backup():
    """创建备份"""
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': '请先登录'})
    
    try:
        manager = get_backup_manager()
        if manager is None:
            return jsonify({'success': False, 'message': '备份管理器不可用'})
        
        data = request.get_json() or {}
        backup_type = data.get('backup_type', 'full')
        description = data.get('description', '手动备份')
        
        backup_info = manager.create_backup(backup_type=backup_type, description=description)
        
        if backup_info:
            return jsonify({'success': True, 'data': backup_info, 'message': '备份创建成功'})
        else:
            return jsonify({'success': False, 'message': '备份创建失败'})
    except Exception as e:
        logger.error(f"创建备份失败: {str(e)}")
        return jsonify({'success': False, 'message': str(e)})


@app.route('/api/backup/<int:backup_id>/delete', methods=['POST'])
def api_delete_backup(backup_id):
    """删除备份"""
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': '请先登录'})
    
    try:
        manager = get_backup_manager()
        if manager is None:
            return jsonify({'success': False, 'message': '备份管理器不可用'})
        
        success = manager.delete_backup(backup_id=backup_id)
        if success:
            return jsonify({'success': True, 'message': '备份已删除'})
        else:
            return jsonify({'success': False, 'message': '删除备份失败'})
    except Exception as e:
        logger.error(f"删除备份失败: {str(e)}")
        return jsonify({'success': False, 'message': str(e)})


@app.route('/api/backup/<int:backup_id>/restore', methods=['POST'])
def api_restore_backup(backup_id):
    """恢复备份"""
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': '请先登录'})
    
    try:
        manager = get_backup_manager()
        if manager is None:
            return jsonify({'success': False, 'message': '备份管理器不可用'})
        
        result = manager.restore_backup(backup_id=backup_id)
        return jsonify(result)
    except Exception as e:
        logger.error(f"恢复备份失败: {str(e)}")
        return jsonify({'success': False, 'message': str(e)})


# ========== 定时任务管理 API ==========

@app.route('/api/scheduled/tasks', methods=['GET'])
def api_get_scheduled_tasks():
    """获取所有定时任务"""
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': '请先登录'})
    
    try:
        manager = get_scheduled_task_manager()
        if manager is None:
            return jsonify({'success': False, 'message': '定时任务管理器不可用', 'data': []})
        tasks = manager.get_all_tasks()
        return jsonify({'success': True, 'data': tasks})
    except Exception as e:
        logger.error(f"获取定时任务列表失败: {str(e)}")
        return jsonify({'success': False, 'message': str(e), 'data': []})


@app.route('/api/scheduled/tasks', methods=['POST'])
def api_create_scheduled_task():
    """创建定时任务"""
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': '请先登录'})
    
    try:
        manager = get_scheduled_task_manager()
        if manager is None:
            return jsonify({'success': False, 'message': '定时任务管理器不可用'})
        
        data = request.get_json()
        task_name = data.get('task_name')
        task_type = data.get('task_type')
        schedule_type = data.get('schedule_type', 'daily')
        schedule_time = data.get('schedule_time')
        schedule_weekdays = data.get('schedule_weekdays')
        task_config = data.get('task_config', {})
        
        if not task_name or not task_type:
            return jsonify({'success': False, 'message': '任务名称和类型不能为空'})
        
        created_by = session.get('user_id')
        task_id = manager.create_task(
            task_name=task_name,
            task_type=task_type,
            schedule_type=schedule_type,
            schedule_time=schedule_time,
            schedule_weekdays=schedule_weekdays,
            task_config=task_config,
            created_by=created_by
        )
        
        if task_id:
            return jsonify({'success': True, 'message': '任务创建成功', 'task_id': task_id})
        else:
            return jsonify({'success': False, 'message': '创建任务失败'})
    except Exception as e:
        logger.error(f"创建定时任务失败: {str(e)}")
        return jsonify({'success': False, 'message': str(e)})


@app.route('/api/scheduled/tasks/<int:task_id>/start', methods=['POST'])
def api_start_scheduled_task(task_id):
    """启动定时任务"""
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': '请先登录'})
    
    try:
        # 获取任务来源参数
        task_source = request.args.get('source', 'scheduled_tasks')
        
        manager = get_scheduled_task_manager()
        if manager is None:
            return jsonify({'success': False, 'message': '定时任务管理器不可用'})
        
        # 如果是股票分析任务，需要特殊处理
        if task_source == 'analysis_tasks':
            # 从analysis_tasks表获取任务配置
            sql = "SELECT * FROM analysis_tasks WHERE id = %s"
            from utils.db_connection import DatabaseConnection
            db = DatabaseConnection()
            tasks = db.execute_query(sql, (task_id,))
            if tasks:
                task = tasks[0]
                # 调用原有的股票分析任务启动API
                # 这里需要复用api_start_task的逻辑
                return jsonify({'success': False, 'message': '股票分析任务请通过"开始分析"按钮启动'})
        
        success = manager.start_task(task_id, task_source=task_source)
        if success:
            return jsonify({'success': True, 'message': '任务已启动'})
        else:
            return jsonify({'success': False, 'message': '启动任务失败'})
    except Exception as e:
        logger.error(f"启动定时任务失败: {str(e)}")
        return jsonify({'success': False, 'message': str(e)})


@app.route('/api/scheduled/tasks/<int:task_id>/stop', methods=['POST'])
def api_stop_scheduled_task(task_id):
    """停止定时任务"""
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': '请先登录'})
    
    try:
        # 获取任务来源参数
        task_source = request.args.get('source', 'scheduled_tasks')
        
        manager = get_scheduled_task_manager()
        if manager is None:
            return jsonify({'success': False, 'message': '定时任务管理器不可用'})
        
        # 如果是股票分析任务，需要调用原有的停止接口
        if task_source == 'analysis_tasks':
            # 调用原有的停止API
            task_id_str = str(task_id)
            with task_lock:
                if task_id_str in task_stop_flags:
                    task_stop_flags[task_id_str] = True
                    return jsonify({'success': True, 'message': '已发送停止信号'})
                else:
                    return jsonify({'success': False, 'message': '任务不在运行中'})
        
        success = manager.stop_task(task_id, task_source=task_source)
        if success:
            return jsonify({'success': True, 'message': '任务已停止'})
        else:
            return jsonify({'success': False, 'message': '停止任务失败'})
    except Exception as e:
        logger.error(f"停止定时任务失败: {str(e)}")
        return jsonify({'success': False, 'message': str(e)})


@app.route('/api/scheduled/tasks/<int:task_id>', methods=['GET'])
def api_get_scheduled_task(task_id):
    """获取定时任务信息"""
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': '请先登录'})
    
    try:
        manager = get_scheduled_task_manager()
        if manager is None:
            return jsonify({'success': False, 'message': '定时任务管理器不可用'})
        task = manager.get_task(task_id)
        if task:
            return jsonify({'success': True, 'data': task})
        else:
            return jsonify({'success': False, 'message': '任务不存在'})
    except Exception as e:
        logger.error(f"获取定时任务失败: {str(e)}")
        return jsonify({'success': False, 'message': str(e)})


@app.route('/api/scheduled/tasks/<int:task_id>', methods=['DELETE'])
def api_delete_scheduled_task(task_id):
    """删除定时任务"""
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': '请先登录'})
    
    try:
        manager = get_scheduled_task_manager()
        if manager is None:
            return jsonify({'success': False, 'message': '定时任务管理器不可用'})
        success = manager.delete_task(task_id)
        if success:
            return jsonify({'success': True, 'message': '任务已删除'})
        else:
            return jsonify({'success': False, 'message': '删除任务失败'})
    except Exception as e:
        logger.error(f"删除定时任务失败: {str(e)}")
        return jsonify({'success': False, 'message': str(e)})


@app.route('/api/stock-data/tasks', methods=['GET'])
def api_get_stock_data_tasks():
    """获取股票数据获取任务列表（支持分页）"""
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': '请先登录'}), 401
    
    try:
        page = request.args.get('page', 1, type=int)
        page_size = request.args.get('page_size', 20, type=int)
        task_type = request.args.get('task_type', None)  # stock_data_collection_cn, stock_data_collection_us
        
        manager = get_scheduled_task_manager()
        if manager is None:
            return jsonify({'success': False, 'message': '定时任务管理器不可用', 'data': [], 'total': 0, 'page': page, 'page_size': page_size})
        
        # 获取所有任务
        all_tasks = manager.get_all_tasks()
        
        # 过滤股票数据获取任务
        stock_data_tasks = []
        for task in all_tasks:
            if task.get('task_type') in ['stock_data_collection_cn', 'stock_data_collection_us']:
                if task_type is None or task.get('task_type') == task_type:
                    stock_data_tasks.append(task)
        
        # 分页
        total = len(stock_data_tasks)
        start = (page - 1) * page_size
        end = start + page_size
        paginated_tasks = stock_data_tasks[start:end]
        
        return jsonify({
            'success': True,
            'data': paginated_tasks,
            'total': total,
            'page': page,
            'page_size': page_size,
            'total_pages': (total + page_size - 1) // page_size
        })
    except Exception as e:
        logger.error(f"获取股票数据获取任务列表失败: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({'success': False, 'message': str(e), 'data': [], 'total': 0, 'page': 1, 'page_size': 20})


@app.route('/api/stock-data/tasks', methods=['POST'])
def api_create_stock_data_task():
    """创建股票数据获取任务"""
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': '请先登录'}), 401
    
    try:
        manager = get_scheduled_task_manager()
        if manager is None:
            # 检查为什么管理器不可用
            if not SCHEDULED_TASK_MANAGER_AVAILABLE:
                return jsonify({'success': False, 'message': '定时任务管理器模块未启用，请检查系统配置'})
            else:
                return jsonify({'success': False, 'message': '定时任务管理器初始化失败，请检查日志'})
        
        data = request.get_json()
        task_name = data.get('task_name')
        market_type = data.get('market_type')  # 'cn' or 'us'
        collection_type = data.get('collection_type', 'incremental')  # 'incremental' or 'full'
        schedule_type = data.get('schedule_type', 'daily')
        schedule_time = data.get('schedule_time')
        schedule_weekdays = data.get('schedule_weekdays')
        
        # 任务配置
        task_config = {
            'collection_type': collection_type
        }
        
        if market_type == 'cn':
            task_type = 'stock_data_collection_cn'
            symbols = data.get('symbols', None)
            # 只有全量收集才需要years参数
            if collection_type == 'full':
                years = data.get('years', 10)
                task_config['years'] = years
            if symbols:
                task_config['symbols'] = symbols
        elif market_type == 'us':
            task_type = 'stock_data_collection_us'
            symbols = data.get('symbols', None)
            period = data.get('period', '10y')
            index_type = data.get('index_type', None)  # 'sp500', 'nasdaq100', or None
            if symbols:
                task_config['symbols'] = symbols
            task_config['period'] = period
            if index_type:
                task_config['index_type'] = index_type
        else:
            return jsonify({'success': False, 'message': 'market_type必须是cn或us'})
        
        if not task_name:
            return jsonify({'success': False, 'message': '任务名称不能为空'})
        
        created_by = session.get('user_id')
        task_id = manager.create_task(
            task_name=task_name,
            task_type=task_type,
            schedule_type=schedule_type,
            schedule_time=schedule_time,
            schedule_weekdays=schedule_weekdays,
            task_config=task_config,
            created_by=created_by
        )
        
        if task_id:
            return jsonify({'success': True, 'message': '任务创建成功', 'task_id': task_id})
        else:
            return jsonify({'success': False, 'message': '创建任务失败'})
    except Exception as e:
        logger.error(f"创建股票数据获取任务失败: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({'success': False, 'message': str(e)})


@app.route('/api/stock-data/tasks/<int:task_id>/history', methods=['GET'])
def api_get_stock_data_task_history(task_id):
    """获取股票数据获取任务历史记录（支持分页）"""
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': '请先登录'}), 401
    
    try:
        page = request.args.get('page', 1, type=int)
        page_size = request.args.get('page_size', 20, type=int)
        
        manager = get_scheduled_task_manager()
        if manager is None:
            return jsonify({'success': False, 'message': '定时任务管理器不可用', 'data': [], 'total': 0})
        
        # 获取任务历史记录
        history = manager.get_task_history(task_id, limit=None)
        
        # 分页
        total = len(history) if history else 0
        start = (page - 1) * page_size
        end = start + page_size
        paginated_history = history[start:end] if history else []
        
        return jsonify({
            'success': True,
            'data': paginated_history,
            'total': total,
            'page': page,
            'page_size': page_size,
            'total_pages': (total + page_size - 1) // page_size
        })
    except Exception as e:
        logger.error(f"获取任务历史记录失败: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({'success': False, 'message': str(e), 'data': [], 'total': 0})


@app.route('/api/scheduled/tasks/<int:task_id>/history', methods=['GET'])
def api_get_scheduled_task_history(task_id):
    """获取定时任务执行历史"""
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': '请先登录'})
    
    try:
        manager = get_scheduled_task_manager()
        if manager is None:
            return jsonify({'success': False, 'message': '定时任务管理器不可用', 'data': []})
        limit = int(request.args.get('limit', 50))
        history = manager.get_task_history(task_id=task_id, limit=limit)
        return jsonify({'success': True, 'data': history})
    except Exception as e:
        logger.error(f"获取定时任务历史失败: {str(e)}")
        return jsonify({'success': False, 'message': str(e), 'data': []})


@app.route('/api/news/articles', methods=['GET'])
def api_get_news_articles():
    """获取新闻文章列表"""
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': '请先登录'})
    
    try:
        storage = get_news_storage()
        if storage is None:
            return jsonify({'success': False, 'message': '新闻存储管理器不可用', 'data': []})
        
        symbol = request.args.get('symbol')
        sentiment = request.args.get('sentiment')  # positive/negative/neutral
        # 验证limit（防止SQL注入和无效输入）
        try:
            limit_raw = request.args.get('limit', '20')
            limit = int(limit_raw)
            if limit <= 0 or limit > 1000:  # 设置上限
                limit = 20
        except (ValueError, TypeError):
            limit = 20
        
        if symbol:
            articles = storage.get_news_by_symbol(symbol, limit=limit, sentiment=sentiment)
        else:
            # 获取市场新闻
            if not USE_DATABASE:
                return jsonify({'success': False, 'message': '数据库未启用', 'data': []})
            
            sql = """
                SELECT * FROM news_articles 
                WHERE news_type = 'market'
            """
            params = []
            if sentiment:
                sql += " AND sentiment = %s"
                params.append(sentiment)
            sql += " ORDER BY publish_time DESC LIMIT %s"
            params.append(limit)
            
            articles = DatabaseConnection.execute_query(sql, tuple(params))
        
        return jsonify({'success': True, 'data': articles, 'total': len(articles)})
    except Exception as e:
        logger.error(f"获取新闻文章失败: {str(e)}")
        return jsonify({'success': False, 'message': str(e), 'data': []})


@app.route('/api/news/search', methods=['GET'])
def api_search_news():
    """搜索新闻（支持多种筛选条件）"""
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': '请先登录'}), 401
    
    try:
        from utils.news_search import NewsSearch
        
        searcher = NewsSearch()
        
        # 获取搜索参数
        keyword = request.args.get('keyword')
        symbol = request.args.get('symbol')
        sentiment = request.args.get('sentiment')  # positive/negative/neutral
        date_from = request.args.get('date_from')
        date_to = request.args.get('date_to')
        sector = request.args.get('sector')
        industry = request.args.get('industry')
        news_type = request.args.get('news_type')  # stock/market/policy/industry
        is_positive = request.args.get('is_positive')  # true/false
        is_negative = request.args.get('is_negative')  # true/false
        is_policy = request.args.get('is_policy')  # true/false
        page = request.args.get('page', 1, type=int)
        page_size = request.args.get('page_size', 20, type=int)
        sort_by = request.args.get('sort_by', 'publish_time')  # publish_time/relevance_score/sentiment_score
        sort_order = request.args.get('sort_order', 'DESC')  # ASC/DESC
        
        # 转换布尔值
        is_positive_bool = None if is_positive is None else is_positive.lower() == 'true'
        is_negative_bool = None if is_negative is None else is_negative.lower() == 'true'
        is_policy_bool = None if is_policy is None else is_policy.lower() == 'true'
        
        # 执行搜索
        result = searcher.search(
            keyword=keyword,
            symbol=symbol,
            sentiment=sentiment,
            date_from=date_from,
            date_to=date_to,
            sector=sector,
            industry=industry,
            news_type=news_type,
            is_positive=is_positive_bool,
            is_negative=is_negative_bool,
            is_policy=is_policy_bool,
            page=page,
            page_size=page_size,
            sort_by=sort_by,
            sort_order=sort_order
        )
        
        return jsonify({
            'success': True,
            'data': result['data'],
            'total': result['total'],
            'page': result['page'],
            'page_size': result['page_size'],
            'total_pages': result['total_pages']
        })
    except Exception as e:
        logger.error(f"搜索新闻失败: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({'success': False, 'message': str(e), 'data': [], 'total': 0})


@app.route('/api/news/search/suggestions', methods=['GET'])
def api_get_search_suggestions():
    """获取搜索建议（自动补全）"""
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': '请先登录'}), 401
    
    try:
        from utils.news_search import NewsSearch
        
        searcher = NewsSearch()
        keyword = request.args.get('keyword', '')
        limit = request.args.get('limit', 10, type=int)
        
        suggestions = searcher.get_search_suggestions(keyword, limit=limit)
        
        return jsonify({
            'success': True,
            'data': suggestions
        })
    except Exception as e:
        logger.error(f"获取搜索建议失败: {str(e)}")
        return jsonify({'success': False, 'message': str(e), 'data': []})


@app.route('/api/news/statistics', methods=['GET'])
def api_get_news_statistics():
    """获取新闻统计信息"""
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': '请先登录'})
    
    try:
        storage = get_news_storage()
        if storage is None:
            return jsonify({'success': False, 'message': '新闻存储管理器不可用', 'data': {}})
        
        symbol = request.args.get('symbol')
        days = int(request.args.get('days', 7))
        
        stats = storage.get_news_statistics(symbol=symbol, days=days)
        return jsonify({'success': True, 'data': stats})
    except Exception as e:
        logger.error(f"获取新闻统计失败: {str(e)}")
        return jsonify({'success': False, 'message': str(e), 'data': {}})


# ========== 新闻推送通知 API ==========

@app.route('/api/news/notifications', methods=['GET'])
def api_get_news_notifications():
    """获取推送通知列表（推送历史）"""
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': '请先登录'})
    
    try:
        manager = get_news_notification_manager()
        if manager is None:
            return jsonify({'success': False, 'message': '新闻推送通知管理器不可用', 'data': []})
        
        user_id = session.get('user_id')
        limit = int(request.args.get('limit', 20))
        unread_only = request.args.get('unread_only', 'false').lower() == 'true'
        
        notifications = manager.get_user_notifications(user_id, limit=limit, unread_only=unread_only)
        return jsonify({'success': True, 'data': notifications, 'total': len(notifications)})
    except Exception as e:
        logger.error(f"获取推送通知列表失败: {str(e)}")
        return jsonify({'success': False, 'message': str(e), 'data': []})


@app.route('/api/news/notifications/history', methods=['GET'])
def api_get_notification_history():
    """获取推送历史记录"""
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': '请先登录'})
    
    try:
        manager = get_news_notification_manager()
        if manager is None:
            return jsonify({'success': False, 'message': '新闻推送通知管理器不可用', 'data': []})
        
        user_id = session.get('user_id')
        limit = int(request.args.get('limit', 50))
        days = int(request.args.get('days', 7))
        
        history = manager.get_notification_history(user_id=user_id, limit=limit, days=days)
        return jsonify({'success': True, 'data': history, 'total': len(history)})
    except Exception as e:
        logger.error(f"获取推送历史失败: {str(e)}")
        return jsonify({'success': False, 'message': str(e), 'data': []})


@app.route('/api/news/notifications/rules', methods=['GET'])
def api_get_notification_rules():
    """获取推送规则配置"""
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': '请先登录'})
    
    try:
        manager = get_news_notification_manager()
        if manager is None:
            return jsonify({'success': False, 'message': '新闻推送通知管理器不可用', 'data': {}})
        
        user_id = session.get('user_id')
        rules = manager.get_user_notification_rules(user_id)
        return jsonify({'success': True, 'data': rules})
    except Exception as e:
        logger.error(f"获取推送规则失败: {str(e)}")
        return jsonify({'success': False, 'message': str(e), 'data': {}})


@app.route('/api/news/notifications/rules', methods=['POST'])
def api_update_notification_rules():
    """更新推送规则配置"""
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': '请先登录'})
    
    try:
        manager = get_news_notification_manager()
        if manager is None:
            return jsonify({'success': False, 'message': '新闻推送通知管理器不可用'})
        
        user_id = session.get('user_id')
        data = request.get_json()
        rules = data.get('rules', {})
        
        success = manager.update_user_notification_rules(user_id, rules)
        if success:
            return jsonify({'success': True, 'message': '推送规则更新成功'})
        else:
            return jsonify({'success': False, 'message': '推送规则更新失败'})
    except Exception as e:
        logger.error(f"更新推送规则失败: {str(e)}")
        return jsonify({'success': False, 'message': str(e)})


# ========== 预测参数配置 API ==========

@app.route('/api/prediction/configs', methods=['GET'])
def api_get_prediction_configs():
    """获取所有预测配置列表"""
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': '请先登录'}), 401
    
    try:
        manager = get_prediction_config_manager()
        if manager is None:
            return jsonify({'success': False, 'message': '预测参数配置管理器不可用', 'data': []})
        
        configs = manager.get_all_configs()
        return jsonify({'success': True, 'data': configs})
    except Exception as e:
        logger.error(f"获取预测配置列表失败: {str(e)}")
        return jsonify({'success': False, 'message': str(e), 'data': []})


@app.route('/api/prediction/config/<int:config_id>', methods=['GET'])
def api_get_prediction_config(config_id):
    """获取指定配置详情"""
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': '请先登录'}), 401
    
    try:
        manager = get_prediction_config_manager()
        if manager is None:
            return jsonify({'success': False, 'message': '预测参数配置管理器不可用'})
        
        config_info = manager.get_config_info(config_id)
        config_values = manager.get_config(config_id)
        
        if config_info is None:
            return jsonify({'success': False, 'message': '配置不存在'})
        
        return jsonify({
            'success': True,
            'data': {
                'info': config_info,
                'values': config_values
            }
        })
    except Exception as e:
        logger.error(f"获取预测配置失败: {str(e)}")
        return jsonify({'success': False, 'message': str(e)})


@app.route('/api/prediction/config/active', methods=['GET'])
def api_get_active_prediction_config():
    """获取当前激活的配置"""
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': '请先登录'}), 401
    
    try:
        manager = get_prediction_config_manager()
        if manager is None:
            return jsonify({'success': False, 'message': '预测参数配置管理器不可用'})
        
        active_config_id = manager.get_active_config_id()
        if active_config_id is None:
            return jsonify({
                'success': True,
                'data': {
                    'info': None,
                    'values': None,
                    'message': '当前未激活任何配置，使用config.py中的默认值'
                }
            })
        
        config_info = manager.get_config_info(active_config_id)
        config_values = manager.get_config(active_config_id)
        
        return jsonify({
            'success': True,
            'data': {
                'info': config_info,
                'values': config_values
            }
        })
    except Exception as e:
        logger.error(f"获取激活配置失败: {str(e)}")
        return jsonify({'success': False, 'message': str(e)})


@app.route('/api/prediction/config', methods=['POST'])
def api_create_prediction_config():
    """创建新配置"""
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': '请先登录'}), 401
    
    try:
        manager = get_prediction_config_manager()
        if manager is None:
            return jsonify({'success': False, 'message': '预测参数配置管理器不可用'})
        
        data = request.get_json()
        config_name = data.get('config_name')
        description = data.get('description', '')
        values = data.get('values', {})
        is_default = data.get('is_default', False)
        
        if not config_name:
            return jsonify({'success': False, 'message': '配置名称不能为空'})
        
        if not values:
            return jsonify({'success': False, 'message': '配置值不能为空'})
        
        user_id = session.get('user_id')
        config_id = manager.create_config(
            config_name=config_name,
            description=description,
            values=values,
            user_id=user_id,
            is_default=is_default
        )
        
        if config_id:
            return jsonify({'success': True, 'message': '配置创建成功', 'data': {'id': config_id}})
        else:
            return jsonify({'success': False, 'message': '配置创建失败'})
    except Exception as e:
        logger.error(f"创建预测配置失败: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({'success': False, 'message': str(e)})


@app.route('/api/prediction/config/<int:config_id>', methods=['PUT'])
def api_update_prediction_config(config_id):
    """更新配置"""
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': '请先登录'}), 401
    
    try:
        manager = get_prediction_config_manager()
        if manager is None:
            return jsonify({'success': False, 'message': '预测参数配置管理器不可用'})
        
        data = request.get_json()
        config_name = data.get('config_name')
        description = data.get('description')
        values = data.get('values')
        
        user_id = session.get('user_id')
        success = manager.update_config(
            config_id=config_id,
            config_name=config_name,
            description=description,
            values=values,
            user_id=user_id
        )
        
        if success:
            return jsonify({'success': True, 'message': '配置更新成功'})
        else:
            return jsonify({'success': False, 'message': '配置更新失败'})
    except Exception as e:
        logger.error(f"更新预测配置失败: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({'success': False, 'message': str(e)})


@app.route('/api/prediction/config/<int:config_id>', methods=['DELETE'])
def api_delete_prediction_config(config_id):
    """删除配置"""
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': '请先登录'}), 401
    
    try:
        manager = get_prediction_config_manager()
        if manager is None:
            return jsonify({'success': False, 'message': '预测参数配置管理器不可用'})
        
        user_id = session.get('user_id')
        success = manager.delete_config(config_id, user_id=user_id)
        
        if success:
            return jsonify({'success': True, 'message': '配置删除成功'})
        else:
            return jsonify({'success': False, 'message': '配置删除失败（可能是激活的配置或配置不存在）'})
    except Exception as e:
        logger.error(f"删除预测配置失败: {str(e)}")
        return jsonify({'success': False, 'message': str(e)})


@app.route('/api/prediction/config/<int:config_id>/activate', methods=['POST'])
def api_activate_prediction_config(config_id):
    """激活配置"""
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': '请先登录'}), 401
    
    try:
        manager = get_prediction_config_manager()
        if manager is None:
            return jsonify({'success': False, 'message': '预测参数配置管理器不可用'})
        
        user_id = session.get('user_id')
        success = manager.activate_config(config_id, user_id=user_id)
        
        if success:
            return jsonify({'success': True, 'message': '配置激活成功'})
        else:
            return jsonify({'success': False, 'message': '配置激活失败（配置可能不存在）'})
    except Exception as e:
        logger.error(f"激活预测配置失败: {str(e)}")
        return jsonify({'success': False, 'message': str(e)})


@app.route('/api/prediction/config/validate', methods=['POST'])
def api_validate_prediction_config():
    """验证配置值"""
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': '请先登录'}), 401
    
    try:
        manager = get_prediction_config_manager()
        if manager is None:
            return jsonify({'success': False, 'message': '预测参数配置管理器不可用'})
        
        data = request.get_json()
        values = data.get('values', {})
        
        is_valid, error_msg = manager.validate_config(values)
        
        return jsonify({
            'success': is_valid,
            'message': error_msg,
            'is_valid': is_valid
        })
    except Exception as e:
        logger.error(f"验证配置失败: {str(e)}")
        return jsonify({'success': False, 'message': str(e), 'is_valid': False})


@app.route('/api/prediction/config/<int:config_id>/history', methods=['GET'])
def api_get_prediction_config_history(config_id):
    """获取配置变更历史"""
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': '请先登录'}), 401
    
    try:
        manager = get_prediction_config_manager()
        if manager is None:
            return jsonify({'success': False, 'message': '预测参数配置管理器不可用', 'data': []})
        
        limit = request.args.get('limit', 50, type=int)
        history = manager.get_config_history(config_id, limit=limit)
        
        return jsonify({'success': True, 'data': history})
    except Exception as e:
        logger.error(f"获取配置历史失败: {str(e)}")
        return jsonify({'success': False, 'message': str(e), 'data': []})


# ========== 模型学习 API ==========

@app.route('/api/model/evaluate', methods=['GET'])
def api_model_evaluate():
    """执行模型性能评估"""
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': '请先登录'}), 401
    
    if not MODEL_LEARNING_AVAILABLE:
        return jsonify({'success': False, 'message': '模型学习模块不可用'})
    
    try:
        days = request.args.get('days', 30, type=int)
        
        evaluator = ModelPerformanceEvaluator()
        
        # 评估预测性能
        prediction_result = evaluator.evaluate_prediction_performance(days=days)
        
        # 评估交易性能
        trading_result = evaluator.evaluate_trading_performance(days=days)
        
        # 合并结果
        result = {
            'prediction': prediction_result if prediction_result.get('success') else None,
            'trading': trading_result if trading_result.get('success') else None
        }
        
        # 如果预测评估成功，返回其主要指标
        if prediction_result.get('success'):
            result.update({
                'direction_accuracy': prediction_result.get('direction_accuracy', 0),
                'magnitude_mae': prediction_result.get('magnitude_mae', 0),
                'factor_contributions': prediction_result.get('factor_contributions', {}),
                'market_condition': prediction_result.get('market_condition', 'unknown')
            })
        
        # 如果交易评估成功，返回其主要指标
        if trading_result.get('success'):
            result.update({
                'total_return': trading_result.get('total_return', 0),
                'win_rate': trading_result.get('win_rate', 0),
                'win_count': trading_result.get('win_count', 0),
                'loss_count': trading_result.get('loss_count', 0),
                'max_drawdown': 0  # TODO: 从回测结果中获取
            })
        
        return jsonify({'success': True, 'data': result})
        
    except Exception as e:
        logger.error(f"模型性能评估失败: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({'success': False, 'message': str(e)})


@app.route('/api/model/optimize', methods=['POST'])
def api_model_optimize():
    """执行参数优化"""
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': '请先登录'}), 401
    
    if not MODEL_LEARNING_AVAILABLE:
        return jsonify({'success': False, 'message': '模型学习模块不可用'})
    
    try:
        data = request.get_json()
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        
        if not start_date or not end_date:
            # 如果没有提供日期，使用默认值（最近30天）
            end_date_obj = datetime.now().date()
            start_date_obj = end_date_obj - timedelta(days=30)
            start_date = start_date_obj.strftime('%Y-%m-%d')
            end_date = end_date_obj.strftime('%Y-%m-%d')
        
        optimizer = ModelOptimizer()
        
        # 获取自动应用阈值（默认5%）
        auto_apply_threshold = data.get('auto_apply_threshold', 5.0)
        
        # 执行优化（使用较小的搜索空间以加快速度）
        optimization_config = {
            'search_space': {
                'news_weight': [0.20, 0.25, 0.30],
                'capital_flow_weight': [0.15, 0.18, 0.20],
                'market_weight': [0.15, 0.17, 0.20],
                'technical_weight': [0.18, 0.20, 0.22]
            },
            'auto_apply_threshold': auto_apply_threshold  # 自动应用阈值
        }
        
        result = optimizer.optimize_weights_grid_search(
            start_date=start_date,
            end_date=end_date,
            optimization_config=optimization_config
        )
        
        if result.get('success'):
            optimization_id = result.get('optimization_id', None)
            is_auto_applied = result.get('is_auto_applied', False)
            
            message = '参数优化完成'
            if is_auto_applied:
                message += '（已自动应用）'
            
            return jsonify({
                'success': True,
                'optimization_id': optimization_id,
                'best_score': result.get('best_score'),
                'current_score': result.get('current_score'),
                'improvement_pct': result.get('improvement_pct'),
                'is_auto_applied': is_auto_applied,
                'message': message
            })
        else:
            return jsonify({'success': False, 'message': result.get('message', '优化失败')})
        
    except Exception as e:
        logger.error(f"参数优化失败: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({'success': False, 'message': str(e)})


@app.route('/api/model/optimization-history', methods=['GET'])
def api_get_optimization_history():
    """获取优化历史记录"""
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': '请先登录'}), 401
    
    if not MODEL_LEARNING_AVAILABLE:
        return jsonify({'success': False, 'message': '模型学习模块不可用'})
    
    try:
        limit = request.args.get('limit', 20, type=int)
        
        updater = ModelParameterUpdater()
        history = updater.get_optimization_history(limit=limit)
        
        return jsonify({'success': True, 'data': history})
        
    except Exception as e:
        logger.error(f"获取优化历史失败: {str(e)}")
        return jsonify({'success': False, 'message': str(e)})


@app.route('/api/model/apply-optimization/<int:optimization_id>', methods=['POST'])
def api_apply_optimization(optimization_id):
    """应用优化后的参数"""
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': '请先登录'}), 401
    
    if not MODEL_LEARNING_AVAILABLE:
        return jsonify({'success': False, 'message': '模型学习模块不可用'})
    
    try:
        user_id = session.get('user_id')
        
        updater = ModelParameterUpdater()
        result = updater.apply_optimized_parameters(
            optimization_id=optimization_id,
            user_id=user_id,
            force=False
        )
        
        if result.get('success'):
            logger.info("优化参数已应用，建议刷新预测配置以生效")
            
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"应用优化参数失败: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({'success': False, 'message': str(e)})


@app.route('/api/backtest/run', methods=['POST'])
def api_backtest_run():
    """执行回测"""
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': '请先登录'}), 401
    
    if not MODEL_LEARNING_AVAILABLE or BacktestEngine is None:
        return jsonify({'success': False, 'message': '回测模块不可用'})
    
    try:
        data = request.get_json()
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        initial_capital = data.get('initial_capital', 100000.0)
        generate_visualization = data.get('generate_visualization', True)
        
        if not start_date or not end_date:
            # 如果没有提供日期，使用默认值（最近30天）
            end_date_obj = datetime.now().date()
            start_date_obj = end_date_obj - timedelta(days=30)
            start_date = start_date_obj.strftime('%Y-%m-%d')
            end_date = end_date_obj.strftime('%Y-%m-%d')
        
        engine = BacktestEngine()
        backtest_result = engine.backtest_predictions(
            start_date=start_date,
            end_date=end_date,
            initial_capital=initial_capital
        )
        
        if backtest_result.get('success'):
            # 如果请求生成可视化，则生成HTML报告
            visualization_path = None
            if generate_visualization and BacktestVisualizer is not None:
                try:
                    visualizer = BacktestVisualizer()
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    filename = f"backtest_{start_date}_{end_date}_{timestamp}.html"
                    visualization_path = visualizer.visualize_backtest_result(
                        backtest_result, filename=filename
                    )
                    # 返回相对路径（用于Web访问）
                    if visualization_path:
                        visualization_path = os.path.basename(visualization_path)
                except Exception as e:
                    logger.warning(f"生成回测可视化报告失败: {str(e)}")
            
            return jsonify({
                'success': True,
                'data': backtest_result,
                'visualization_path': visualization_path
            })
        else:
            return jsonify({
                'success': False,
                'message': backtest_result.get('message', '回测失败')
            })
        
    except Exception as e:
        logger.error(f"执行回测失败: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({'success': False, 'message': str(e)})


@app.route('/api/backtest/result/<path:filename>', methods=['GET'])
def api_backtest_result_file(filename):
    """获取回测结果HTML文件"""
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': '请先登录'}), 401
    
    try:
        # 确保文件在reports目录下（安全措施）
        reports_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'reports')
        filepath = os.path.join(reports_dir, filename)
        
        # 安全检查：确保文件在reports目录内
        if not os.path.abspath(filepath).startswith(os.path.abspath(reports_dir)):
            return jsonify({'success': False, 'message': '无效的文件路径'}), 403
        
        if not os.path.exists(filepath):
            return jsonify({'success': False, 'message': '文件不存在'}), 404
        
        # 返回HTML文件
        from flask import send_from_directory
        return send_from_directory(reports_dir, filename)
        
    except Exception as e:
        logger.error(f"获取回测结果文件失败: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/api/predict/before_close', methods=['POST'])
@rate_limit(max_per_minute=30)  # 每分钟最多30次请求
def api_predict_before_close():
    """预测股票走势（未收盘-明天）
    
    使用：
    - 新闻源：数据库中的当天新闻
    - 当天股票数据：实时获取
    - 历史股票数据：数据库中的数据
    """
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': '请先登录'}), 401
    
    # 检查市场是否收盘
    market_status = is_market_open()
    if not market_status['is_trading']:
        return jsonify({'success': False, 'message': f'市场已收盘，无法进行预测（{market_status["message"]}）'})
    
    try:
        data = request.get_json()
        symbols = data.get('symbols', [])
        
        if not symbols or not isinstance(symbols, list):
            return jsonify({'success': False, 'message': '股票代码列表不能为空'})
        
        if len(symbols) > 10:
            return jsonify({'success': False, 'message': '最多只能预测10只股票'})
        
        # 验证股票代码格式（防止注入和无效输入）
        validated_symbols = []
        for symbol in symbols:
            symbol_str = str(symbol).strip()
            # 验证：只允许6位数字
            if not symbol_str or not symbol_str.isdigit() or len(symbol_str) != 6:
                return jsonify({'success': False, 'message': f'股票代码格式错误: {symbol_str}（应为6位数字）'})
            validated_symbols.append(symbol_str.zfill(6))
        
        if StockPredictor is None or PredictionVisualizer is None:
            return jsonify({'success': False, 'message': '预测模块未加载'})
        
        predictor = StockPredictor()
        visualizer = PredictionVisualizer()
        
        success_count = 0
        fail_count = 0
        results = []
        
        for symbol in validated_symbols:
            try:
                logger.info(f"开始预测股票（未收盘-明天）: {symbol}")
                
                # 执行预测（会自动使用数据库新闻和历史数据，实时获取当天数据）
                prediction_result = predictor.predict(symbol)
                
                if not prediction_result.get('success', False):
                    logger.warning(f"预测失败: {symbol} - {prediction_result.get('message', '未知错误')}")
                    fail_count += 1
                    results.append({
                        'symbol': symbol,
                        'success': False,
                        'message': prediction_result.get('message', '预测失败')
                    })
                    continue
                
                # 设置预测类型为"未收盘-明天"
                prediction_result['prediction_type'] = 'before_close'
                
                # 保存预测结果
                visualizer.save_stock_record(symbol, prediction_result)
                
                success_count += 1
                results.append({
                    'symbol': symbol,
                    'success': True,
                    'prediction': prediction_result.get('prediction', '震荡'),
                    'up_probability': prediction_result.get('up_probability', 0),
                    'down_probability': prediction_result.get('down_probability', 0),
                    'confidence': prediction_result.get('confidence', 0)
                })
                
                logger.info(f"预测完成: {symbol} - {prediction_result.get('prediction', '震荡')}")
                
            except Exception as e:
                logger.error(f"预测股票 {symbol} 异常: {str(e)}")
                import traceback
                logger.error(traceback.format_exc())
                fail_count += 1
                results.append({
                    'symbol': symbol,
                    'success': False,
                    'message': str(e)
                })
        
        return jsonify({
            'success': True,
            'message': f'预测完成: 成功 {success_count}, 失败 {fail_count}',
            'data': {
                'success_count': success_count,
                'fail_count': fail_count,
                'total': len(symbols),
                'results': results
            }
        })
        
    except Exception as e:
        logger.error(f"预测失败: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return jsonify({'success': False, 'message': str(e)})


if __name__ == '__main__':
    print("=" * 60)
    print("股票预测系统 Web 应用")
    print("=" * 60)
    print("访问地址: http://localhost:5000")
    print("默认账号: admin / admin123")
    print("=" * 60)
    print("\n重要提示：")
    print("   - Web服务启动时不会自动运行任何分析或抓取任务")
    print("   - 所有任务必须通过Web界面手动启动")
    print("   - 股票分析：在设置页面 > 任务管理")
    print("   - 新闻抓取：在设置页面 > 新闻抓取")
    print("=" * 60)
    print("\n按 Ctrl+C 停止服务器\n")
    
    # 确保服务启动时不会自动运行任何任务
    # 所有任务必须通过API接口手动触发
    
    socketio.run(app, host='0.0.0.0', port=5000, debug=True)
