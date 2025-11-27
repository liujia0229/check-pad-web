"""
配置加载模块
用于读取和解析 config.properties 文件
"""
import configparser
import os
from typing import Dict


class ConfigLoader:
    """配置加载器，用于读取 properties 文件"""
    
    def __init__(self, config_path: str = "config.properties"):
        """
        初始化配置加载器
        
        Args:
            config_path: 配置文件路径
        """
        self.config_path = config_path
        self.config = {}
    
    def load(self) -> Dict[str, str]:
        """
        加载配置文件并返回 header 字典
        
        Returns:
            包含 header 键值对的字典
        """
        if not os.path.exists(self.config_path):
            print(f"警告: 配置文件 {self.config_path} 不存在，使用空配置")
            return {}
        
        headers = {}
        
        # 使用 configparser 读取 properties 文件
        # 注意：configparser 默认使用 INI 格式，需要特殊处理 properties 格式
        config = configparser.ConfigParser()
        config.optionxform = str  # 保持键的大小写
        
        try:
            # 读取文件内容，手动处理 properties 格式
            with open(self.config_path, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    # 跳过空行和注释
                    if not line or line.startswith('#'):
                        continue
                    
                    # 解析键值对
                    if '=' in line:
                        key, value = line.split('=', 1)
                        key = key.strip()
                        value = value.strip()
                        # 跳过空值
                        if key:
                            headers[key] = value
        except Exception as e:
            print(f"读取配置文件时出错: {e}")
            return {}
        
        return headers
    
    def get_headers(self) -> Dict[str, str]:
        """
        获取 header 配置
        
        Returns:
            header 字典
        """
        if not self.config:
            self.config = self.load()
        return self.config.copy()

