**智能数据流看板（AI Trending Dashboard）项目说明文档**

**项目概述**：
这是一个完全由 Python 驱动的、高度可扩展的全自动信息流抓取、AI 异步提炼与纯静态网页构建系统。该项目的核心设计初衷在于严格控制大模型（LLM）的 Token 接口调用成本，彻底规避前端跨域（CORS）与外部样式依赖引发的安全风控，同时具备极低成本的多数据源一键扩展能力。

**系统架构与设计理念**：
项目整体基于“数据驱动与变量硬编码注入”的自包含架构，底层运作完全解耦为爬虫信息搜集模块、AI 智能降本与去重存储缓冲池，以及前端渲染与免环境依赖生成层。系统在运行期间，会通过本地增量查重机制自动拦截历史库中已有的重复数据，达到 100% 免除冗余 Token 消耗的目的。同时，强行约束大模型直接输出无污染的 HTML 结构片段，最终直接在项目目录下写出一个整合了原生免外部依赖 CSS 库与原生折叠交互逻辑的纯静态 index.html 页面。

**目录结构说明**：
- AI_Dashboard/ ：项目根目录。
- main.py ：主程序总控调度入口，负责管理全局读写、顺次启动抓取模块并最终触发网页渲染。
- crawlers/ ：爬虫模块文件夹，用于存放各类数据源抓取脚本，内部包含 __init__.py 标识包。
- crawlers/github_trending.py ：GitHub 看板抓取专用逻辑，包含页面解析、README 深度抓取及大模型清洗。
- render/ ：渲染模块文件夹，用于存放网页生成脚本，内部包含 __init__.py 标识包。
- render/build_html.py ：静态网页核心渲染逻辑，负责将各模块的数据拼接注入到 HTML 模板中。
- database/ ：数据库文件夹，程序运行时会自动在此生成 dashboard_data.json 用于持久化历史缓存。

**隐私安全与环境变量**：
为了确保隐私安全，代码中不包含任何明文的 API 密钥。系统采用安全的环境变量隔离方案，通过 python-dotenv 库在运行时动态加载根目录下的 .env 配置文件。所有敏感凭证（如 DEEPSEEK_API_KEY）和运行产生的本地数据库（dashboard_data.json）均已通过 .gitignore 文件进行严格排除，坚决防止隐私泄露至公共代码仓库。

**部署与多站共存**：
与传统的动态 Web 项目不同，常规生产运行过程不依赖 Flask 或 FastAPI 等常驻型后端服务框架，而是依靠操作系统级的 Crontab 周期定时机制来执行 main.py 脚本。得益于这种全静态自包含的输出模式，在任何已运行其他业务逻辑的主生产服务器上，操作者仅需配置 Nginx 将某一个独立端口（如 8080）或特定子路径直接指向本系统自动产出的静态网页目录，即可实现绝对无缝、完全无干扰的多项目平滑共存与独立页面分发。

**当前生产环境**：
- 服务器：AWS Lightsail (Debian 11, Singapore)
- 部署路径：`/var/www/ai_dashboard/`
- Nginx 端口：8080（与原网站 80/443 完全隔离）
- 虚拟环境：`.venv/`（python-dotenv + httpx + beautifulsoup4）
- 定时任务：Crontab 每日凌晨 3:00 自动执行 `main.py`
- 日志输出：`/var/log/ai_dashboard_cron.log`

**快速部署命令**：
```bash
# 1. 克隆仓库
cd /var/www && git clone https://github.com/hcy9546843522/Daily-information-feed.git ai_dashboard

# 2. 创建 .env（需手动写入密钥）
echo 'DEEPSEEK_API_KEY=sk-xxxx' > /var/www/ai_dashboard/.env

# 3. 创建虚拟环境并安装依赖
cd /var/www/ai_dashboard
python3 -m venv .venv
.venv/bin/pip install httpx beautifulsoup4 python-dotenv

# 4. 配置 Crontab
# 0 3 * * * cd /var/www/ai_dashboard && /var/www/ai_dashboard/.venv/bin/python main.py >> /var/log/ai_dashboard_cron.log 2>&1

# 5. Nginx 配置（8080 端口）
# server {
#     listen 8080;
#     root /var/www/ai_dashboard;
#     index index.html;
#     location / { try_files $uri $uri/ =404; }
# }
```
