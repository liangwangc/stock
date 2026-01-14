"""
统一异常处理模块

提供统一的异常类和错误处理机制，提高代码质量和可维护性。
"""
from typing import Optional, Dict, Any


class BaseAPIException(Exception):
    """API异常基类"""
    
    def __init__(self, message: str, status_code: int = 500, error_code: str = None, 
                 details: Dict[str, Any] = None):
        """
        初始化异常
        
        Args:
            message: 错误消息
            status_code: HTTP状态码
            error_code: 错误代码（用于前端识别错误类型）
            details: 错误详情（可选）
        """
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.error_code = error_code or self.__class__.__name__
        self.details = details or {}
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式（用于JSON响应）"""
        return {
            'success': False,
            'error_code': self.error_code,
            'message': self.message,
            'details': self.details
        }


class ValidationError(BaseAPIException):
    """输入验证错误"""
    
    def __init__(self, message: str, field: str = None, details: Dict[str, Any] = None):
        """
        初始化验证错误
        
        Args:
            message: 错误消息
            field: 验证失败的字段名
            details: 错误详情
        """
        if field:
            details = details or {}
            details['field'] = field
        super().__init__(message, status_code=400, error_code='VALIDATION_ERROR', details=details)


class AuthenticationError(BaseAPIException):
    """认证错误（未登录）"""
    
    def __init__(self, message: str = "请先登录", details: Dict[str, Any] = None):
        super().__init__(message, status_code=401, error_code='AUTHENTICATION_ERROR', details=details)


class AuthorizationError(BaseAPIException):
    """授权错误（权限不足）"""
    
    def __init__(self, message: str = "权限不足", details: Dict[str, Any] = None):
        super().__init__(message, status_code=403, error_code='AUTHORIZATION_ERROR', details=details)


class NotFoundError(BaseAPIException):
    """资源未找到错误"""
    
    def __init__(self, message: str = "资源未找到", resource_type: str = None, 
                 resource_id: str = None, details: Dict[str, Any] = None):
        if resource_type or resource_id:
            details = details or {}
            if resource_type:
                details['resource_type'] = resource_type
            if resource_id:
                details['resource_id'] = resource_id
        super().__init__(message, status_code=404, error_code='NOT_FOUND', details=details)


class DatabaseError(BaseAPIException):
    """数据库操作错误"""
    
    def __init__(self, message: str = "数据库操作失败", details: Dict[str, Any] = None):
        super().__init__(message, status_code=500, error_code='DATABASE_ERROR', details=details)


class ExternalAPIError(BaseAPIException):
    """外部API调用错误"""
    
    def __init__(self, message: str = "外部API调用失败", api_name: str = None, 
                 details: Dict[str, Any] = None):
        if api_name:
            details = details or {}
            details['api_name'] = api_name
        super().__init__(message, status_code=502, error_code='EXTERNAL_API_ERROR', details=details)


class BusinessLogicError(BaseAPIException):
    """业务逻辑错误"""
    
    def __init__(self, message: str, status_code: int = 400, details: Dict[str, Any] = None):
        super().__init__(message, status_code=status_code, error_code='BUSINESS_LOGIC_ERROR', details=details)


class ConfigurationError(BaseAPIException):
    """配置错误"""
    
    def __init__(self, message: str = "配置错误", config_key: str = None, 
                 details: Dict[str, Any] = None):
        if config_key:
            details = details or {}
            details['config_key'] = config_key
        super().__init__(message, status_code=500, error_code='CONFIGURATION_ERROR', details=details)
