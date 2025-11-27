"""
API 拦截模块
使用 Chrome DevTools Protocol (CDP) 拦截和统计网络请求
"""
import json
import time
import threading
from typing import Dict, Optional
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from .error_summarizer import ErrorSummarizer
from .response_validator import ResponseValidator, ErrorType


class APIInterceptor:
    """API 拦截器"""
    
    def __init__(self, driver: webdriver.Chrome, headers: Dict[str, str], 
                 error_summarizer: ErrorSummarizer):
        """
        初始化 API 拦截器
        
        Args:
            driver: Selenium WebDriver 实例
            headers: 需要注入的 HTTP Headers
            error_summarizer: 错误汇总器实例
        """
        self.driver = driver
        self.headers = headers
        self.error_summarizer = error_summarizer
        self.validator = ResponseValidator()
        self.response_data: Dict[str, Dict] = {}  # 存储响应数据，key 为 requestId
        self.processed_request_ids = set()  # 已处理的请求 ID
        self.monitoring = False
        self.monitor_thread = None
    
    def start_intercepting(self):
        """开始拦截网络请求"""
        try:
            # 启用 Network 域
            self.driver.execute_cdp_cmd('Network.enable', {})
            print("Network 域已启用")
            
            # 设置额外的 HTTP Headers
            if self.headers:
                self.driver.execute_cdp_cmd('Network.setExtraHTTPHeaders', {
                    'headers': self.headers
                })
                print(f"已注入 Headers: {self.headers}")
            
            # 通过 CDP 设置网络相关选项，帮助解决 CORS 问题
            try:
                # 设置网络条件，允许跨域请求
                self.driver.execute_cdp_cmd('Network.setBypassServiceWorker', {'bypass': True})
            except Exception:
                # 如果 CDP 命令不支持，忽略错误
                pass
            
        except Exception as e:
            print(f"启动拦截器时出错: {e}")
    
    def process_logs(self):
        """处理浏览器性能日志，提取网络请求信息"""
        try:
            logs = self.driver.get_log('performance')
            processed_count = 0
            for log_entry in logs:
                try:
                    message = json.loads(log_entry['message'])
                    message_method = message.get('message', {}).get('method', '')
                    message_params = message.get('message', {}).get('params', {})
                    
                    if message_method == 'Network.responseReceived':
                        self._handle_response_received(message_params)
                        processed_count += 1
                    elif message_method == 'Network.loadingFinished':
                        self._handle_loading_finished(message_params)
                        processed_count += 1
                except (json.JSONDecodeError, KeyError) as e:
                    continue
        except Exception as e:
            # 如果日志不可用，可能是性能日志未启用或浏览器版本不支持
            # 首次错误时输出提示
            if not hasattr(self, '_log_error_shown'):
                print(f"警告: 无法获取性能日志: {e}")
                self._log_error_shown = True
            pass
    
    def _handle_response_received(self, params: Dict):
        """处理响应接收事件"""
        try:
            response = params.get('response', {})
            request = params.get('request', {})
            request_id = params.get('requestId', '')
            url = response.get('url', '')
            status = response.get('status', 0)
            
            # 存储响应和请求信息
            if request_id and url:
                self.response_data[request_id] = {
                    'url': url,
                    'status': status,
                    'headers': response.get('headers', {}),
                    'mimeType': response.get('mimeType', ''),
                    'request_method': request.get('method', ''),
                    'request_headers': request.get('headers', {}),
                    'request_post_data': request.get('postData', '')
                }
        except Exception as e:
            print(f"处理响应接收事件时出错: {e}")
    
    def _handle_loading_finished(self, params: Dict):
        """处理加载完成事件"""
        try:
            request_id = params.get('requestId', '')
            if not request_id or request_id in self.processed_request_ids:
                return
            
            if request_id in self.response_data:
                response_info = self.response_data[request_id]
                url = response_info['url']
                status_code = response_info['status']
                mime_type = response_info.get('mimeType', '')
                request_method = response_info.get('request_method', '')
                request_headers = response_info.get('request_headers', {})
                request_body = response_info.get('request_post_data', '')
                response_headers = response_info.get('headers', {})
                
                # 获取响应体
                body_text = ""
                try:
                    response_body = self.driver.execute_cdp_cmd('Network.getResponseBody', {
                        'requestId': request_id
                    })
                    body_text = response_body.get('body', '')
                    
                    # 如果是 base64 编码，需要解码
                    if response_body.get('base64Encoded', False):
                        import base64
                        body_text = base64.b64decode(body_text).decode('utf-8', errors='ignore')
                except Exception as e:
                    # 某些响应可能无法获取（如跨域、已关闭的连接等）
                    body_text = ""
                
                # 验证响应（新的方法会判断是否为 API 请求）
                is_success, error_type, error_message, is_api = self.validator.validate_response(
                    status_code, body_text, url, mime_type
                )
                
                # 如果不是 API 请求，跳过记录
                if not is_api:
                    # 标记为已处理但不记录错误
                    self.processed_request_ids.add(request_id)
                    if request_id in self.response_data:
                        del self.response_data[request_id]
                    return
                
                # 如果是 API 请求但验证失败，记录错误（包含详细信息）
                if not is_success:
                    self.error_summarizer.add_error(
                        url, error_type, error_message, status_code, body_text,
                        request_method, request_headers, request_body, response_headers
                    )
                    print(f"发现错误: {url} - {error_type.value} - {error_message}")
                
                # 标记为已处理
                self.processed_request_ids.add(request_id)
                
                # 清理已处理的响应数据
                if request_id in self.response_data:
                    del self.response_data[request_id]
        except Exception as e:
            print(f"处理加载完成事件时出错: {e}")
    
    def start_monitoring(self):
        """开始持续监控请求"""
        if self.monitoring:
            return
        
        self.monitoring = True
        print("开始监控网络请求...")
        print("按 Ctrl+C 停止监控")
        
        def monitor_loop():
            while self.monitoring:
                try:
                    self.process_logs()
                    time.sleep(0.5)  # 每 0.5 秒检查一次
                except Exception as e:
                    if self.monitoring:
                        print(f"监控过程中出错: {e}")
        
        self.monitor_thread = threading.Thread(target=monitor_loop, daemon=True)
        self.monitor_thread.start()
    
    def stop_monitoring(self):
        """停止监控"""
        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=2)
        print("监控已停止")

