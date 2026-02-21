import feedparser
import os
import google.generativeai as genai
from datetime import datetime
import pytz
import requests
import json

def get_fear_and_greed():
    url = "https://production.dataviz.cnn.io/index/fearandgreed/graphdata"
    headers = { "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)", "Referer": "https://edition.cnn.com/" }
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
            f = feedparser.parse(url, agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36')
            for entry in f.entries[:80]: 
                title = entry.title
                summary = entry.summary[:200] if 'summary' in entry else ""
                import re
                summary = re.sub('<[^<]+>', '', summary)
                content += f"[{name}] {title} | 补充: {summary}\n"
        except: pass
    return content

def get_ai_analysis(raw_text):
    genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
    model = genai.GenerativeModel('gemini-2.5-flash')
    tz = pytz.timezone('Asia/Shanghai')
    today_str = datetime.now(tz).strftime("%Y年%m月%d日")
    
    prompt = f"""
    你是一个专业的美股量化分析引擎。请基于下方提供的（{today_str}）Reddit数据池，提炼真实的市场情绪网页。
    
    【核心规则（绝对服从，生死攸关）】：
    1. 【反幻觉】：所有引用必须 100% 源自下方数据池！绝对不允许使用你的历史记忆捏造数据。
    2. 【质量过滤】：剔除纯情绪化的谩骂（如“微软是垃圾”、“死猫跳”）和毫无逻辑的发泄。只保留包含业务探讨、数据支撑、或做多/做空逻辑的优质内容。如果原帖只是一堆公司名字的堆砌而没有实质内容，直接丢弃！
    3. 【禁止乱加标签】：在输出个股标题时，严格遵守 `代码 (公司全名)` 的格式。绝对不要自己加戏去标注“未上市公司”、“私人公司”等未经核实的修饰词（例如不要写 Klarna(未上市瑞典金融科技公司)，直接写 Klarna 即可）。
    4. 【纯净的个股板块】：第二和第三部分只能是具体的“单一上市公司”！绝对禁止把 ETF、宏观话题、或泛行业板块混入个股版块！
    5. 【聚合深挖（严禁偷懒）】：在个股板块，请全面扫描数据池，把关于该公司的所有有价值的讨论聚合在一起。如果能找到多条不同的高质量观点，必须输出 2-4 条引用，绝不要只放 1 条就草草了事！（除非数据池里真的只有1条）。

    【个股输出强制模板（必须严格复制以下 HTML 结构）】：
    <li>
      <div class="stock-tag">1. 代码 (公司全名)</div>
      <blockquote class="quote">
        [英文原文1]
        <div class="translation">翻译：[中文翻译1]</div>
      </blockquote>
      </li>

    【网页强制四大结构】：
    <h2>1. 宏观与市场情绪</h2> (总结今日核心逻辑，摘录真实原文)
    <h2>2. 热议中的个股和想法</h2> (挖掘真实提及的高热度上市公司，每只尽力输出多条多空逻辑引用)
    <h2>3. 小众公司冒泡</h2> (挖掘0-10只冷门股，没有就不写)
    <h2>4. AI主线讨论</h2> (使用 <div class="track-header">标题</div> 标签严格输出8大类：模型、算、光、存、电、板、云、AI应用)

    原始数据池：
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
