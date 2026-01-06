import os
import re
import matplotlib.pyplot as plt
import yfinance as yf
import pandas as pd
import markdown
from src.graph import get_graph
from src.config import SystemConfig

# === 設定目標 ===
TICKER = "TSLA"
OUTPUT_DIR = "output"

def save_report(state):
    """將結果生成為 HTML (Markdown 渲染修復版)"""
    ticker = state['ticker']
    domain = f"{ticker.split('.')[0].lower()}.com"
    try:
        # 嘗試抓取比較精確的網域
        match = re.search(r'https?://(www\.)?([a-zA-Z0-9-]+\.[a-zA-Z]+)', str(state.get('market_data','')))
        if match: domain = match.group(2)
    except: pass
    
    img_src = f"https://www.google.com/s2/favicons?domain={domain}&sz=128"
    
    # 2. 使用 markdown 套件將文字轉為 HTML
    # extensions=['extra'] 可以支援表格和更豐富的格式
    raw_content = state['story_content']
    html_content = markdown.markdown(raw_content, extensions=['extra'])
    
    html = f"""
    <html>
    <head>
        <meta charset="utf-8">
        <style>
            body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; max-width: 800px; margin: 40px auto; padding: 20px; background-color: #f4f4f9; color: #333; line-height: 1.6; }} 
            .container {{ background: #ffffff; padding: 40px; border-radius: 15px; box-shadow: 0 4px 15px rgba(0,0,0,0.1); }}
            
            /* 標題樣式 */
            h1 {{ color: #2c3e50; border-bottom: 2px solid #eee; padding-bottom: 10px; }}
            h2 {{ color: #e67e22; margin-top: 30px; }}
            h3 {{ color: #2980b9; margin-top: 25px; }}
            
            /* 重點文字 */
            strong {{ color: #c0392b; }}
            
            /* 列表樣式 */
            ul {{ padding-left: 20px; }}
            li {{ margin-bottom: 8px; }}
            
            /* 頂部 Header */
            .header {{ display: flex; align-items: center; margin-bottom: 30px; }}
            .header img {{ width: 64px; height: 64px; margin-right: 20px; border-radius: 10px; }}
            .source {{ color: #7f8c8d; font-size: 0.9em; }}
            
            /* 經理結論區塊 */
            .verdict {{ background-color: #ecf0f1; padding: 15px; border-left: 5px solid #bdc3c7; margin-top: 30px; border-radius: 4px; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <img src="{img_src}" onerror="this.src='https://via.placeholder.com/64'">
                <div>
                    <h1 style="margin:0; border:none;">{ticker} Analysis Report</h1>
                    <span class="source">Source: {domain}</span>
                </div>
            </div>
            
            {html_content}
            
            <div class="verdict">
                <h3>🤵 Manager's Verdict</h3>
                <p>{state.get('final_decision')}</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    path = f"{OUTPUT_DIR}/report_{ticker}.html"
    with open(path, "w", encoding="utf-8") as f: f.write(html)
    print(f"✅ HTML Report saved: {path}")

def save_chart(ticker):
    """生成 K 線圖並存檔"""
    try:
        df = yf.Ticker(ticker).history(period="6mo")
        if df.empty: return
        df['SMA20'] = df['Close'].rolling(20).mean()
        
        plt.figure(figsize=(10,5))
        plt.plot(df.index, df['Close'], label='Close')
        plt.plot(df.index, df['SMA20'], label='SMA20', linestyle='--')
        plt.title(f"{ticker} Trend")
        plt.legend()
        plt.grid(True, alpha=0.3)
        
        path = f"{OUTPUT_DIR}/chart_{ticker}.png"
        plt.savefig(path)
        plt.close()
        print(f"✅ Chart saved: {path}")
    except: pass

if __name__ == "__main__":
    # 檢查 API Key
    if not SystemConfig.GROQ_API_KEY:
        print("❌ Error: GROQ_API_KEY not found in .env")
        exit()

    if not os.path.exists(OUTPUT_DIR): os.makedirs(OUTPUT_DIR)

    print(f"🚀 Starting Analysis for {TICKER}...")
    app = get_graph()
    
    inputs = {"ticker": TICKER, "revision_count": 0}
    final_state = inputs.copy()
    
    # 執行並顯示進度
    for output in app.stream(inputs):
        for key, val in output.items():
            if val:
                print(f"📍 Node Finished: {key}")
                if "bull_score" in val:
                    print(f"   📊 Score: Bull {val['bull_score']} | Bear {val['bear_score']}")
                final_state.update(val)

    if final_state and "story_content" in final_state:
        save_report(final_state)
        save_chart(TICKER)
        print("🎉 All tasks completed!")
    else:
        print("⚠️ Workflow ended unexpectedly.")
