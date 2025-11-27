# Selenium API 拦截统计项目

## 项目简介

这是一个基于 Python Selenium 和 Chrome DevTools Protocol (CDP) 的项目，用于拦截和统计浏览器中的所有 API 请求，检查响应状态，并将错误信息汇总到文本文件中。

## 功能特性

- ✅ 使用 Chrome DevTools Protocol (CDP) 拦截所有网络请求
- ✅ 自动注入配置的 HTTP Headers 到请求中
- ✅ 验证 HTTP 状态码（非 2xx 视为错误）
- ✅ 验证 JSON 响应中的 `code` 字段（`code=SUCCESS` 表示成功）
- ✅ 按 API URI 去重汇总错误信息
- ✅ 生成详细的错误汇总报告文件

## 项目结构

```
check-pad-web/
├── requirements.txt              # Python 依赖包
├── config.properties            # Header 配置（键值对）
├── main.py                      # 主程序入口
├── src/                         # 源代码目录
│   ├── __init__.py              # Python 包初始化文件
│   ├── config_loader.py         # 配置加载模块
│   ├── api_interceptor.py       # API 拦截和统计核心模块
│   ├── response_validator.py   # 响应验证模块
│   ├── error_summarizer.py     # 错误汇总模块
│   ├── web_server.py           # Web 服务器模块
│   ├── templates/              # HTML 模板目录
│   │   └── index.html          # 统计结果展示页面
│   └── static/                 # 静态文件目录
├── summary/                     # 统计结果目录（自动创建）
│   └── yyyyMMddHHmmss.txt       # 带时间戳的统计文件
└── README.md                    # 项目说明文档
```

## 安装依赖

1. 确保已安装 Python 3.7 或更高版本
2. 安装项目依赖：

```bash
pip install -r requirements.txt
```

3. 确保已安装 Chrome 浏览器
4. ChromeDriver 会自动管理（通过 webdriver-manager），或手动下载并配置到 PATH

## 配置说明

### 1. Header 配置 (`config.properties`)

编辑 `config.properties` 文件，添加需要注入到请求中的 HTTP Headers：

```properties
# API Request Headers
# 格式: key=value
Authorization=Bearer your-token-here
Content-Type=application/json
X-Custom-Header=custom-value
```

### 2. 用户数据目录（可选）

如果需要在已存在的浏览器会话中监控，可以指定 Chrome 用户数据目录：

```bash
python main.py --user-data-dir /path/to/chrome/user/data
```

## 使用方法

### 基本使用

1. 启动监控（不指定 URL，手动在浏览器中操作）：

```bash
python main.py
```

2. 启动监控并自动访问指定 URL：

```bash
python main.py --url https://example.com
```

3. 使用自定义配置文件：

```bash
python main.py --config my-config.properties
```

4. 使用用户数据目录：

```bash
python main.py --user-data-dir ~/Library/Application\ Support/Google/Chrome
```

5. 自定义 Web 服务器端口：

```bash
python main.py --web-port 8080
```

6. 禁用 Web 服务：

```bash
python main.py --no-web
```

### 完整示例

```bash
# 访问指定网站并开始监控
python main.py --url https://your-api-site.com --user-data-dir ~/.chrome-profile

# 在浏览器中进行操作，程序会自动拦截和统计 API 请求
# 访问 http://127.0.0.1:5000 查看实时统计结果
# 按 Ctrl+C 停止监控并生成报告
```

## Web 统计界面

程序启动后会自动启动一个 Web 服务器（默认端口 5000），提供实时统计结果展示界面。

**注意**：统计结果不再实时写入文件，所有数据通过 Web 界面查看。程序退出时会自动生成最终报告文件保存到 `summary` 目录。

### 功能特性

- 📊 **实时统计展示**：以表格形式展示所有 API 错误
- 🔄 **自动刷新**：支持自动刷新（每 5 秒）或手动刷新
- 📈 **统计摘要**：显示错误 API 总数、错误请求次数等信息
- 🎨 **美观界面**：现代化的 UI 设计，易于查看和理解

### 访问方式

启动程序后，在浏览器中访问：

```
http://127.0.0.1:5000
```

### 界面说明

- **统计摘要栏**：显示错误 API 总数、错误请求次数和统计文件名
- **刷新按钮**：手动刷新统计数据
- **自动刷新开关**：开启后每 5 秒自动刷新一次
- **错误表格**：展示所有错误的详细信息，包括：
  - URI：API 路径
  - 错误类型：状态码错误/返回值错误/格式错误
  - 错误内容：详细的错误信息
  - 状态码：HTTP 状态码（如果有）
  - 错误次数：同一 URI 的错误次数

