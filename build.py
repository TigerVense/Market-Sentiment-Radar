import feedparser
import os
import google.generativeai as genai
from datetime import datetime
import pytz
import requests
import json
import re

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
            f = feedparser.parse(url, agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64)')
            for entry in f.entries[:80]: 
                title = entry.title
                summary = entry.summary if 'summary' in entry else ""
                summary = re.sub('<[^<]+>', '', summary)
                content += f"[{name}] {title} | 补充: {summary[:800]}\n"
        except: pass
    return content

def get_ai_analysis(raw_text):
    genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
    model = genai.GenerativeModel('gemini-2.5-flash')
    tz = pytz.timezone('Asia/Shanghai')
    today_str = datetime.now(tz).strftime("%Y年%m月%d日")
    
    prompt = f"""
    你是一个专业的美股量化分析引擎。请基于下方提供的（{today_str}）Reddit数据池，提炼真实的市场情绪网页。
    
    【核心规则（绝对服从）】：
    1. 【反幻觉】：引用必须 100% 源自数据池！
    2. 【防截断】：如果发现补充内容在末尾被生硬截断，请只提取前面【完整的句子】。
    3. 【质量过滤】：剔除纯情绪化的谩骂。只保留包含业务探讨、数据支撑、或做多/做空逻辑的优质内容。
    4. 【禁止乱加标签】：输出个股标题时，格式为 `代码 (公司全名)`。
    5. 【纯净板块】：第二和第三部分只能是具体的“单一上市公司”。严禁混入 ETF 或泛行业板块！
    6. 【聚合深挖】：在个股板块，全面扫描数据池，如果能找到多条高质量观点，必须输出 2-4 条引用！

    【个股输出强制模板（必须严格复制以下 HTML 结构）】：
    <li>
      <div class="stock-tag">1. 代码 (公司全名)</div>
      <blockquote class="quote">
        [英文原文1]
        <div class="translation">翻译：[中文翻译1]</div>
      </blockquote>
    </li>

    【网页强制四大结构】：
    <h2>1. 宏观与市场情绪</h2> 
    <h2>2. 热议中的个股和想法</h2> 
    <h2>3. 小众公司冒泡</h2> 
    <h2>4. AI主线讨论</h2>

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
            .stock-tag { display: block; width: fit-content; background: rgba(251, 191, 36, 0.15); color: #fbbf24; padding: 6px 16px; border-left: 5px solid #fbbf24; border-radius: 4px; font-size: 1.3rem; margin-bottom: 15px; font-weight: bold; }
            .track-header { display: block; color: var(--accent); font-size: 1.25rem; margin-top: 35px; margin-bottom: 15px; padding: 8px 12px; background: linear-gradient(90deg, rgba(56, 189, 248, 0.1) 0%, transparent 100%); border-bottom: 2px solid rgba(56, 189, 248, 0.4); font-weight: bold; }
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

def send_wechat_push(score, rating):
    token = os.environ.get("PUSHPLUS_TOKEN")
    if not token: return

    repo_url = "https://vense-23.github.io/Market-Sentiment-Radar/" 
    title = f"🚨 美股情报雷达已更新 ({rating})"
    content = f"<h3>📊 当前市场情绪：{rating} ({score}分)</h3><p>👉 <b><a href='{repo_url}'>点击此处，立即查看完整版深度透视网页</a></b></p>"
    
    try: requests.post("http://www.pushplus.plus/send", json={"token": token, "title": title, "content": content, "template": "html"}, timeout=10)
    except: pass

def send_discord_push(score, rating):
    webhook_url = os.environ.get("DISCORD_WEBHOOK_URL")
    if not webhook_url: return
    
    # 根据分数动态改变 Discord 卡片的侧边颜色 (红色代表恐慌，绿色代表贪婪)
    color = 15158332 if score < 45 else (3066993 if score > 55 else 9807270)
    
    repo_url = "https://vense-23.github.io/Market-Sentiment-Radar/" 
    tz = pytz.timezone('Asia/Shanghai')
    today_str = datetime.now(tz).strftime("%Y-%m-%d %H:%M")
    
    payload = {
        "username": "实战派雷达",
        "avatar_url": "https://cdn-icons-png.flaticon.com/512/3254/3254107.png",
        "embeds": [{
            "title": f"🎯 {today_str} 美股情绪深度研报已出炉",
            "description": f"**📊 CNN 恐慌与贪婪指数**：`{rating} ({score}分)`\n\n🤖 AI 已经完成 Reddit 全网数据扫描，提取了最新的个股博弈逻辑与小众黑马股。\n\n👉 **[点击此处进入浏览器阅读极客排版全文]({repo_url})**",
            "color": color
        }]
    }
    
    try:
        requests.post(webhook_url, json=payload, timeout=10)
        print("Discord 推送成功！")
    except Exception as e:
        print(f"Discord 推送失败: {e}")

if __name__ == "__main__":
    score, rating = get_fear_and_greed()
    data = fetch_data()
    analysis = get_ai_analysis(data)
    generate_html(analysis, score, rating)
    
    # 网页生成完后，触发推送（代码会自动检测你填了哪个 Secrets，填了哪个就推哪个）
    send_wechat_push(score, rating)
    send_discord_push(score, rating)
