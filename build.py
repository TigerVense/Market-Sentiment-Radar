import feedparser
import os
import google.generativeai as genai
from datetime import datetime
import pytz
import requests
import json

def get_fear_and_greed():
    url = "https://production.dataviz.cnn.io/index/fearandgreed/graphdata"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Referer": "https://edition.cnn.com/"
    }
    try:
        response = requests.get(url, headers=headers, timeout=10)
        data = response.json()
        score = int(data['fear_and_greed']['score'])
        rating = data['fear_and_greed']['rating']
        
        rating_dict = {
            "extreme fear": "极度恐慌",
            "fear": "恐慌",
            "neutral": "中立",
            "greed": "贪婪",
            "extreme greed": "极度贪婪"
        }
        cn_rating = rating_dict.get(rating.lower(), rating)
        return score, cn_rating
    except Exception as e:
        print(f"获取 CNN 指数失败: {e}")
        return 50, "中立"

def fetch_data():
    feeds = {
        "WSB(散户情绪)": "https://www.reddit.com/r/wallstreetbets/.rss",
        "Stocks(主流个股)": "https://www.reddit.com/r/stocks/.rss",
        "Options(期权异动)": "https://www.reddit.com/r/options/.rss",
        "Investing(长线逻辑)": "https://www.reddit.com/r/investing/.rss",
        "Economics(宏观大势)": "https://www.reddit.com/r/Economics/.rss",
        "SecAnalysis(硬核研报)": "https://www.reddit.com/r/SecurityAnalysis/.rss",
        "ThetaGang(波动率博弈)": "https://www.reddit.com/r/thetagang/.rss"
    }
    content = ""
    for name, url in feeds.items():
        try:
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
    
    prompt = f"""
    你是一个极其严谨的美股量化分析引擎。请基于（{today_str}）Reddit数据生成中文网页。
    
    【核心质量控制与反作弊机制】（违背将导致系统崩溃）：
    1. 【过滤无脑喷子】：纯情绪化、无逻辑的发泄废话直接丢弃！只保留有业务探讨或博弈逻辑的高价值评论。
    2. 【严防话题伪装成个股】：在“个股”版块，**绝对禁止**将“AI产业”、“SaaS”、“半导体”、“降息”、“宏观大势”或“ETF（如SPY/QQQ）”等泛话题当作股票列出！
    3. 标题结束立刻换行输出正文，绝对不要写任何“过渡段”或“总结语”。

    【强制网页三大结构】：
    
    <h2>1. 宏观与市场情绪</h2>
    - 直接列出今日关于宏观经济、政治、整体风险偏好的核心逻辑。强制摘录3-5条原文。
    
    <h2>2. 热议中的个股和想法</h2>
    - （不要写开头介绍，直接开始编号）
    - 【真·个股白名单校验】：本版块**只能**包含带有明确股票代码的具体上市公司。输出格式必须是：`1. **代码 (公司名)**`。
    - 在保证绝对是“真实上市公司”的前提下，尽可能挖掘 **10 到 15 只** 不同的股票。如果优质股票只有 12 只，就只输出 12 只，**宁缺毋滥，严禁拿话题凑数！**
    - 每只个股下，强制摘录 3-5 条高质量评论（纯英文+翻译）。如果尾部股票实在只有1-2条，也可接受，首要保证它是真股票。
    
    <h2>3. AI主线讨论</h2>
    - 严格按照以下 8 个分类输出标题，并在每个分类下大量摘录市场真实观点：
      * 模型：模型进展是第一性原理。
      * 算：技术路线、台积电产能分配。
      * 光：光通信格局、技术路线、边际变化；上游边际变化。
      * 存：格局、边际变化。
      * 电：数据中心对电力的消耗、边际变化 (如燃气轮机需求、格局、供应链等)。
      * 板：PCB格局、边际变化；上游边际变化。
      * 云：中国&全球云服务边际变化。
      * AI应用：AI对应用产业的改造，千行百业。

    【引用排版格式】：
    <blockquote class="quote">
      [纯英文原文，不带任何来源前缀]
      <div class="translation">翻译：[中文翻译]</div>
    </blockquote>

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
        <title>{{today_str}} 实战派情报终端</title>
        <script src="https://cdn.jsdelivr.net/npm/echarts@5.5.0/dist/echarts.min.js"></script>
        <style>
            :root { --bg: #0f172a; --card-bg: #1e293b; --text-main: #f1f5f9; --text-muted: #94a3b8; --accent: #38bdf8; --border: #334155; }
            body { background: var(--bg); color: var(--text-main); font-family: -apple-system, sans-serif; padding: 20px; line-height: 1.6; }
            .container { max-width: 900px; margin: auto; }
            h1 { color: var(--accent); border-bottom: 2px solid var(--border); padding-bottom: 10px; font-size: 1.8rem; }
            h2 { color: #fbbf24; margin-top: 40px; border-bottom: 1px solid var(--border); padding-bottom: 8px; font-size: 1.5rem; display: block; width: 100%; }
            h3 { color: #38bdf8; margin-top: 25px; font-size: 1.2rem; }
            .time { color: var(--text-muted); font-size: 0.9rem; margin-bottom: 20px; }
            
            .dashboard-card { background: #020617; border-radius: 12px; padding: 25px 20px 10px 20px; margin-top: 20px; margin-bottom: 30px; border: 1px solid var(--border); }
            .gauge-container { width: 100%; height: 260px; margin-top: 10px; }
            .index-title { text-align: center; color: #f8fafc; font-size: 1.5rem; font-weight: bold; margin-bottom: 5px; }
            .index-subtitle { text-align: center; color: var(--text-muted); font-size: 0.9rem; margin-bottom: 15px; position: relative; z-index: 10; }
            
            ol, ul { padding-left: 20px; margin-top: 15px; display: block; }
            ol li { margin-bottom: 40px; font-size: 1.1rem; border-bottom: 1px dashed var(--border); padding-bottom: 20px; display: block; }
            ol li strong { color: var(--accent); font-size: 1.4rem; display: block; margin-bottom: 15px; } 
            
            blockquote, .quote {
                background: #020617; border-left: 4px solid #10b981; padding: 12px 15px; margin: 15px 0; color: #e2e8f0; font-size: 0.95rem; border-radius: 4px; line-height: 1.6; display: block;
            }
            .translation { color: #94a3b8; margin-top: 10px; font-size: 0.9rem; border-top: 1px dotted #334155; padding-top: 10px; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🎯 {{today_str}} 市场异动与情报透视</h1>
            <p class="time">情报源头: 300+ 硬核原帖 | 最后分析时间: {{update_time}} (北京时间)</p>
            
            <div class="dashboard-card">
                <div class="index-title">Fear & Greed Index</div>
                <div class="index-subtitle">What emotion is driving the market now?</div>
                <div id="gauge" class="gauge-container"></div>
            </div>

            {{report}}
        </div>

        <script>
            var chartDom = document.getElementById('gauge');
            var myChart = echarts.init(chartDom);
            
            var option = {
                series: [{
                    type: 'gauge',
                    startAngle: 180, endAngle: 0, min: 0, max: 100,
                    radius: '100%',
                    center: ['50%', '65%'],
                    axisLine: {
                        lineStyle: {
                            width: 45,
                            color: [
                                [0.25, '#ef4444'], [0.45, '#f97316'], [0.55, '#d1d5db'], [0.75, '#84cc16'], [1, '#22c55e']  
                            ]
                        }
                    },
                    pointer: {
                        icon: 'path://M12.8,0.7l12,40.1H0.7L12.8,0.7z',
                        length: '65%', width: 8, offsetCenter: [0, '-5%'],
                        itemStyle: { color: '#ffffff' }
                    },
                    axisTick: { show: false }, splitLine: { show: false }, axisLabel: { show: false },
                    detail: {
                        fontSize: 45, fontWeight: 'bold', offsetCenter: [0, '20%'],
                        formatter: function (value) {
                            return value + '\\n{rating|{{fg_rating}}}';
                        },
                        rich: { rating: { fontSize: 20, color: '#94a3b8', padding: [10, 0, 0, 0], fontWeight: 'normal' } },
                        color: '#f8fafc'
                    },
                    data: [{ value: {{fg_score}} }]
                }]
            };
            option && myChart.setOption(option);
            window.addEventListener('resize', function() { myChart.resize(); });
        </script>
    </body>
    </html>
    """
    
    html_template = html_template.replace("{{today_str}}", today_str)
    html_template = html_template.replace("{{update_time}}", update_time)
    html_template = html_template.replace("{{report}}", report)
    html_template = html_template.replace("{{fg_score}}", str(fg_score))
    html_template = html_template.replace("{{fg_rating}}", fg_rating)
    
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html_template)

if __name__ == "__main__":
    print("1. 获取 CNN 指数...")
    score, rating = get_fear_and_greed()
    print("2. 抓取情报...")
    data = fetch_data()
    print("3. Gemini 深度过滤执行中...")
    analysis = get_ai_analysis(data)
    print("4. 渲染页面...")
    generate_html(analysis, score, rating)