## 输出说明

### 错误汇总报告 (`summary/yyyyMMddHHmmss.txt`)

程序退出时会在 `summary` 目录下自动生成带时间戳的统计文件。文件格式为 `yyyyMMddHHmmss.txt`（年月日时分秒）。

**注意**：运行过程中统计结果通过 Web 界面实时查看，不再实时写入文件。只有在程序退出时才会生成最终报告文件。

报告包含以下信息：

- 报告生成时间
- 错误 API 总数
- 每个错误的详细信息：
  - URI 路径
  - 错误类型（状态码错误/返回值错误/格式错误）
  - 错误内容
  - HTTP 状态码（如果有）
  - 错误次数（如果同一 URI 出现多次错误）

报告示例：

```
API 错误汇总报告
启动时间: 2024-01-01 12:00:00
当前时间: 2024-01-01 12:05:30
运行时长: 5分钟30秒

共发现 2 个不同的 API 错误：

==================================================
URI: /api/user/info
错误类型: 返回值错误
错误内容: code=FAILED, message=用户不存在
状态码: 200
错误次数: 1
==================================================

==================================================
URI: /api/order/list
错误类型: 状态码错误
错误内容: HTTP 500 - Internal Server Error
状态码: 500
错误次数: 3
==================================================
```

## 响应验证规则

1. **HTTP 状态码验证**：
   - 200-299：状态码正常
   - 其他：视为状态码错误

2. **JSON 响应验证**：
   - 响应必须是有效的 JSON 格式
   - JSON 对象的一级属性中必须包含 `code` 字段
   - `code` 字段的值必须等于 `"SUCCESS"` 或 `"00000"`（字符串）才视为成功
   - 如果 `code` 不等于 `"SUCCESS"` 或 `"00000"`，或不存在，视为返回值错误

## 注意事项

1. **Chrome 浏览器要求**：需要 Chrome 浏览器支持 CDP（Chrome 59+）
2. **用户数据目录**：如果指定了用户数据目录，确保该目录存在且可访问
3. **错误去重**：同一 URI 的多次错误会被合并，显示错误次数
4. **响应体限制**：为了性能考虑，响应体内容可能被截断
5. **静态资源过滤**：默认会过滤掉常见的静态资源请求（.js, .css, .png 等），只监控 API 请求
6. **CORS 跨域问题**：程序已自动配置 Chrome 选项以解决 CORS 跨域问题，包括禁用 Web 安全策略和允许跨域资源共享

## 故障排除

### 问题：无法启动浏览器

- 确保已安装 Chrome 浏览器
- 检查 ChromeDriver 版本是否与 Chrome 版本匹配
- 尝试更新 selenium 和 webdriver-manager

### 问题：无法拦截请求

- 确保 Chrome 版本支持 CDP（Chrome 59+）
- 检查是否有防火墙或安全软件阻止
- 尝试使用无头模式（在代码中取消注释 `options.add_argument('--headless')`）

### 问题：配置文件读取失败

- 确保 `config.properties` 文件存在
- 检查文件格式是否正确（key=value 格式）
- 确保文件编码为 UTF-8

### 问题：CORS 跨域错误

如果遇到类似以下错误：
```
Access to script at 'xxx' from origin 'xxx' has been blocked by CORS policy
```

程序已自动配置了以下 Chrome 选项来解决 CORS 问题：
- `--disable-web-security`：禁用 Web 安全策略
- `--disable-site-isolation-trials`：禁用站点隔离
- `--allow-running-insecure-content`：允许运行不安全内容
- `--disable-features=BlockInsecurePrivateNetworkRequests`：禁用不安全的私有网络请求阻止

如果问题仍然存在：
- 确保没有其他 Chrome 实例正在运行
- 尝试不使用用户数据目录（让程序使用临时目录）
- 检查目标网站是否有特殊的 CORS 策略要求

## 开发说明

### 模块说明

- **config_loader.py**: 读取和解析 properties 配置文件
- **api_interceptor.py**: 使用 CDP 拦截网络请求，注入 headers
- **response_validator.py**: 验证 HTTP 状态码和 JSON 响应
- **error_summarizer.py**: 收集和汇总错误信息，按 URI 去重
- **main.py**: 主程序，整合所有模块

### 扩展开发

如需扩展功能，可以：

1. 修改 `response_validator.py` 添加自定义验证规则
2. 修改 `error_summarizer.py` 更改报告格式
3. 修改 `api_interceptor.py` 添加更多请求过滤条件

## 许可证

本项目采用 MIT 许可证。

## 贡献

欢迎提交 Issue 和 Pull Request！

