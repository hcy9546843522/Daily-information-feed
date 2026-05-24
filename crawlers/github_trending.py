import os
import re
from datetime import datetime, timedelta

import httpx
from bs4 import BeautifulSoup
from dotenv import load_dotenv

load_dotenv()

# ==================== 模块独立配置 ====================
API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
API_URL = "https://api.deepseek.com/chat/completions"
MODEL_NAME = "deepseek-v4-flash"
CLEANUP_DAYS = 30
PROCESS_LIMIT = 30


# ======================================================

def fetch_trending_projects():
    url = "https://github.com/trending"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    print("\n[GitHub 模块] 🛰️ 正在爬取 GitHub Trending 页面...")
    try:
        response = httpx.get(url, headers=headers, timeout=15)
        response.raise_for_status()
    except Exception as e:
        print(f"❌ 抓取 Trending 失败: {e}")
        return []

    soup = BeautifulSoup(response.text, "html.parser")
    articles = soup.find_all("article", class_="Box-row")
    projects = []

    for article in articles:
        title_tag = article.find("h2", class_="h3")
        if not title_tag: continue
        title = title_tag.get_text(strip=True).replace(" ", "")

        link_tag = title_tag.find("a")
        project_url = f"https://github.com{link_tag['href']}" if link_tag else ""

        desc_tag = article.find("p", class_="col-9")
        basic_desc = desc_tag.get_text(strip=True) if desc_tag else ""

        projects.append({"title": title, "url": project_url, "raw_description": basic_desc})

    print(f"✅ 成功抓取到今日官方榜单共 {len(projects)} 个项目。")
    return projects


def fetch_readme_content(project_url):
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    try:
        response = httpx.get(project_url, headers=headers, timeout=15)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, "html.parser")
            readme_article = soup.find("article", class_="markdown-body")
            if readme_article:
                return readme_article.get_text(separator="\n", strip=True)[:4000]
    except Exception as e:
        print(f"⚠️ 抓取 README 异常: {e}")
    return ""


def get_ai_summary_html(title, basic_desc, readme_text):
    if not API_KEY or API_KEY == "your-api-key-here":
        return "<p>未配置大模型 API_KEY</p>", 0, 0

    headers = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}
    prompt = f"你是一个专业的技术文档精简器。请分析以下 GitHub 项目并生成中文总结。\n\n项目名称: {title}\n基础简介: {basic_desc}\n详细文档片段: \n\"\"\"\n{str(readme_text).strip()}\n\"\"\"\n\n[必须严格遵守的输出格式要求]：\n1. 严禁任何客套话、前言、后记。\n2. 直接输出一个以 <div> 开头，</div> 结尾的 HTML 代码片段。\n3. 内部包含三个部分，格式严格如下：\n<h3>一句话简介</h3>\n<p>这里用大白话解释核心功能。</p>\n<h3>核心亮点</h3>\n<ul><li>亮点1</li><li>亮点2</li></ul>\n<h3>应用场景</h3>\n<p>适合什么业务场景使用。</p>"

    payload = {"model": MODEL_NAME, "messages": [{"role": "user", "content": prompt}], "temperature": 0.2,
               "max_tokens": 1200}
    try:
        response = httpx.post(API_URL, headers=headers, json=payload, timeout=30)
        if response.status_code != 200:
            return f"<p class='error'>AI 生成失败 (HTTP {response.status_code})</p>", 0, 0

        result = response.json()
        ai_output = result["choices"][0]["message"]["content"].strip()
        match = re.search(r"<div.*?>.*</div>", ai_output, re.DOTALL)
        if match:
            ai_output = match.group(0)

        usage = result.get("usage", {})
        return ai_output, usage.get("prompt_tokens", 0), usage.get("completion_tokens", 0)
    except Exception as e:
        return f"<p class='error'>网络请求异常: {e}</p>", 0, 0


def run(db):
    """供 main.py 调用的模块执行入口"""
    archive = db.get("archive_pool", {})
    online_projects = fetch_trending_projects()

    if not online_projects:
        print("❌ 未捕获到在线数据，GitHub 抓取任务终止。")
        return

    print("\n[GitHub 模块] 🔍 开始进行智能去重比对...")
    db["current_trending"] = [proj["title"] for proj in online_projects]

    skipped_count = 0
    new_request_count = 0
    total_in_tokens = 0
    total_out_tokens = 0
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    print(f"\n[GitHub 模块] 🤖 开始通过 AI ({MODEL_NAME}) 丰富项目内容...")
    for proj in online_projects:
        title = proj["title"]
        if title in archive and "新入榜项目" not in archive[title]["ai_summary"]:
            skipped_count += 1
            archive[title]["updated_at"] = current_time
            continue

        if new_request_count >= PROCESS_LIMIT:
            archive[title] = {"url": proj["url"], "raw_description": proj["raw_description"],
                              "ai_summary": "<p>📢 新入榜项目，等待下一批次 AI 总结生成...</p>",
                              "updated_at": current_time}
            continue

        new_request_count += 1
        print(f"  ➡️ 正在分析新项目: {title}...")

        readme = fetch_readme_content(proj["url"])
        html_summary, in_t, out_t = get_ai_summary_html(title, proj["raw_description"], readme)

        total_in_tokens += in_t
        total_out_tokens += out_t

        archive[title] = {"url": proj["url"], "raw_description": proj["raw_description"], "ai_summary": html_summary,
                          "updated_at": current_time}

    print("\n[GitHub 模块] 🧹 正在执行数据缓存池自动瘦身...")
    now = datetime.now()
    expired_keys = []

    for title, info in archive.items():
        try:
            updated_time = datetime.strptime(info["updated_at"], "%Y-%m-%d %H:%M:%S")
            if now - updated_time > timedelta(days=CLEANUP_DAYS):
                expired_keys.append(title)
        except Exception:
            pass

    for key in expired_keys:
        del archive[key]

    print("\n=================== 📝 GitHub 模块执行看板 ===================")
    print(f"⏰ 执行时间：{current_time}")
    print(f"📋 今日榜单：当前看板共锁定了 {len(db['current_trending'])} 个项目")
    print(f"🛡️ 查重护航：成功拦截了 {skipped_count} 个重复项目")
    print(f"🚀 算力消耗：本次实际向 AI 提交了 {new_request_count} 个新项目")
    print(f"🧹 内存瘦身：清除了 {len(expired_keys)} 个过气项目")
    print(f"📊 算力总账：Input {total_in_tokens} Tokens，Output {total_out_tokens} Tokens")
    print("==============================================================")