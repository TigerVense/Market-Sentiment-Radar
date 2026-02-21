import feedparser
import os
import google.generativeai as genai
from datetime import datetime
import pytz
import requests
import json

# 1. 抓取 CNN 恐慌与贪婪指数底层数据
def get_fear_and_greed():
    url = "https://production.dataviz.cnn.io/index/fearandgreed/graphdata"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.0.0 Safari/537.36",
        "Referer": "https://edition.cnn.com/"
    }
    try:
        response = requests.get(url, headers=headers, timeout=10)
        data = response.json()
        score = int(data['fear_and_greed']['score'])
        rating = data['fear_and_greed']['rating']
        
        # 将英文评级翻译为中文
        rating_dict = {
            "extreme fear": "极度恐慌",
            "fear": "恐慌",
            "neutral": "中性",
            "greed": "贪婪",
            "extreme greed": "极度贪婪"
        }
        cn_rating = rating_dict.get(rating.lower(), rating)
        return score, cn_rating
    except Exception as e:
        print(f"获取 CNN 指数失败: {e}")
        return 50, "数据获取延迟"

# 2. 七大硬核信息源抓取
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

# 3. AI 深度过滤与分析
def get_ai_analysis(raw_text):
    genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))
    model = genai.GenerativeModel('gemini-2.5-flash')
    
    tz = pytz.timezone('Asia/Shanghai')
    today_str = datetime.now(tz).strftime("%Y年%m月%d日")
    
    prompt = f"""
    你现在是一个服务于一线实战派参与者的顶级美股情绪分析引擎。
    请基于今日（{today_str}）Reddit 最新数据（近350条讨论），生成极度硬核的中文网页简报。
    
    【核心质量控制与杂音过滤】（最高优先级，必须严格遵守）：
    1. 绝对禁止收录券商软件故障、账户限制、出入金问题。
    2. 绝对禁止收录纯情绪化的攻击或无脑宣泄。
    3. 只准提取客观、中肯、带有逻辑支撑的观点。

    【强制排版与翻译要求】：
    - 所有引用的 Reddit 评论必须包裹在 <blockquote class="quote"> 中。
    - 每一条引用必须严格采用以下结构：
      [英文原文]
      <div class="translation">翻译：[中文翻译]</div>

    【网页三大强制结构】（必须且只能按顺序输出这三个模块）：
    
    <h2>1. 宏观与市场情绪</h2>
    - 总结今日关于宏观经济、政治局势、机构/散户仓位、整体风险偏好、市场风险的讨论。
    - 必须摘录 3-5 条高质量的宏观/情绪面逻辑原帖。
    
    <h2>2. 热议中的个股和想法</h2>
    - 筛选 10-20 只今日高频提及、且有基本面/博弈逻辑的具体上市公司（不要把大盘 ETF 混进来）。
    - 必须按顺序“1. 2. 3...”垂直向下排列。
    - 在每只个股逻辑下方，摘录 2-5 条针对该公司的理性、深度的优质评论。
    
    <h2>3. AI主线讨论</h2>
    - 聚焦 AI 产业链：模型、算力、光通信、存储、电力、PCB、云服务。
    - 在相关的细分环节下方，汇总摘录 5-10 个当日探讨行业趋势、技术演进或供应链博弈的高质量原文。

    今日原始讨论数据池：
    {raw_text}
    """
    response = model.generate_content(prompt)
    return response.text.replace("```html", "").replace("```", "").strip()

