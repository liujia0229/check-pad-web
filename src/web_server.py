"""
Web 服务器模块
提供 Web 界面展示统计结果
"""
import os
import json
from flask import Flask, render_template, jsonify
from typing import Optional
from .error_summarizer import ErrorSummarizer


class WebServer:
    """Web 服务器类"""
    
    def __init__(self, error_summarizer: ErrorSummarizer, host: str = '127.0.0.1', port: int = 5000):
        """
        初始化 Web 服务器
        
        Args:
            error_summarizer: 错误汇总器实例
            host: 服务器主机地址
            port: 服务器端口
        """
        # 获取模板和静态文件目录的绝对路径
        base_dir = os.path.dirname(os.path.abspath(__file__))
        template_dir = os.path.join(base_dir, 'templates')
        static_dir = os.path.join(base_dir, 'static')
        
        self.app = Flask(__name__, template_folder=template_dir, static_folder=static_dir)
        self.error_summarizer = error_summarizer
        self.host = host
        self.port = port
        
        # 注册路由
        self._register_routes()
    
    def _register_routes(self):
        """注册路由"""
        
        @self.app.route('/')
        def index():
            """首页"""
            return render_template('index.html')
        
        @self.app.route('/api/summary')
        def get_summary():
            """获取统计摘要 API"""
            try:
                errors = self.error_summarizer.get_summary()
                
                # 转换为字典格式
                errors_data = []
                for record in errors:
                    errors_data.append({
                        'uri': record.uri,
                        'error_type': record.error_type.value,
                        'error_message': record.error_message,
                        'status_code': record.status_code,
                        'count': record.count
                    })
                
                # 获取统计信息
                total_errors = len(errors)
                total_requests = sum(record.count for record in errors)
                
                # 调试输出
                print(f"API 请求: 返回 {total_errors} 个错误，共 {total_requests} 次错误请求")
                
                return jsonify({
                    'success': True,
                    'data': {
                        'total_errors': total_errors,
                        'total_requests': total_requests,
                        'errors': errors_data,
                        'start_time': self.error_summarizer.start_time.strftime('%Y-%m-%d %H:%M:%S'),
                        'output_file': os.path.basename(self.error_summarizer.output_file) if self.error_summarizer.output_file else None
                    }
                })
            except Exception as e:
                import traceback
                traceback.print_exc()
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500
        
        @self.app.route('/api/error-details/<path:uri>')
        def get_error_details(uri):
            """获取指定 URI 的错误详情 API"""
            try:
                from urllib.parse import unquote
                # 解码 URI（Flask 会自动解码，但为了安全再次处理）
                decoded_uri = unquote(uri)
                
                errors = self.error_summarizer.get_summary()
                
                # 标准化 URI：提取路径部分（去除查询参数和域名）
                normalized_uri = self.error_summarizer._extract_uri_path(decoded_uri)
                
                # 调试输出
                print(f"查找错误详情 - 原始 URI: {decoded_uri}, 标准化 URI: {normalized_uri}")
                print(f"可用 URI 列表: {[r.uri for r in errors]}")
                
                # 查找匹配的错误记录（尝试多种匹配方式）
                for record in errors:
                    # 尝试多种匹配方式：精确匹配、标准化路径匹配、包含匹配
                    if (record.uri == decoded_uri or 
                        record.uri == normalized_uri or
                        (normalized_uri and record.uri.endswith(normalized_uri)) or
                        (record.uri and normalized_uri.endswith(record.uri))):
                        
                        # 转换详情为字典格式
                        details_data = []
                        for detail in record.details:
                            details_data.append({
                                'error_message': detail.error_message,
                                'status_code': detail.status_code,
                                'request_method': detail.request_method,
                                'request_headers': detail.request_headers,
                                'request_body': detail.request_body,
                                'response_headers': detail.response_headers,
                                'response_body': detail.response_body,
                                'timestamp': detail.timestamp.strftime('%Y-%m-%d %H:%M:%S') if detail.timestamp else None
                            })
                        
                        return jsonify({
                            'success': True,
                            'data': {
                                'uri': record.uri,
                                'error_type': record.error_type.value,
                                'count': record.count,
                                'details': details_data
                            }
                        })
                
                # 如果都没匹配到，返回详细错误信息
                available_uris = [r.uri for r in errors]
                return jsonify({
                    'success': False,
                    'error': f'未找到指定的错误记录。查找的 URI: {decoded_uri}，可用 URI: {available_uris}'
                }), 404
            except Exception as e:
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500
    
    def run(self, debug: bool = False):
        """
        启动 Web 服务器
        
        Args:
            debug: 是否启用调试模式
        """
        try:
            print(f"\nWeb 服务正在启动: http://{self.host}:{self.port}")
            print(f"在浏览器中访问 http://{self.host}:{self.port} 查看统计结果\n")
            # 在后台线程中运行 Flask，需要禁用 reloader
            self.app.run(
                host=self.host, 
                port=self.port, 
                debug=False,  # 在后台线程中必须禁用 debug
                use_reloader=False,
                threaded=True  # 启用多线程支持
            )
        except Exception as e:
            print(f"Web 服务器启动失败: {e}")
            import traceback
            traceback.print_exc()

