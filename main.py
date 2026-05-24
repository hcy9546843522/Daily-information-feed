import json
import os

from dotenv import load_dotenv

load_dotenv()

from crawlers import github_trending
from render import build_html

DATA_FILE = "database/dashboard_data.json"


def load_structured_data(filename=DATA_FILE):
    """加载底层总数据库"""
    default_structure = {"current_trending": [], "archive_pool": {}}
    if os.path.exists(filename):
        try:
            with open(filename, "r", encoding="utf-8") as f:
                data = json.load(f)
                if "current_trending" not in data: data["current_trending"] = []
                if "archive_pool" not in data: data["archive_pool"] = {}
                return data
        except Exception as e:
            print(f"⚠️ 读取 JSON 失败 ({e})，将初始化新结构。")
    return default_structure


def save_to_json(data, filename=DATA_FILE):
    """将全量数据安全持久化"""
    os.makedirs(os.path.dirname(filename), exist_ok=True)
    try:
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=4)
    except Exception as e:
        print(f"❌ 写入 JSON 失败: {e}")


def main():
    print("========================================")
    print("  🚀 启动自动化信息流抓取与构建中心")
    print("========================================")

    # 1. 连接数据库
    db = load_structured_data()

    # 2. 调用抓取模块群 (未来若新增模块，直接在此处增加调用即可)
    github_trending.run(db)

    # 3. 将各大模块抓取更新后的数据统一保存
    save_to_json(db)

    # 4. 触发网页渲染模块，构建前端展示页
    print("\n[渲染模块] 🖥️ 正在重新静态化构建前端页面...")
    refresh_token = os.getenv("REFRESH_TOKEN", "")
    build_html.build(db, refresh_token=refresh_token)

    print("\n✅ 全流程执行完毕！可以直接双击打开项目根目录下的 index.html 查看。")


if __name__ == "__main__":
    main()