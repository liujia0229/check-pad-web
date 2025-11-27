"""
响应验证模块
用于验证 API 响应的状态码和返回值
"""
import json
import re
from typing import Dict, Optional, Tuple
from enum import Enum


class ErrorType(Enum):
    """错误类型枚举"""
    STATUS_CODE_ERROR = "状态码错误"
    RESPONSE_CODE_ERROR = "返回值错误"
    FORMAT_ERROR = "格式错误"


class ResponseValidator:
    """响应验证器"""
    
    # 静态资源文件扩展名
    STATIC_FILE_EXTENSIONS = {'.js', '.css', '.png', '.jpg', '.jpeg', '.gif', '.ico', '.svg', 
                              '.woff', '.woff2', '.ttf', '.eot', '.pdf', '.zip', '.mp4', '.mp3',
                              '.webp', '.avif', '.jpg', '.jpeg'}
    
    # 非 API 请求的 URL 模式
    NON_API_PATTERNS = [
        r'\.(js|css|png|jpg|jpeg|gif|ico|svg|woff|woff2|ttf|eot|pdf|zip|mp4|mp3|webp|avif)(\?|$|#)',
        r'data:image/',
        r'data:text/',
        r'chrome-extension://',
        r'moz-extension://',
    ]
    
    @classmethod
    def _is_api_request(cls, url: str, mime_type: str = None) -> bool:
        """
        判断是否为 API 请求
        
        Args:
            url: 请求 URL
            mime_type: MIME 类型（可选）
        
        Returns:
            是否为 API 请求
        """
        # 检查 URL 是否匹配非 API 模式
        for pattern in cls.NON_API_PATTERNS:
            if re.search(pattern, url, re.IGNORECASE):
                return False
        
        # 检查 MIME 类型
        if mime_type:
            mime_lower = mime_type.lower()
            # 如果是 JSON，肯定是 API
            if 'json' in mime_lower:
                return True
            # 如果是静态资源类型，不是 API
            if any(ext in mime_lower for ext in ['text/css', 'text/javascript', 'application/javascript',
                                                  'image/', 'font/', 'video/', 'audio/', 'application/pdf']):
                return False
        
        # 检查 URL 路径是否包含常见的 API 路径标识
        url_lower = url.lower()
        api_indicators = ['/api/', '/rest/', '/graphql', '/rpc/', '/service/', '/v1/', '/v2/', '/v3/']
        if any(indicator in url_lower for indicator in api_indicators):
            return True
        
        # 如果 URL 是根路径或 HTML 页面，不是 API
        if url_lower.endswith('/') or url_lower.endswith('.html') or url_lower.endswith('.htm'):
            return False
        
        # 默认情况下，如果响应体看起来像 JSON，则认为是 API
        # 这个判断会在 validate_response 中进行
        return True
    
    @classmethod
    def _is_json_like(cls, response_body: str) -> bool:
        """
        判断响应体是否看起来像 JSON
        
        Args:
            response_body: 响应体内容
        
        Returns:
            是否像 JSON
        """
        if not response_body:
            return False
        
        stripped = response_body.strip()
        # JSON 通常以 { 或 [ 开头
        return stripped.startswith('{') or stripped.startswith('[')
    
    @staticmethod
    def validate_response(status_code: int, response_body: str, url: str, 
                         mime_type: str = None) -> Tuple[bool, Optional[ErrorType], str, bool]:
        """
        验证 API 响应
        
        Args:
            status_code: HTTP 状态码
            response_body: 响应体内容
            url: 请求 URL
            mime_type: MIME 类型（可选）
        
        Returns:
            (是否成功, 错误类型, 错误消息, 是否为 API 请求)
            如果不是 API 请求，返回 (True, None, "", False) 表示跳过验证
        """
        # 首先判断是否为 API 请求
        is_api = ResponseValidator._is_api_request(url, mime_type)
        
        # 如果不是 API 请求，跳过验证
        if not is_api:
            return True, None, "", False
        
        # 检查状态码
        if not (200 <= status_code < 300):
            error_msg = f"HTTP {status_code}"
            if status_code == 404:
                error_msg += " - Not Found"
            elif status_code == 500:
                error_msg += " - Internal Server Error"
            elif status_code == 401:
                error_msg += " - Unauthorized"
            elif status_code == 403:
                error_msg += " - Forbidden"
            else:
                error_msg += f" - Error"
            return False, ErrorType.STATUS_CODE_ERROR, error_msg, True
        
        # 检查响应体格式和 code 字段
        if not response_body:
            # 对于 API 请求，空响应体可能是错误
            return False, ErrorType.FORMAT_ERROR, "响应体为空", True
        
        # 如果响应体看起来不像 JSON，但 MIME 类型是 JSON，仍然尝试解析
        # 如果响应体看起来不像 JSON 且 MIME 类型也不是 JSON，可能不是 API 响应
        if not ResponseValidator._is_json_like(response_body):
            if mime_type and 'json' not in mime_type.lower():
                # 看起来不像 JSON 且 MIME 类型也不是 JSON，跳过
                return True, None, "", False
        
        try:
            # 尝试解析 JSON，使用更宽松的解析方式
            # 先尝试标准解析
            try:
                response_data = json.loads(response_body)
            except json.JSONDecodeError:
                # 如果标准解析失败，尝试清理可能的 BOM 或前后空白
                cleaned_body = response_body.strip()
                # 移除可能的 BOM
                if cleaned_body.startswith('\ufeff'):
                    cleaned_body = cleaned_body[1:]
                # 再次尝试解析
                response_data = json.loads(cleaned_body)
            
            # 检查是否为字典类型
            if not isinstance(response_data, dict):
                # 如果是数组，也认为是有效的 JSON，但不检查 code 字段
                if isinstance(response_data, list):
                    # 数组响应通常也是有效的 API 响应
                    return True, None, "", True
                return False, ErrorType.FORMAT_ERROR, f"响应不是 JSON 对象格式: {type(response_data).__name__}", True
            
            # 检查一级属性中是否存在 code 字段
            if 'code' not in response_data:
                error_msg = "响应中缺少 code 字段"
                # 尝试提取其他错误信息
                if 'message' in response_data:
                    error_msg += f", message={response_data['message']}"
                elif 'msg' in response_data:
                    error_msg += f", msg={response_data['msg']}"
                elif 'error' in response_data:
                    error_msg += f", error={response_data['error']}"
                return False, ErrorType.RESPONSE_CODE_ERROR, error_msg, True
            
            # 检查 code 是否为成功状态（SUCCESS 或 00000）
            code_value = response_data.get('code')
            # 支持两种成功状态：SUCCESS 和 00000
            success_codes = ["SUCCESS", "00000"]
            if code_value not in success_codes:
                error_msg = f"code={code_value}"
                # 提取错误消息
                if 'message' in response_data:
                    error_msg += f", message={response_data['message']}"
                elif 'msg' in response_data:
                    error_msg += f", msg={response_data['msg']}"
                elif 'error' in response_data:
                    error_msg += f", error={response_data['error']}"
                return False, ErrorType.RESPONSE_CODE_ERROR, error_msg, True
            
            # 验证通过
            return True, None, "", True
            
        except json.JSONDecodeError as e:
            # 提供更详细的 JSON 解析错误信息
            error_detail = str(e)
            if "Expecting value" in error_detail:
                # 可能是空响应或非 JSON 内容
                if not response_body.strip():
                    return False, ErrorType.FORMAT_ERROR, "响应体为空或只包含空白字符", True
                # 检查是否可能是 HTML
                if response_body.strip().startswith('<'):
                    return True, None, "", False  # 可能是 HTML 页面，跳过
                return False, ErrorType.FORMAT_ERROR, f"JSON 解析失败: 响应不是有效的 JSON 格式", True
            else:
                return False, ErrorType.FORMAT_ERROR, f"JSON 解析失败: {error_detail}", True
        except Exception as e:
            return False, ErrorType.FORMAT_ERROR, f"验证过程出错: {str(e)}", True

