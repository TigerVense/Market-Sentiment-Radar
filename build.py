import feedparser
import os
import google.generativeai as genai
from datetime import datetime
import pytz
import requests
import json

def get_fear_and_greed():
    url = "https://production.dataviz.cnn.io/index/fearandgreed/graphdata"
    headers = { "User-Agent": "Mozilla/5.0", "Referer": "https://edition.cnn.com/" }
    try:
        response = requests.get(url, headers=headers, timeout=10)
        data = response.json()
        score = int(data['fear_and_greed']['score'])
        rating = data['fear_and_greed']['rating']
        rating_dict = {"extreme fear": "极度恐慌", "fear": "恐慌", "neutral": "中立", "greed": "贪婪", "extreme greed": "极度贪婪"}
        return score, rating_dict.get(rating.lower(), rating)
    except: return 50, "中立"

def fetch_data():
    feeds = {
        "WSB": "https://www.reddit.com/r/wallstreetbets/.rss",
        "Stocks": "https://www.reddit.com/r/stocks/.rss",
        "Options": "https://www.reddit.com/r/options/.rss",
        "Investing": "https://www.reddit.com/r/investing/.rss",
        "Economics": "https://www.reddit.com/r/Economics/.rss",
        "SecAnalysis": "https://www.reddit.com/r/SecurityAnalysis/.rss",
        "ThetaGang": "https://www.reddit.com/r/thetagang/.rss"
    }
    content = ""
    for name, url in feeds.items():
        try:
            f = feedparser.parse(url, agent='Mozilla/5.0')
            for entry in f.entries[:50]: 
                # 尽量获取更多真实文本，避免 AI 幻觉
                title = entry.title
                summary = entry.summary[:200] if 'summary' in entry else ""
                # 清理 summary 中的 HTML 标签
                import re
                summary = re.sub('<[^<]+>', '', summary)
                content += f"[{name}] {title} | 补充内容: {summary}\n"
        except: pass
    return content

def get_ai_analysis(raw_text):
    genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
    model = genai.GenerativeModel('gemini-2.5-flash')
    tz = pytz.timezone('Asia/Shanghai')
    today_str = datetime.now(tz).strftime("%Y年%m月%d日")
    
    prompt = f"""
    你是一个极其严谨的美股量化分析引擎。请基于（{today_str}）Reddit数据生成网页。
    
    【最高警戒：反幻觉与绝对真实（生死攸关）】：
    1. 你摘录的每一句 [英文原文] 必须 100% 逐字源自下方提供的【原始数据】！
    2. 绝对禁止为了凑数而凭空捏造、杜撰不存在的评论！绝不能使用你的历史训练数据（不准出现旧新闻如GPT-4发布等）。
    3. 真实性高于一切数量要求！如果关于某只股票只有1条真实数据，那就只写1条；如果没有看空的真实数据，就不准捏造看空逻辑。

    【个股输出强制模板（必须严格复制以下 HTML 结构填空）】：
    <li>
      <div class="stock-tag">1. 代码 (公司全名)</div>
      <blockquote class="quote">
        [100%源自原始数据的英文原文]
        <div class="translation">翻译：[中文翻译]</div>
      </blockquote>
    </li>

    【网页强制四大结构】：
    <h2>1. 宏观与市场情绪</h2> (总结今日核心逻辑，摘录真实原文)
    <h2>2. 热议中的个股和想法</h2> (挖掘真实提及的上市公司，有几条写几条，绝不造假)
    <h2>3. 小众公司冒泡</h2> (挖掘0-10只冷门股，没有就不写)
    <h2>4. AI主线讨论</h2> (使用 <div class="track-header">标题</div> 标签输出8大类：模型、算、光、存、电、板、云、AI应用。只有在原始数据中找到对应内容才写，找不到就留空)

    原始数据：
    {raw_text}
    """
    response = model.generate_content(prompt)
    return response.text.replace("```html", "").replace("```", "").strip()

