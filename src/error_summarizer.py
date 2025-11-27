"""
错误汇总模块
用于收集和汇总 API 错误信息，按 URI 去重
"""
from typing import Dict, List, Optional
from datetime import datetime
from .response_validator import ErrorType


class ErrorDetail:
    """错误详情类，记录单次错误的详细信息"""
    
    def __init__(self, error_message: str, status_code: Optional[int] = None,
                 request_method: Optional[str] = None, request_headers: Optional[Dict] = None,
                 request_body: Optional[str] = None, response_headers: Optional[Dict] = None,
                 response_body: Optional[str] = None, timestamp: Optional[datetime] = None):
        """
        初始化错误详情
        
        Args:
            error_message: 错误消息
            status_code: HTTP 状态码
            request_method: 请求方法
            request_headers: 请求头
            request_body: 请求体
            response_headers: 响应头
            response_body: 响应体
            timestamp: 时间戳
        """
        self.error_message = error_message
        self.status_code = status_code
        self.request_method = request_method
        self.request_headers = request_headers or {}
        self.request_body = request_body
        self.response_headers = response_headers or {}
        self.response_body = response_body
        self.timestamp = timestamp or datetime.now()


class ErrorRecord:
    """错误记录类"""
    
    def __init__(self, uri: str, error_type: ErrorType, error_message: str, 
                 status_code: Optional[int] = None, response_body: Optional[str] = None,
                 request_method: Optional[str] = None, request_headers: Optional[Dict] = None,
                 request_body: Optional[str] = None, response_headers: Optional[Dict] = None):
        """
        初始化错误记录
        
        Args:
            uri: API URI
            error_type: 错误类型
            error_message: 错误消息
            status_code: HTTP 状态码
            response_body: 响应体内容（可选，用于详细记录）
            request_method: 请求方法
            request_headers: 请求头
            request_body: 请求体
            response_headers: 响应头
        """
        self.uri = uri
        self.error_type = error_type
        self.error_message = error_message
        self.status_code = status_code
        self.response_body = response_body
        self.count = 1  # 同一 URI 的错误次数
        # 存储每次错误的详细信息
        self.details: List[ErrorDetail] = []
        
        # 添加第一次错误的详细信息
        self.details.append(ErrorDetail(
            error_message=error_message,
            status_code=status_code,
            request_method=request_method,
            request_headers=request_headers,
            request_body=request_body,
            response_headers=response_headers,
            response_body=response_body
        ))
    
    def add_detail(self, error_message: str, status_code: Optional[int] = None,
                   request_method: Optional[str] = None, request_headers: Optional[Dict] = None,
                   request_body: Optional[str] = None, response_headers: Optional[Dict] = None,
                   response_body: Optional[str] = None):
        """
        添加错误详情
        
        Args:
            error_message: 错误消息
            status_code: HTTP 状态码
            request_method: 请求方法
            request_headers: 请求头
            request_body: 请求体
            response_headers: 响应头
            response_body: 响应体
        """
        self.count += 1
        self.details.append(ErrorDetail(
            error_message=error_message,
            status_code=status_code,
            request_method=request_method,
            request_headers=request_headers,
            request_body=request_body,
            response_headers=response_headers,
            response_body=response_body
        ))
        # 如果错误消息不同，更新汇总消息
        if error_message != self.error_message:
            self.error_message += f" | {error_message}"
    
    def merge(self, other: 'ErrorRecord'):
        """
        合并相同 URI 的错误记录（已废弃，使用 add_detail 代替）
        
        Args:
            other: 另一个错误记录
        """
        self.count += 1
        # 如果错误消息不同，合并显示
        if self.error_message != other.error_message:
            self.error_message += f" | {other.error_message}"


