import yfinance as yf
import time
from langchain_community.tools import DuckDuckGoSearchResults
from langchain_groq import ChatGroq
from .config import SystemConfig

# --- A. 模型工廠 (Model Factory) ---
def get_model(temperature=0.5, json_mode=False):
    """
    獲取 LLM 實例。取得 Groq 模型。
    """
    llm = ChatGroq(
        model_name=SystemConfig.MODEL_NAME,
        temperature=temperature
    )
    return llm

# --- B. 數據工具服務 (Data Services) ---
class ResearchService:
    """
    負責所有外部數據的獲取。
    對應架構圖中的 Infrastructure Layer。
    """
    @staticmethod
    def _sleep():
        time.sleep(0.5)

    @staticmethod
    def _format_number(num):
        """將大數字轉換為 B/T (十億/兆) 格式"""
        if num is None: return "N/A"
        if num >= 1e12:
            return f"{num / 1e12:.2f}T (兆)"
        elif num >= 1e9:
            return f"{num / 1e9:.2f}B (十億)"
        elif num >= 1e6:
            return f"{num / 1e6:.2f}M (百萬)"
        return f"{num:.2f}"

    @staticmethod
    def _format_percent(num):
        """將小數轉換為百分比"""
        if num is None: return "N/A"
        return f"{num * 100:.2f}%"

    # 技術指標工具
    @staticmethod
    def get_technicals(ticker: str) -> str:
        ResearchService._sleep()
        try:
            stock = yf.Ticker(ticker)
            hist = stock.history(period="3mo") # 抓3個月資料
            if hist.empty: return "No technical data."

            # 1. 計算簡單移動平均 (SMA 50)
            hist['SMA_50'] = hist['Close'].rolling(window=50).mean()
            current_price = hist['Close'].iloc[-1]
            sma_50 = hist['SMA_50'].iloc[-1]

            # 2. 計算 RSI (相對強弱指標)
            delta = hist['Close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs)).iloc[-1]

            trend = "Bullish (Above SMA50)" if current_price > sma_50 else "Bearish (Below SMA50)"
            rsi_signal = "Overbought (>70)" if rsi > 70 else "Oversold (<30)" if rsi < 30 else "Neutral"

            return f"RSI(14): {rsi:.2f} [{rsi_signal}], Price vs SMA50: {trend} (Price: {current_price:.2f}, SMA50: {sma_50:.2f})"
        except Exception as e:
            return f"Technical Error: {str(e)}"

    # 機構持股工具
    @staticmethod
    def get_institutional_holders(ticker: str) -> str:
        ResearchService._sleep()
        try:
            stock = yf.Ticker(ticker)
            # yfinance 有時會回傳 None，防呆
            inst_holders = stock.institutional_holders
            if inst_holders is None or inst_holders.empty:
                return "Institutional Data Not Available"

            # 抓前三大持有機構
            top_holders = inst_holders.head(3)[['Holder', 'Shares']].to_dict('records')
            holders_str = ", ".join([f"{h['Holder']}" for h in top_holders])

            # 抓機構持股比例
            major_holders = stock.major_holders
            if major_holders is not None:
                return f"Top Institutions: {holders_str}"
            return f"Top Holders: {holders_str}"

        except Exception as e:
            return "Institutional Data Error"

    # 基本面與趨勢工具
    @staticmethod
    def get_stock_data(ticker: str) -> str:
        ResearchService._sleep()
        try:
            stock = yf.Ticker(ticker)
            info = stock.info

            market_cap = ResearchService._format_number(info.get('marketCap'))
            revenue_growth = ResearchService._format_percent(info.get('revenueGrowth'))
            profit_margins = ResearchService._format_percent(info.get('profitMargins'))

            fundamentals = {
                "Current Price": info.get('currentPrice'),
                "Market Cap": market_cap,
                "Trailing PE": info.get('trailingPE'),
                "Forward PE": info.get('forwardPE'),
                "PEG Ratio": info.get('pegRatio'),
                "Revenue Growth (YoY)": revenue_growth,
                "Profit Margins": profit_margins,
                "Target Mean Price": info.get('targetMeanPrice'),
                "Recommendation": info.get('recommendationKey')
            }

            fund_str = ", ".join([f"{k}: {v}" for k, v in fundamentals.items() if v is not None])

            hist = stock.history(period="5d")
            if not hist.empty:
                latest = hist.iloc[-1]
                start = hist.iloc[0]
                change = ((latest['Close'] - start['Close']) / start['Close']) * 100
                trend_str = f"5-Day Change: {change:.2f}%"
            else:
                trend_str = "No history data."

            return f"Fundamentals: [{fund_str}]\nTrend: {trend_str}"

        except Exception as e:
            return f"Stock Data Error: {str(e)}"

    # 新聞搜尋工具
    @staticmethod
    def get_news(ticker: str) -> str:
        ResearchService._sleep()
        try:
            search = DuckDuckGoSearchResults()
            results = search.run(f"{ticker} stock revenue growth earnings analysis")
            return results[:2500]
        except Exception as e:
            return f"News Search Error: {str(e)}"

    #  身家調查 (Identity Card)
    @staticmethod
    def get_company_profile(ticker: str) -> str:
        ResearchService._sleep()
        try:
            stock = yf.Ticker(ticker)
            info = stock.info

            profile = {
                "Company Name": info.get('longName', ticker),
                "Sector": info.get('sector', 'N/A'),
                "Industry": info.get('industry', 'N/A'),
                "Summary": info.get('longBusinessSummary', 'N/A')[:250] + "...",
            }
            return str(profile)
        except Exception as e:
            return "Profile Data Error"

    # 時光機 (Time Machine / FOMO)
    @staticmethod
    def get_history_price(ticker: str) -> str:
        """抓取現在、1年前、5年前的股價，供說書人計算報酬率"""
        ResearchService._sleep()
        try:
            stock = yf.Ticker(ticker)

            # 1. 現在股價
            current_hist = stock.history(period="1d")
            if current_hist.empty: return "History Data Error"
            current_price = current_hist['Close'].iloc[-1]

            # 2. 1年前股價
            hist_1y = stock.history(period="1y")
            # 如果資料不足1年，就拿最早的那天
            price_1y = hist_1y['Close'].iloc[0] if not hist_1y.empty else current_price

            # 3. 5年前股價
            hist_5y = stock.history(period="5y")
            price_5y = hist_5y['Close'].iloc[0] if not hist_5y.empty else current_price

            return f"Current Price: {current_price:.2f}, Price 1 Year Ago: {price_1y:.2f}, Price 5 Years Ago: {price_5y:.2f}"
        except Exception as e:
            return "History Data Error"

    @staticmethod
    def search_specific(query: str) -> str:
        """根據具體查詢語句搜尋網路"""
        ResearchService._sleep()
        try:
            print(f"      🕵️‍♂️ [Dynamic Search] 正在搜尋: {query} ...")
            search = DuckDuckGoSearchResults()
            # 限制回傳長度，避免 Token 爆炸
            results = search.run(query)
            return results[:1000]
        except Exception as e:
            return f"Search Error: {str(e)}"
