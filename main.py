"""
主程序入口
整合所有模块，启动浏览器并开始监控 API 请求
"""
import os
import sys
import argparse
import signal
import threading
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from src.config_loader import ConfigLoader
from src.api_interceptor import APIInterceptor
from src.error_summarizer import ErrorSummarizer
from src.web_server import WebServer


class APIMonitor:
    """API 监控主类"""
    
    def __init__(self, user_data_dir: str = None, config_path: str = "config.properties", 
                 web_port: int = 5000, enable_web: bool = True):
        """
        初始化 API 监控器
        
        Args:
            user_data_dir: Chrome 用户数据目录路径
            config_path: 配置文件路径
            web_port: Web 服务器端口
            enable_web: 是否启用 Web 服务
        """
        self.user_data_dir = user_data_dir
        self.config_path = config_path
        self.driver = None
        self.interceptor = None
        self.web_server = None
        self.web_port = web_port
        self.enable_web = enable_web
        
        # 创建 summary 目录（如果不存在，用于退出时生成报告）
        summary_dir = "summary"
        if not os.path.exists(summary_dir):
            os.makedirs(summary_dir)
        
        # 生成带时间戳的输出文件名（仅在退出时生成报告使用）
        timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
        output_file = os.path.join(summary_dir, f"{timestamp}.txt")
        self.error_summarizer = ErrorSummarizer(output_file=output_file)
        self.output_file = output_file
        
        # 注册信号处理，确保程序退出时生成报告
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """信号处理器，用于优雅退出"""
        print("\n接收到退出信号，正在生成报告...")
        self.cleanup()
        sys.exit(0)
    
    def _create_driver(self) -> webdriver.Chrome:
        """
        创建 Chrome WebDriver 实例
        
        Returns:
            Chrome WebDriver 实例
        """
        options = Options()
        
        # 使用用户数据目录（如果提供）
        if self.user_data_dir:
            if os.path.exists(self.user_data_dir):
                options.add_argument(f'--user-data-dir={self.user_data_dir}')
                print(f"使用用户数据目录: {self.user_data_dir}")
            else:
                print(f"警告: 用户数据目录不存在: {self.user_data_dir}")
        
        # 启用性能日志
        options.set_capability('goog:loggingPrefs', {'performance': 'ALL'})
        
        # 其他有用的选项
        options.add_argument('--enable-logging')
        options.add_argument('--v=1')
        
        # 解决 CORS 跨域问题
        options.add_argument('--disable-web-security')
        options.add_argument('--disable-features=VizDisplayCompositor')
        options.add_argument('--allow-running-insecure-content')
        options.add_argument('--disable-blink-features=AutomationControlled')
        # 允许跨域资源共享
        options.add_argument('--disable-site-isolation-trials')
        # 允许跨域请求
        options.add_argument('--disable-features=BlockInsecurePrivateNetworkRequests')
        
        # 隐藏自动化控制提示
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        
        # 如果没有指定用户数据目录，使用临时目录以确保 CORS 设置生效
        if not self.user_data_dir:
            import tempfile
            temp_user_data = os.path.join(tempfile.gettempdir(), 'chrome_dev_session')
            options.add_argument(f'--user-data-dir={temp_user_data}')
        
        # 如果需要无头模式，取消下面的注释
        # options.add_argument('--headless')
        
        try:
            print("正在检查 ChromeDriver...")
            # 使用 webdriver-manager 自动管理 ChromeDriver
            service = Service(ChromeDriverManager().install())
            print("ChromeDriver 已就绪，正在启动浏览器...")
            
            # 设置超时时间（30秒）
            driver = webdriver.Chrome(service=service, options=options)
            print("浏览器启动成功！")
            
            # 执行 CDP 命令来隐藏自动化特征（必须在页面加载前执行）
            try:
                # 启用 Page 域
                driver.execute_cdp_cmd('Page.enable', {})
                # 添加脚本到新文档
                driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
                    'source': '''
                        Object.defineProperty(navigator, 'webdriver', {
                            get: () => undefined
                        });
                    '''
                })
            except Exception as e:
                # 如果 CDP 命令失败，不影响浏览器启动
                print(f"警告: 无法设置自动化隐藏脚本: {e}")
            
            return driver
        except Exception as e:
            print(f"创建 WebDriver 时出错: {e}")
            print("请确保已安装 Chrome 浏览器")
            print("如果问题持续，请尝试：")
            print("  1. 检查 Chrome 浏览器是否已安装")
            print("  2. 检查网络连接（webdriver-manager 需要下载 ChromeDriver）")
            print("  3. 检查是否有防火墙阻止")
            import traceback
            traceback.print_exc()
            raise
    
    def start(self, url: str = None):
        """
        启动监控
        
        Args:
            url: 要访问的 URL（可选）
        """
        try:
            # 加载配置
            config_loader = ConfigLoader(self.config_path)
            headers = config_loader.get_headers()
            print(f"已加载配置，共 {len(headers)} 个 Headers")
            
            # 创建 WebDriver
            print("正在启动浏览器...")
            self.driver = self._create_driver()
            
            # 创建拦截器
            self.interceptor = APIInterceptor(self.driver, headers, self.error_summarizer)
            self.interceptor.start_intercepting()
            
            # 启动 Web 服务器（如果启用）
            if self.enable_web:
                try:
                    self.web_server = WebServer(self.error_summarizer, port=self.web_port)
                    web_thread = threading.Thread(target=self.web_server.run, daemon=True)
                    web_thread.start()
                    # 等待一下确保服务器启动
                    import time
                    time.sleep(1)
                except Exception as e:
                    print(f"启动 Web 服务器时出错: {e}")
                    import traceback
                    traceback.print_exc()
            
            # 如果提供了 URL，导航到该 URL
            if url:
                print(f"正在访问: {url}")
                self.driver.get(url)
            
            # 开始监控
            self.interceptor.start_monitoring()
            
            # 保持程序运行
            print("\n监控已启动，浏览器窗口已打开")
            print("请在浏览器中进行操作，程序将自动拦截和统计 API 请求")
            if self.enable_web:
                print(f"Web 统计界面: http://127.0.0.1:{self.web_port}")
            print("按 Ctrl+C 停止监控并生成最终报告\n")
            
            # 等待用户操作
            try:
                while True:
                    # 处理日志
                    self.interceptor.process_logs()
                    # 检查浏览器是否还在运行
                    try:
                        _ = self.driver.current_url
                    except Exception:
                        print("浏览器已关闭")
                        break
                    import time
                    time.sleep(1)
            except KeyboardInterrupt:
                print("\n接收到中断信号...")
            
        except Exception as e:
            print(f"启动监控时出错: {e}")
            import traceback
            traceback.print_exc()
        finally:
            self.cleanup()
    
    def cleanup(self):
        """清理资源并生成报告"""
        try:
            # 停止监控
            if self.interceptor:
                self.interceptor.stop_monitoring()
            
            # 生成最终错误汇总报告文件（可选）
            if self.error_summarizer:
                self.error_summarizer.generate_report(self.output_file)
                print(f"\n最终统计结果已保存到: {self.output_file}")
            
            # 关闭浏览器
            if self.driver:
                try:
                    self.driver.quit()
                except Exception:
                    pass
            
            print("清理完成")
        except Exception as e:
            print(f"清理资源时出错: {e}")


def main():
    """主函数"""
    parser = argparse.ArgumentParser(description='API 请求拦截和统计工具')
    parser.add_argument('--url', type=str, help='要访问的 URL（可选）')
    parser.add_argument('--user-data-dir', type=str, help='Chrome 用户数据目录路径')
    parser.add_argument('--config', type=str, default='config.properties', 
                       help='配置文件路径（默认: config.properties）')
    parser.add_argument('--web-port', type=int, default=5000,
                       help='Web 服务器端口（默认: 5000）')
    parser.add_argument('--no-web', action='store_true',
                       help='禁用 Web 服务')
    
    args = parser.parse_args()
    
    # 创建监控器并启动
    monitor = APIMonitor(
        user_data_dir=args.user_data_dir, 
        config_path=args.config,
        web_port=args.web_port,
        enable_web=not args.no_web
    )
    monitor.start(url=args.url)


if __name__ == '__main__':
    main()

