"""
错误处理工具模块

提供统一的错误处理装饰器和工具函数，简化API端点的错误处理。
"""
from functools import wraps
from typing import Callable, Any
from flask import jsonify, request
import traceback
from utils.logger import get_logger
from utils.exceptions import BaseAPIException

logger = get_logger(__name__)


def handle_api_error(func: Callable) -> Callable:
    """
    API错误处理装饰器
    
    自动捕获异常并转换为统一的JSON响应格式。
    
    使用示例：
        @app.route('/api/example')
        @handle_api_error
        def api_example():
            # 抛出异常会自动转换为JSON响应
            raise ValidationError("参数错误")
            # 或返回普通响应
            return jsonify({'success': True, 'data': {}})
    
    Args:
        func: 要装饰的函数
    
    Returns:
        装饰后的函数
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            # 执行原函数
            result = func(*args, **kwargs)
            
            # 如果返回的是tuple（Flask响应格式），直接返回
            if isinstance(result, tuple) and len(result) >= 2:
                return result
            
            # 如果已经返回jsonify响应，直接返回
            if hasattr(result, 'headers') or isinstance(result, dict):
                return result
            
            # 其他情况直接返回
            return result
            
        except BaseAPIException as e:
            # 自定义API异常，转换为JSON响应
            logger.warning(f"API异常: {e.error_code} - {e.message}")
            if e.details:
                logger.debug(f"异常详情: {e.details}")
            return jsonify(e.to_dict()), e.status_code
            
        except Exception as e:
            # 未预期的异常，记录日志并返回通用错误
            logger.error(f"未预期的异常: {str(e)}")
            logger.error(traceback.format_exc())
            
            return jsonify({
                'success': False,
                'error_code': 'INTERNAL_ERROR',
                'message': '服务器内部错误，请稍后重试'
            }), 500
    
    return wrapper


def validate_json_request(required_fields: list = None, optional_fields: list = None):
    """
    验证JSON请求数据的装饰器
    
    使用示例：
        @app.route('/api/example', methods=['POST'])
        @handle_api_error
        @validate_json_request(required_fields=['name', 'email'])
        def api_example():
            data = request.json  # 已经验证过
            return jsonify({'success': True})
    
    Args:
        required_fields: 必需字段列表
        optional_fields: 可选字段列表（用于类型验证）
    
    Returns:
        装饰器函数
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            from utils.exceptions import ValidationError
            
            # 检查Content-Type
            if not request.is_json:
                raise ValidationError("请求必须是JSON格式")
            
            # 检查JSON数据
            data = request.get_json()
            if data is None:
                raise ValidationError("请求数据不能为空")
            
            # 验证必需字段
            if required_fields:
                missing_fields = [field for field in required_fields if field not in data]
                if missing_fields:
                    raise ValidationError(
                        f"缺少必需字段: {', '.join(missing_fields)}",
                        field=missing_fields[0]
                    )
            
            # 执行原函数
            return func(*args, **kwargs)
        
        return wrapper
    return decorator


def success_response(data: Any = None, message: str = "操作成功") -> tuple:
    """
    创建成功响应的工具函数
    
    Args:
        data: 响应数据
        message: 成功消息
    
    Returns:
        Flask响应元组 (jsonify对象, 状态码)
    """
    response = {
        'success': True,
        'message': message
    }
    if data is not None:
        response['data'] = data
    return jsonify(response), 200


def error_response(message: str, error_code: str = "ERROR", 
                   status_code: int = 400, details: dict = None) -> tuple:
    """
    创建错误响应的工具函数
    
    Args:
        message: 错误消息
        error_code: 错误代码
        status_code: HTTP状态码
        details: 错误详情
    
    Returns:
        Flask响应元组 (jsonify对象, 状态码)
    """
    response = {
        'success': False,
        'error_code': error_code,
        'message': message
    }
    if details:
        response['details'] = details
    return jsonify(response), status_code


def log_and_handle_error(func: Callable, error: Exception, 
                        context: str = None) -> tuple:
    """
    记录错误并返回统一错误响应的工具函数
    
    用于非装饰器场景的错误处理。
    
    Args:
        func: 出错的函数
        error: 异常对象
        context: 上下文信息（可选）
    
    Returns:
        Flask响应元组 (jsonify对象, 状态码)
    """
    func_name = func.__name__ if func else "unknown"
    context_str = f" [{context}]" if context else ""
    
    if isinstance(error, BaseAPIException):
        logger.warning(f"{func_name}{context_str}: {error.error_code} - {error.message}")
        return jsonify(error.to_dict()), error.status_code
    else:
        logger.error(f"{func_name}{context_str}: 未预期的异常 - {str(error)}")
        logger.error(traceback.format_exc())
        return jsonify({
            'success': False,
            'error_code': 'INTERNAL_ERROR',
            'message': '服务器内部错误，请稍后重试'
        }), 500