def generate_html(report, fg_score, fg_rating):
    tz = pytz.timezone('Asia/Shanghai')
    update_time = datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S")
    today_str = datetime.now(tz).strftime("%m月%d日")
    
    html_template = """
    <!DOCTYPE html>
    <html lang="zh">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>{{today_str}} 情报终端</title>
        <script src="https://cdn.jsdelivr.net/npm/echarts@5.5.0/dist/echarts.min.js"></script>
        <style>
            :root { --bg: #0f172a; --text: #f1f5f9; --accent: #38bdf8; --border: #334155; }
            body { background: var(--bg); color: var(--text); font-family: -apple-system, sans-serif; padding: 20px; line-height: 1.6; }
            .container { max-width: 900px; margin: auto; }
            h1 { color: var(--accent); border-bottom: 2px solid var(--border); padding-bottom: 10px; }
            h2 { color: #fbbf24; margin-top: 45px; border-bottom: 1px solid var(--border); padding-bottom: 10px; }
            
            .stock-tag { 
                display: block; width: fit-content; background: rgba(251, 191, 36, 0.15); 
                color: #fbbf24; padding: 6px 16px; border-left: 5px solid #fbbf24; 
                border-radius: 4px; font-size: 1.3rem; margin-bottom: 15px; font-weight: bold;
            }
            
            .track-header { 
                display: block; color: var(--accent); font-size: 1.25rem; margin-top: 35px; margin-bottom: 15px; padding: 8px 12px;
                background: linear-gradient(90deg, rgba(56, 189, 248, 0.1) 0%, transparent 100%);
                border-bottom: 2px solid rgba(56, 189, 248, 0.4); font-weight: bold;
            }

            .dashboard-card { background: #020617; border-radius: 12px; padding: 25px 20px; margin: 30px 0; border: 1px solid var(--border); }
            .gauge-container { width: 100%; height: 260px; }
            
            ol { padding-left: 0; }
            ol li { margin-bottom: 50px; list-style: none; border-bottom: 1px dashed var(--border); padding-bottom: 25px; }
            blockquote { background: #1e293b; border-left: 4px solid #10b981; padding: 16px; margin: 15px 0; border-radius: 6px; color: #f8fafc; font-size: 0.95rem; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1); }
            .translation { color: #cbd5e1; margin-top: 12px; font-size: 0.9rem; border-top: 1px dashed #475569; padding-top: 12px; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🎯 {{today_str}} 市场情报透视</h1>
            <p style="color:#94a3b8">情报最后更新: {{update_time}} (北京时间)</p>
            <div class="dashboard-card"><div id="gauge" class="gauge-container"></div></div>
            {{report}}
        </div>
        <script>
            var myChart = echarts.init(document.getElementById('gauge'));
            myChart.setOption({
                series: [{
                    type: 'gauge', startAngle: 180, endAngle: 0, min: 0, max: 100, radius: '100%', center: ['50%', '75%'],
                    axisLine: { lineStyle: { width: 45, color: [[0.25, '#ef4444'], [0.45, '#f97316'], [0.55, '#d1d5db'], [0.75, '#84cc16'], [1, '#22c55e']] } },
                    pointer: { length: '60%', width: 8, itemStyle: { color: '#fff' } },
                    detail: { fontSize: 40, fontWeight: 'bold', offsetCenter: [0, '25%'], formatter: '{value}\\n{{fg_rating}}', color: '#fff' },
                    data: [{ value: {{fg_score}} }]
                }]
            });
        </script>
    </body>
    </html>
    """
    html_template = html_template.replace("{{today_str}}", today_str).replace("{{update_time}}", update_time).replace("{{report}}", report).replace("{{fg_score}}", str(fg_score)).replace("{{fg_rating}}", fg_rating)
    with open("index.html", "w", encoding="utf-8") as f: f.write(html_template)

if __name__ == "__main__":
    score, rating = get_fear_and_greed()
    data = fetch_data()
    analysis = get_ai_analysis(data)
    generate_html(analysis, score, rating)
