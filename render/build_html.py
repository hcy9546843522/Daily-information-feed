import html

HTML_FILE = "index.html"  # 输出到项目的根目录


def build(db, output_filename=HTML_FILE):
    current_list = db.get("current_trending", [])
    pool = db.get("archive_pool", {})
    cards_html = ""

    for title in current_list:
        meta = pool.get(title)
        if meta:
            safe_title = html.escape(title)
            safe_desc = html.escape(meta['raw_description'] or 'No description.')
            ai_raw = meta['ai_summary']
            summary_part = ""
            details_part = ai_raw

            if "</h3>" in ai_raw:
                try:
                    parts = ai_raw.split("</h3>", 1)
                    header_and_first_p = parts[1].split("<h3>", 1)
                    summary_part = header_and_first_p[0].strip()
                    details_part = "<h3>" + header_and_first_p[1] if len(header_and_first_p) > 1 else ""
                except Exception:
                    summary_part = f"<p>{safe_desc}</p>"
                    details_part = ai_raw

            cards_html += f"""
            <div class="card">
                <div class="card-body">
                    <div class="card-header">
                        <h2 class="card-title">
                            <a href="{meta["url"]}" target="_blank">{safe_title}</a>
                        </h2>
                        <span class="badge">GITHUB</span>
                    </div>
                    <div class="ai-summary-zone">{summary_part}</div>
                    <details class="fold-section">
                        <summary class="fold-trigger">
                            <span class="arrow">▶</span><span>展开详细分析与亮点</span>
                        </summary>
                        <div class="ai-content">
                            {details_part}
                            <div class="raw-desc-zone">
                                <span class="raw-title">Raw Description:</span>
                                <p>{safe_desc}</p>
                            </div>
                        </div>
                    </details>
                </div>
                <div class="card-footer">
                    <span>🔄 每日自动流同步</span><span>{meta["updated_at"].split(" ")[0]}</span>
                </div>
            </div>"""

    if not cards_html:
        cards_html = '<div style="grid-column: 1/-1; text-align: center; color: #94a3b8; padding: 4rem 0; font-size: 0.875rem;">📭 今日暂无更新数据。</div>'

    html_template = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>个人专属看板</title>
    <style>
        * {{box-sizing: border-box; margin: 0; padding: 0;}} 
        body {{background-color: #f8fafc; color: #334155; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif; padding-bottom: 5rem;}} 
        header {{background-color: rgba(255, 255, 255, 0.95); border-bottom: 1px solid #e2e8f0; position: sticky; top: 0; z-index: 50;}} 
        .header-container {{max-width: 1280px; margin: 0 auto; padding: 0.85rem 1.5rem; display: flex; justify-content: space-between; align-items: center;}} 
        .brand-zone {{display: flex; align-items: center; gap: 0.75rem;}} 
        .logo-box {{background-color: #2563eb; color: white; font-weight: bold; width: 2.25rem; height: 2.25rem; border-radius: 0.75rem; display: flex; align-items: center; justify-content: center;}} 
        .brand-title {{font-size: 1rem; font-weight: 700; color: #0f172a;}} 
        .brand-subtitle {{font-size: 0.7rem; color: #94a3b8; font-weight: 500;}} 
        nav {{display: flex; gap: 0.5rem; background-color: #f1f5f9; padding: 0.25rem; border-radius: 0.75rem;}} 
        .nav-btn {{border: none; padding: 0.35rem 1rem; font-size: 0.75rem; font-weight: 600; border-radius: 0.5rem; cursor: pointer;}} 
        .nav-btn.active {{background-color: white; color: #2563eb;}} 
        .nav-btn.disabled {{background: transparent; color: #94a3b8; cursor: not-allowed;}} 
        main {{max-width: 1280px; margin: 0 auto; padding: 2rem 1.5rem;}} 
        .grid {{display: grid; grid-template-columns: repeat(auto-fill, minmax(360px, 1fr)); gap: 1.25rem;}} 
        .card {{background-color: white; border: 1px solid #e2e8f0; border-radius: 1rem; display: flex; flex-direction: column; justify-content: space-between;}} 
        .card-body {{padding: 1.5rem;}} 
        .card-header {{display: flex; justify-content: space-between; align-items: center; gap: 1rem; margin-bottom: 0.75rem;}} 
        .card-title {{font-size: 0.95rem; font-weight: 600; color: #0f172a; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;}} 
        .card-title a {{color: inherit; text-decoration: none;}} 
        .badge {{font-size: 0.65rem; font-weight: 700; background-color: #f8fafc; border: 1px solid #e2e8f0; color: #64748b; padding: 0.15rem 0.5rem; border-radius: 0.375rem;}} 
        .ai-summary-zone p {{font-size: 0.92rem; line-height: 1.55; color: #334155; font-weight: 500;}} 
        .fold-section {{margin-top: 1rem; padding-top: 0.75rem; border-top: 1px solid #f1f5f9;}} 
        .fold-trigger {{display: flex; align-items: center; gap: 0.35rem; font-size: 0.75rem; font-weight: 600; color: #2563eb; cursor: pointer; list-style: none; outline: none;}} 
        .fold-trigger::-webkit-details-marker {{display: none;}} 
        .fold-trigger .arrow {{font-size: 0.65rem; display: inline-block; transition: transform 0.2s;}} 
        .fold-section[open] .fold-trigger .arrow {{transform: rotate(90deg);}} 
        .ai-content {{margin-top: 0.75rem;}} 
        .ai-content h3 {{font-size: 0.85rem; font-weight: 600; color: #0f172a; margin-top: 0.85rem; margin-bottom: 0.35rem; border-left: 3px solid #3b82f6; padding-left: 0.4rem;}} 
        .ai-content p {{font-size: 0.85rem; color: #475569; line-height: 1.5; margin-bottom: 0.5rem;}} 
        .ai-content ul {{list-style-type: disc; padding-left: 1.1rem; margin-bottom: 0.5rem;}} 
        .ai-content li {{font-size: 0.85rem; color: #475569; margin-bottom: 0.2rem;}} 
        .raw-desc-zone {{margin-top: 1rem; padding-top: 0.75rem; border-top: 1px solid #f1f5f9; font-size: 0.7rem; color: #94a3b8;}} 
        .raw-title {{font-weight: 600; color: #64748b; display: block;}} 
        .card-footer {{padding: 0.75rem 1.5rem; border-top: 1px solid #f8fafc; background-color: #fafafa; border-radius: 0 0 1rem 1rem; display: flex; justify-content: space-between; align-items: center; font-size: 0.65rem; color: #94a3b8;}} 
        footer.site-footer {{text-align: center; padding: 2.5rem 0; font-size: 0.7rem; color: #94a3b8; border-top: 1px solid #e2e8f0; background-color: white; margin-top: 8rem;}}
    </style>
</head>
<body>
    <header>
        <div class="header-container">
            <div class="brand-zone">
                <div class="logo-box">✨</div>
                <div>
                    <h1 class="brand-title">专属自动化快讯聚合</h1>
                    <p class="brand-subtitle">模块化全静态免跨域版本</p>
                </div>
            </div>
            <nav>
                <button class="nav-btn active">🐱 GitHub 热门</button>
                <button class="nav-btn disabled" disabled>➕ 待扩展数据源</button>
            </nav>
        </div>
    </header>
    <main>
        <div class="grid">{cards_html}</div>
    </main>
    <footer class="site-footer">
        <p>© 2026 自动化空间 · 高内聚低耦合模块化架构</p>
    </footer>
</body>
</html>"""

    try:
        with open(output_filename, "w", encoding="utf-8") as f:
            f.write(html_template)
        print(f"🎉 网页渲染模块执行成功！已在根目录生成网页: {output_filename}")
    except Exception as e:
        print(f"❌ 写入 HTML 失败: {e}")