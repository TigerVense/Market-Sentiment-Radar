import feedparser
import os
import google.generativeai as genai
from datetime import datetime
import pytz

def fetch_data():
    feeds = {
        "WSB(散户情绪)": "https://www.reddit.com/r/wallstreetbets/.rss",
        "Stocks(主流个股)": "https://www.reddit.com/r/stocks/.rss",
        "Options(期权异动)": "https://www.reddit.com/r/options/.rss",
        "Investing(长线逻辑)": "https://www.reddit.com/r/investing/.rss"
    }
    content = ""
    for name, url in feeds.items():
        try:
            # 【爆改点 1】：将抓取深度提升至 50 条，总计提供约 200 条原材料
            f = feedparser.parse(url, agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64)')
            for entry in f.entries[:50]: 
                content += f"[{name}] {entry.title}\n"
        except Exception as e:
            print(f"抓取 {name} 失败: {e}")
    return content

def get_ai_analysis(raw_text):
    genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
    model = genai.GenerativeModel('gemini-2.5-flash')
    
    tz = pytz.timezone('Asia/Shanghai')
    today_str = datetime.now(tz).strftime("%Y年%m月%d日")
    
    # 【爆改点 2】：引入负面提示词、动态数量控制和海量摘录要求
    prompt = f"""
    你现在是一个服务于一线实战派参与者的顶级美股情绪分析引擎。
    请基于今日（{today_str}）Reddit 最新数据（近200条讨论），生成极度硬核的中文网页简报。
    
    分析核心要求（必须严格遵守）：
    1. 【严格的杂音过滤（Negative Prompt）】：
       - 绝对禁止收录任何关于券商软件故障、账户无法交易、期权限制、出入金问题的话题（如 Moomoo/FUTU, JPM, Robinhood 客服类问题）。
       - 绝对禁止将 SPY, QQQ 等大盘 ETF 或“降息”、“衰退”等纯宏观话题列为个股。
    
    2. 【宁缺毋滥的个股名单（动态 10-20 只）】：
       - 筛选标准：仅限今日有高频提及、且包含具体基本面或交易情绪博弈的上市公司。
       - 如果真正有价值的个股只有 12 只，就只写 12 只，宁缺毋滥。
       - 排版：必须按顺序“1. 2. 3...”垂直向下排列。
       - 【重要细节】：在每只个股逻辑下方，如果存在优质讨论，请摘录 3-5 条原文（带引用样式），不要吝啬篇幅。

    3. 【AI 产业链深度追踪与海量原文展示】：
       - 聚焦：模型、算、光、存、电（组件/发电/电网）、板、云。
       - 【重要细节】：这是本次报告的核心！在每一个产业链环节下方，不要过度精简。如果底层数据库中有大量关于该环节的讨论，请直接展示 5 条、10 条甚至 15 条最高质量的原文摘录（翻译为中文）。越详细、越原汁原味越好，让我直接看到市场的真实声音。

    4. 【排版要求】：只输出内部的 HTML 元素，使用 <ol> 或 <ul> 列表。<blockquote class="quote"> 用于包裹原文摘录。如果有连续的多条摘录，请将它们分多个 blockquote 堆叠排列。

    今日原始讨论数据池：
    {raw_text}
    """
    response = model.generate_content(prompt)
    return response.text.replace("```html", "").replace("```", "").strip()

def generate_html(report):
    tz = pytz.timezone('Asia/Shanghai')
    update_time = datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S")
    today_str = datetime.now(tz).strftime("%m月%d日")
    
    html_template = f"""
    <!DOCTYPE html>
    <html lang="zh">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>{today_str} 核心个股与AI雷达</title>
        <style>
            :root {{
                --bg: #0f172a;
                --text-main: #f1f5f9;
                --text-muted: #94a3b8;
                --accent: #38bdf8;
                --border: #334155;
            }}
            body {{ background: var(--bg); color: var(--text-main); font-family: -apple-system, sans-serif; padding: 20px; line-height: 1.6; }}
            .container {{ max-width: 900px; margin: auto; }}
            h1 {{ color: var(--accent); border-bottom: 2px solid var(--border); padding-bottom: 10px; font-size: 1.8rem; }}
            h2, h3 {{ color: #fbbf24; margin-top: 30px; }}
            .time {{ color: var(--text-muted); font-size: 0.9rem; margin-bottom: 20px; }}
            
            ol {{ padding-left: 20px; margin-top: 20px; }}
            ol li {{ margin-bottom: 30px; font-size: 1.1rem; border-bottom: 1px dashed var(--border); padding-bottom: 15px; }}
            ol li strong {{ color: var(--accent); font-size: 1.2rem; }}
            
            /* 优化后的原文摘录样式，适合大量堆叠 */
            blockquote, .quote {{
                background: #020617;
                border-left: 4px solid #10b981;
                padding: 10px 15px;
                margin: 8px 0;
                color: #cbd5e1;
                font-size: 0.95rem;
                font-style: italic;
                border-radius: 4px;
                line-height: 1.5;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🎯 {today_str} 市场异动个股与AI产业链透视</h1>
            <p class="time">情报源头: 200+ 最新高热原帖 | 最后分析时间: {update_time} (北京时间)</p>
            {report}
        </div>
    </body>
    </html>
    """
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html_template)

if __name__ == "__main__":
    print("开始大批量抓取今日 200+ 原始数据...")
    data = fetch_data()
    print("Gemini 正在执行严苛过滤与深度海量摘录...")
    analysis = get_ai_analysis(data)
    print("生成网页...")
    generate_html(analysis)