# 4. 组装带 ECharts 仪表盘的 HTML
def generate_html(report, fg_score, fg_rating):
    tz = pytz.timezone('Asia/Shanghai')
    update_time = datetime.now(tz).strftime("%Y-%m-%d %H:%M:%S")
    today_str = datetime.now(tz).strftime("%m月%d日")
    
    # 使用纯文本替换，避免 JS 和 Python 大括号冲突
    html_template = """
    <!DOCTYPE html>
    <html lang="zh">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>{{today_str}} 实战派情报终端</title>
        <script src="https://cdn.jsdelivr.net/npm/echarts@5.5.0/dist/echarts.min.js"></script>
        <style>
            :root {
                --bg: #0f172a;
                --card-bg: #1e293b;
                --text-main: #f1f5f9;
                --text-muted: #94a3b8;
                --accent: #38bdf8;
                --border: #334155;
            }
            body { background: var(--bg); color: var(--text-main); font-family: -apple-system, sans-serif; padding: 20px; line-height: 1.6; }
            .container { max-width: 900px; margin: auto; }
            h1 { color: var(--accent); border-bottom: 2px solid var(--border); padding-bottom: 10px; font-size: 1.8rem; }
            h2 { color: #fbbf24; margin-top: 40px; border-bottom: 1px solid var(--border); padding-bottom: 8px; font-size: 1.5rem; }
            h3 { color: #38bdf8; margin-top: 25px; font-size: 1.2rem; }
            .time { color: var(--text-muted); font-size: 0.9rem; margin-bottom: 20px; }
            
            /* 仪表盘卡片样式 */
            .dashboard-card { background: var(--card-bg); border-radius: 12px; padding: 20px; margin-top: 20px; margin-bottom: 30px; border: 1px solid var(--border); box-shadow: 0 10px 15px -3px rgba(0,0,0,0.5); }
            .gauge-container { width: 100%; height: 260px; }
            
            ol, ul { padding-left: 20px; margin-top: 20px; }
            ol li { margin-bottom: 40px; font-size: 1.1rem; border-bottom: 1px dashed var(--border); padding-bottom: 20px; }
            ol li strong { color: var(--accent); font-size: 1.3rem; }
            
            blockquote, .quote {
                background: #020617;
                border-left: 4px solid #10b981;
                padding: 12px 15px;
                margin: 12px 0;
                color: #e2e8f0;
                font-size: 0.95rem;
                font-style: normal;
                border-radius: 4px;
                line-height: 1.6;
            }
            .translation { color: #94a3b8; margin-top: 10px; font-size: 0.9rem; border-top: 1px dotted #334155; padding-top: 10px; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🎯 {{today_str}} 市场异动与情绪透视</h1>
            <p class="time">情报源头: 300+ 硬核原帖 | 最后分析时间: {{update_time}} (北京时间)</p>
            
            <div class="dashboard-card">
                <h3 style="margin-top: 0; text-align: center; color: #f8fafc; border:none;">CNN 市场恐慌与贪婪指数</h3>
                <div id="gauge" class="gauge-container"></div>
            </div>

            {{report}}
        </div>

        <script>
            var chartDom = document.getElementById('gauge');
            var myChart = echarts.init(chartDom, 'dark');
            
            // 动态决定颜色
            var score = {{fg_score}};
            var color = '#eab308'; // 默认黄色
            if (score <= 25) color = '#ef4444';      // 极度恐慌 (红)
            else if (score <= 45) color = '#f97316'; // 恐慌 (橙)
            else if (score <= 55) color = '#eab308'; // 中性 (黄)
            else if (score <= 75) color = '#84cc16'; // 贪婪 (浅绿)
            else color = '#22c55e';                  // 极度贪婪 (深绿)

            var option = {
                backgroundColor: 'transparent',
                series: [
                    {
                        type: 'gauge',
                        startAngle: 180,
                        endAngle: 0,
                        min: 0,
                        max: 100,
                        splitNumber: 4,
                        itemStyle: { color: color },
                        progress: { show: true, width: 25 },
                        pointer: { show: true, length: '50%', width: 6 },
                        axisLine: { lineStyle: { width: 25, color: [[1, '#1e293b']] } },
                        axisTick: { show: false },
                        splitLine: { length: 25, lineStyle: { width: 2, color: '#0f172a' } },
                        axisLabel: { distance: 30, color: '#94a3b8', fontSize: 14 },
                        detail: {
                            valueAnimation: true,
                            formatter: '{value}\\n{{fg_rating}}',
                            color: 'auto',
                            fontSize: 28,
                            offsetCenter: [0, '30%'],
                            lineHeight: 40
                        },
                        data: [{ value: score }]
                    }
                ]
            };
            option && myChart.setOption(option);
            window.addEventListener('resize', function() { myChart.resize(); });
        </script>
    </body>
    </html>
    """
    
    # 注入数据
    html_template = html_template.replace("{{today_str}}", today_str)
    html_template = html_template.replace("{{update_time}}", update_time)
    html_template = html_template.replace("{{report}}", report)
    html_template = html_template.replace("{{fg_score}}", str(fg_score))
    html_template = html_template.replace("{{fg_rating}}", fg_rating)
    
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html_template)

if __name__ == "__main__":
    print("1. 正在获取 CNN 恐慌与贪婪指数...")
    score, rating = get_fear_and_greed()
    print(f"当前指数: {score} ({rating})")
    
    print("2. 正在抓取七大硬核信息源...")
    data = fetch_data()
    
    print("3. Gemini 正在执行质量过滤与解析...")
    analysis = get_ai_analysis(data)
    
    print("4. 渲染仪表盘与生成网页...")
    generate_html(analysis, score, rating)
