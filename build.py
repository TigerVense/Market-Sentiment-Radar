import feedparser
import os
import google.generativeai as genai
from datetime import datetime
import pytz

# 1. 扩大讨论区抓取范围
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
            # 增加抓取深度，每个版块取前 15 条
            f = feedparser.parse(url, agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64)')
            for entry in f.entries[:15]:
                content += f"[{name}] {entry.title}\n"
        except Exception as e:
            print(f"抓取 {name} 失败: {e}")
    return content

# 2. 调用 Gemini 2.5 进行产业链深度扫描
def get_ai_analysis(raw_text):
    genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
    # 使用你指定的最新模型
    model = genai.GenerativeModel('gemini-2.5-flash')
    
    prompt = f"""
    你现在是一个资深美股机构级分析助手。请分析以下 Reddit 讨论并生成一份深度中文网页简报。
    
    分析要求：
    1. 【全市场扫描】：列出当前讨论热度最高的前 20 只美股个股（Ticker），并简述其核心看点。
    2. 【AI 产业链深度穿透】：根据以下 Check List 重点分析科技股异动：
       - 模型：最新进展与第一性原理讨论。
       - 算：技术路线演进、台积电产能分配。
       - 光：光通信格局（CPO/NPO）、边际变化及上游异动（重点看中际旭创相关逻辑）。
       - 存：存储格局与边际变化。
       - 电：数据中心电力消耗（燃气轮机需求、公用事业板块相关）。
       - 板：PCB 布局、技术路径边际变化。
       - 云/应用：全球云服务商动态及 AI 对千行百业的改造。
    3. 【风险评估】：提炼当前散户最担心的 3 个宏观或技术性风险。

    请直接输出专业美观的 HTML 元素（不要包含 ```html 标签），使用卡片布局。
    原始讨论数据：
    {raw_text}
    """
    response = model.generate_content(prompt)
    # 清理可能生成的 markdown 代码块标记
    return response.text.replace("```html", "").replace("```", "").strip()

def generate_html(report):
    tz = pytz.timezone('Asia/Shanghai')
    update_time = datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S")
    
    html_template = f"""
    <!DOCTYPE html>
    <html lang="zh">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>AI & 全美股雷达 | 深度实战版</title>
        <style>
            body {{ background: #020617; color: #f8fafc; font-family: -apple-system, sans-serif; padding: 20px; }}
            .container {{ max-width: 1000px; margin: auto; }}
            h1 {{ color: #38bdf8; border-bottom: 2px solid #1e293b; padding-bottom: 10px; }}
            .time {{ color: #94a3b8; font-size: 0.9rem; margin-bottom: 30px; }}
            .card {{ background: #0f172a; border: 1px solid #1e293b; border-radius: 12px; padding: 20px; margin-bottom: 20px; box-shadow: 0 4px 6px -1px rgba(0,0,0,0.1); }}
            h3 {{ color: #fbbf24; margin-top: 0; }}
            li {{ margin-bottom: 8px; border-bottom: 1px solid #1e293b; padding-bottom: 4px; }}
            strong {{ color: #38bdf8; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🔭 AI & 全美股情绪雷达 (深度分析版)</h1>
            <p class="time">最后分析时间: {update_time} (北京时间)</p>
            {report}
        </div>
    </body>
    </html>
    """
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html_template)

if __name__ == "__main__":
    data = fetch_data()
    analysis = get_ai_analysis(data)
    generate_html(analysis)