class ErrorSummarizer:
    """错误汇总器"""
    
    def __init__(self, output_file: str = None):
        """
        初始化错误汇总器
        
        Args:
            output_file: 输出文件路径（可选，仅在生成报告时使用）
        """
        self.errors: Dict[str, ErrorRecord] = {}  # 使用 URI 作为键进行去重
        self.output_file = output_file
        self.start_time = datetime.now()
    
    def add_error(self, uri: str, error_type: ErrorType, error_message: str,
                  status_code: Optional[int] = None, response_body: Optional[str] = None,
                  request_method: Optional[str] = None, request_headers: Optional[Dict] = None,
                  request_body: Optional[str] = None, response_headers: Optional[Dict] = None):
        """
        添加错误记录
        
        Args:
            uri: API URI
            error_type: 错误类型
            error_message: 错误消息
            status_code: HTTP 状态码
            response_body: 响应体内容
            request_method: 请求方法
            request_headers: 请求头
            request_body: 请求体
            response_headers: 响应头
        """
        # 提取 URI 路径部分（去除查询参数和域名）
        clean_uri = self._extract_uri_path(uri)
        
        if clean_uri in self.errors:
            # 如果已存在相同 URI 的错误，添加详情
            existing_record = self.errors[clean_uri]
            existing_record.add_detail(
                error_message=error_message,
                status_code=status_code,
                request_method=request_method,
                request_headers=request_headers,
                request_body=request_body,
                response_headers=response_headers,
                response_body=response_body
            )
        else:
            # 创建新记录
            self.errors[clean_uri] = ErrorRecord(
                clean_uri, error_type, error_message, status_code, response_body,
                request_method, request_headers, request_body, response_headers
            )
    
    def _extract_uri_path(self, url: str) -> str:
        """
        从完整 URL 中提取 URI 路径
        
        Args:
            url: 完整 URL
        
        Returns:
            URI 路径
        """
        try:
            from urllib.parse import urlparse
            parsed = urlparse(url)
            return parsed.path
        except Exception:
            # 如果解析失败，返回原始 URL
            return url
    
    def get_summary(self) -> List[ErrorRecord]:
        """
        获取错误汇总列表
        
        Returns:
            错误记录列表
        """
        return list(self.errors.values())
    
    def _generate_report_content(self) -> str:
        """
        生成报告内容
        
        Returns:
            报告内容字符串
        """
        current_time = datetime.now()
        runtime = current_time - self.start_time
        
        if not self.errors:
            report_content = "API 错误汇总报告\n"
            report_content += f"启动时间: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}\n"
            report_content += f"当前时间: {current_time.strftime('%Y-%m-%d %H:%M:%S')}\n"
            report_content += f"运行时长: {self._format_runtime(runtime)}\n\n"
            report_content += "未发现任何错误。\n"
        else:
            report_content = "API 错误汇总报告\n"
            report_content += f"启动时间: {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}\n"
            report_content += f"当前时间: {current_time.strftime('%Y-%m-%d %H:%M:%S')}\n"
            report_content += f"运行时长: {self._format_runtime(runtime)}\n\n"
            report_content += f"共发现 {len(self.errors)} 个不同的 API 错误：\n\n"
            
            for uri, record in sorted(self.errors.items()):
                report_content += "=" * 50 + "\n"
                report_content += f"URI: {record.uri}\n"
                report_content += f"错误类型: {record.error_type.value}\n"
                report_content += f"错误内容: {record.error_message}\n"
                if record.status_code:
                    report_content += f"状态码: {record.status_code}\n"
                if record.count > 1:
                    report_content += f"错误次数: {record.count}\n"
                report_content += "=" * 50 + "\n\n"
        
        return report_content
    
    def _format_runtime(self, runtime) -> str:
        """
        格式化运行时长
        
        Args:
            runtime: timedelta 对象
        
        Returns:
            格式化的运行时长字符串
        """
        total_seconds = int(runtime.total_seconds())
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        seconds = total_seconds % 60
        
        if hours > 0:
            return f"{hours}小时{minutes}分钟{seconds}秒"
        elif minutes > 0:
            return f"{minutes}分钟{seconds}秒"
        else:
            return f"{seconds}秒"
    
    def generate_report(self, output_file: str = None):
        """
        生成错误汇总报告文件
        
        Args:
            output_file: 输出文件路径（如果为 None，使用 self.output_file）
        """
        target_file = output_file or self.output_file or "api_error_summary.txt"
        
        try:
            report_content = self._generate_report_content()
            with open(target_file, 'w', encoding='utf-8') as f:
                f.write(report_content)
            print(f"错误汇总报告已生成: {target_file}")
        except Exception as e:
            print(f"生成报告文件时出错: {e}")
    
    def clear(self):
        """清空所有错误记录"""
        self.errors.clear()

