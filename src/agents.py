import time
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from .config import SystemConfig
from .state import AgentState, ManagerReview
from .tools import ResearchService, get_model

# --- 定義各個節點邏輯 (Node Implementation) ---

# Search Tool of Bull & Bear
def generate_search_query(ticker, feedback, role):
    """根據 Feedback 產生搜尋關鍵字"""
    time.sleep(SystemConfig.API_DELAY / 2)
    llm = get_model(temperature=0.3)
    prompt = ChatPromptTemplate.from_template("""
    You are an expert search query engineer.
    The goal is to find **SPECIFIC NUMBERS** on DuckDuckGo to address the manager's feedback.

    **CONTEXT:**
    - Role: {role}
    - Ticker: {ticker}
    - Feedback: "{feedback}"

    **RULES FOR QUERY GENERATION:**
    1. **NO SENTENCES**: Do not write "I want to find..." or "Analysis of...".
    2. **USE KEYWORDS**: Use concise keywords. (e.g., "PE ratio", "Market Share", "Revenue").
    3. **USE COMPARISONS**: If feedback mentions "competition", search "TICKER vs COMPETITOR metric".
    4. **MAX 5 WORDS**: Keep it short. Search engines fail with long queries.

    **EXAMPLES:**
    - Bad: "Why is NVDA stock price dropping and what are the risks?" (Too long, vague)
    - Good: "NVDA vs AMD market share AI" (Targeted)
    - Good: "NVDA insider selling 2025" (Specific)
    - Good: "NVDA short interest ratio" (Data-focused)

    **OUTPUT:** Generate ONE single search query string. No quotes.
    """)
    chain = prompt | llm | StrOutputParser()
    return chain.invoke({"ticker": ticker, "feedback": feedback, "role": role})

def research_node(state: AgentState):
    """[節點 1] 研究員"""
    print(f"🔍 [System] 正在搜集 {state['ticker']} 的全方位數據...")

    # 1. 基本面
    basic_info = ResearchService.get_stock_data(state['ticker'])
    # 2. 新聞
    news_info = ResearchService.get_news(state['ticker'])
    # 3. 技術面
    tech_info = ResearchService.get_technicals(state['ticker'])
    # 4. 籌碼面
    inst_info = ResearchService.get_institutional_holders(state['ticker'])
    # 5. 身家調查
    profile_info = ResearchService.get_company_profile(state['ticker'])
    # 6. 時光機數據
    history_info = ResearchService.get_history_price(state['ticker'])

    # 組合所有數據
    combined_data = f"""
    [Company Profile]: {profile_info}
    [History Price (For Time Machine)]: {history_info}
    [Fundamental Data]: {basic_info}
    [Technical Analysis]: {tech_info}
    [Institutional Holdings]: {inst_info}
    [News Sentiment]: {news_info}
    """

    return {"market_data": combined_data, "revision_count": 0}

def bull_agent_node(state: AgentState):
    """[節點 2-A] 多頭分析師 """
    current_score = state.get("bull_score", 0)
    threshold = SystemConfig.PASS_THRESHOLD
    time.sleep(SystemConfig.API_DELAY + 0.0)

    if current_score >= threshold and state.get("bull_report"):
        print(f"📈 [Bull Agent] 上次得分 {current_score} (Pass)，直接沿用舊報告。")
        return {}

    print("📈 [Bull Agent] 正在撰寫多頭報告...")
    llm = get_model(temperature=SystemConfig.AGENT_TEMP)

    # feedback of manager and GO TO SEARCH
    feedback = state.get("bull_feedback")
    market_data = state["market_data"]

    if feedback:
        print(f"   ⚠️ 建議Bull: {feedback}")
        # A. 思考要查什麼
        query = generate_search_query(state['ticker'], feedback, "Bullish Analyst")
        # B. 執行搜尋
        new_info = ResearchService.search_specific(query)
        # C. 將新資料注入 Context
        market_data += f"\n\n### 🔍 NEW DATA FOUND (Query: '{query}'):\n{new_info}\n(USE THIS DATA TO FIX YOUR REPORT!)"
        feedback_context = f"FEEDBACK: {feedback}"
    else:
        feedback_context = "None"

    # last report
    last_report = state.get("bull_report")

    REWRITE_THRESHOLD = threshold - 5
    if last_report and current_score < REWRITE_THRESHOLD:
        report_context = "None (Write from scratch based on feedback)"
    else:
        report_context = last_report if last_report else "None (First Draft)"

    # [Bull Prompt]
    bull_prompt = ChatPromptTemplate.from_template("""
    # ROLE
    You are a **High-Conviction Growth Fund Manager**.
    You are NOT a cheerleader; you are a professional investor who sees value where others see risk.

    # OBJECTIVE
    Write a passionate bullish pitch (max 300 words) in **Traditional Chinese (繁體中文)** to convince a skeptical CIO to BUY immediately.

    ## INPUT DATA
    1. **Market Data**: {market_data}
      *(Note: Focus ONLY on Fundamental Data, Technical Analysis, and Institutional Holdings. IGNORE Company Profile/History.)*
    2. **Manager's Feedback**: {feedback_context}
    3. **Your Previous Draft**: {report_context}

    ## EXECUTION RULES (NON-NEGOTIABLE)
    1. **MANDATORY METRICS**: You **MUST** cite specific numbers from the data.
      - **Revenue Growth / Margins**: To prove business expansion.
      - **PE / PEG Ratio**: To argue why it's cheap relative to growth.
      - **RSI / SMA**: To prove momentum (e.g., "RSI < 30 is a steal", "Price > SMA is a breakout").
    2. **Handling Feedback**:
      - If `Manager's Feedback` exists, you MUST fix the specific flaws pointed out.
      - If `New Research` is found in the data, weave it into your logic (don't just paste it at the end).
    3. **Tone**: Enthusiastic, Urgent (FOMO), Confident. Use words like "Skyrocket", "Dominate", "Moat".

    ## STRUCTURE
    1. **The Hook**: A one-sentence power statement about the company's massive potential.
    2. **The Evidence**: Connect the dots using the MANDATORY METRICS. (e.g., "Revenue is up X%, proving Y...").
    3. **The Verdict**: A powerful closing statement on why buying NOW is critical.

    # OUTPUT
    (Generate the Traditional Chinese report below. Do not output pre-computation thoughts.)
    """)

    chain = bull_prompt | llm | StrOutputParser()
    report = chain.invoke({
        "ticker": state["ticker"],
        "market_data": state["market_data"],
        "feedback_context": feedback_context,
        "report_context": report_context
    })
    return {"bull_report": report}

def bear_agent_node(state: AgentState):
    """[節點 2-B] 空頭風險師 """
    current_score = state.get("bear_score", 0)
    threshold = SystemConfig.PASS_THRESHOLD
    time.sleep(SystemConfig.API_DELAY + 0.2)

    if current_score >= threshold and state.get("bear_report"):
        print(f"📉 [Bear Agent] 上次得分 {current_score} (Pass)，直接沿用舊報告。")
        return {}

    print("📉 [Bear Agent] 正在撰寫空頭報告...")
    llm = get_model(temperature=SystemConfig.AGENT_TEMP)

    # feedback of manager and GO TO SEARCH
    feedback = state.get("bear_feedback")
    market_data = state["market_data"]

    if feedback:
        print(f"   ⚠️ 建議Bear: {feedback}")
        # A. 思考要查什麼
        query = generate_search_query(state['ticker'], feedback, "Bearish Short-Seller")
        # B. 執行搜尋
        new_info = ResearchService.search_specific(query)
        # C. 注入新資料
        market_data += f"\n\n### 🔍 NEW DATA FOUND (Query: '{query}'):\n{new_info}\n(USE THIS DATA TO FIX YOUR REPORT!)"
        feedback_context = f"FEEDBACK: {feedback}"
    else:
        feedback_context = "None"

    # last report
    last_report = state.get("bear_report")
    REWRITE_THRESHOLD = threshold - 5
    if last_report and current_score < REWRITE_THRESHOLD:
        report_context = "None (Write from scratch based on feedback)"
    else:
        report_context = last_report if last_report else "None (First Draft)"

    # [Bear Prompt]
    bear_prompt = ChatPromptTemplate.from_template("""
    # ROLE
    You are a **Forensic Accountant & Short Seller**.
    You don't just hate stocks; you hate **inefficiency and bubbles**.

    # OBJECTIVE
    Write a sharp, critical risk warning (max 300 words) in **Traditional Chinese (繁體中文)** to convince a CIO to SELL or SHORT immediately.

    ## INPUT DATA
    1. **Market Data**: {market_data}
      *(Note: Focus ONLY on Fundamentals [High PE/Debt] and Technicals [RSI > 70]. IGNORE Company Profile/History.)*
    2. **Manager's Feedback**: {feedback_context}
    3. **Your Previous Draft**: {report_context}

    ## EXECUTION RULES (NON-NEGOTIABLE)
    1. **MANDATORY METRICS**: You **MUST** cite specific numbers to expose weaknesses.
      - **PE Ratio / Valuations**: To prove it's "priced for perfection".
      - **Debt / Cash Flow**: To show financial fragility.
      - **RSI > 70 / Price < SMA**: To signal "Overbought" or "Broken Trend".
    2. **Handling Feedback**:
      - If `Manager's Feedback` exists, address it directly. Use new data to strengthen your attack.
      - Never just list data; explain the **negative consequence** (e.g., "PE is 50x, meaning any miss will crash the stock").
    3. **Tone**: Cold, Ruthless, Analytical. Use words like "Bubble", "Correction", "Unsustainable".

    ## STRUCTURE
    1. **The Warning**: A blunt statement on why the market is wrong.
    2. **The Cracks**: Expose the flaws using MANDATORY METRICS. Destroy the "growth narrative".
    3. **The Trigger**: Predict what will cause the inevitable crash.

    # OUTPUT
    (Generate the Traditional Chinese report below. Do not output pre-computation thoughts.)
    """)

    chain = bear_prompt | llm | StrOutputParser()
    report = chain.invoke({
        "ticker": state["ticker"],
        "market_data": state["market_data"],
        "feedback_context": feedback_context,
        "report_context": report_context
    })
    return {"bear_report": report}

def manager_node(state: AgentState):
    """[節點 3] 基金經理"""
    threshold = getattr(SystemConfig, 'PASS_THRESHOLD', 85)

    # 1. 判斷是否需要重審
    bull_passed = state.get("bull_score", 0) >= threshold
    bear_passed = state.get("bear_score", 0) >= threshold

    print("\n🤵 [Manager] 正在審核桌上的報告...")
    time.sleep(SystemConfig.API_DELAY + 5)

    # 2. 動態準備 Prompt
    if bull_passed:
        print(f"   ⏩ Bull 已達標 ({state['bull_score']})，跳過審核。")
        bull_input_content = f"""
        [SYSTEM NOTE]: This report has ALREADY PASSED with score {state['bull_score']}.
        CONTENT UNCHANGED.
        PLEASE OUTPUT SCORE: {state['bull_score']} AND FEEDBACK: "{state['bull_feedback']}".
        """
    else:
        bull_input_content = state['bull_report']

    if bear_passed:
        print(f"   ⏩ Bear 已達標 ({state['bear_score']})，跳過審核。")
        bear_input_content = f"""
        [SYSTEM NOTE]: This report has ALREADY PASSED with score {state['bear_score']}.
        CONTENT UNCHANGED.
        PLEASE OUTPUT SCORE: {state['bear_score']} AND FEEDBACK: "{state['bear_feedback']}".
        """
    else:
        bear_input_content = state['bear_report']

    # 3. 呼叫 LLM
    llm = get_model(temperature=SystemConfig.MANAGER_TEMP)
    structured_llm = llm.with_structured_output(ManagerReview)

    rubric_text = f"""
    **Scoring Rubric:**
    - **Score > {SystemConfig.PASS_THRESHOLD} + 2 (Perfect)**:
          Perfect Causal Logic, Multiple Data Sources, Deep Insight.

    - **Score >= {SystemConfig.PASS_THRESHOLD} (Pass)**:
          Specific Data, Acceptable Logic.

    - **Score < {SystemConfig.PASS_THRESHOLD} - 2 (Fail)**:
          Data Dump, No Logic, Pure Emotion.

    **Instruction:**
    If you see [SYSTEM NOTE] saying report passed, JUST COPY that score/feedback.
    """

    manager_prompt = ChatPromptTemplate.from_template("""
    You are a Senior Chief Investment Officer (CIO).
    Your goal is to evaluate if the arguments are **LOGICALLY SOUND** and **DATA-BACKED**.
    Review reports for {ticker}.

    [Bull Report]: {bull_input}
    [Bear Report]: {bear_input}

    **Task:** Score **EACH** report separately based on the STRICT rubric below.
    """ + rubric_text + """

    **CRITICAL INSTRUCTION for 'feedback':**
    1. **DO NOT summarize.**
    2. **Be Specific**: Tell them EXACTLY what logic is missing and how to update.
    3. Keep feedback short (30-50 words).
    4. Feedback MUST be in **Traditional Chinese**(繁體中文).
    5. **Do NOT penalize "emotional tone" if the data is there.**

    Output JSON.
    """)

    chain = manager_prompt | structured_llm
    result = chain.invoke({
        "ticker": state['ticker'],
        "bull_input": bull_input_content,
        "bear_input": bear_input_content
    })

    # 4. 確保已通過的人資料不會被改變
    final_bull_score = state['bull_score'] if bull_passed else result.bull_score
    final_bull_feedback = state['bull_feedback'] if bull_passed else result.bull_feedback

    final_bear_score = state['bear_score'] if bear_passed else result.bear_score
    final_bear_feedback = state['bear_feedback'] if bear_passed else result.bear_feedback

    # print(f"   📝 評分結果 - Bull: {result.bull_score}, Bear: {result.bear_score}")
    return {
        "bull_score": result.bull_score,
        "bull_feedback": result.bull_feedback,
        "bear_score": result.bear_score,
        "bear_feedback": result.bear_feedback,
        "final_decision": result.final_decision,
        "revision_count": state["revision_count"] + 1
    }

def storyteller_node(state: AgentState):
    """[節點 4] 說書人 (負責把資料變成 IG 懶人包)"""
    print("\n🎭 [Storyteller] 正在製作 IG 財經懶人包...")
    time.sleep(SystemConfig.API_DELAY)
    llm = get_model(temperature=0.7) # 溫度高一點，讓他有創意

    # 給說書人所有的原料
    prompt = ChatPromptTemplate.from_template("""
    You are a charismatic Financial Influencer (IG/TikTok style).
    Your audience is college students and beginners (小白).

    **Input Data:**
    [Market Data]: {market_data}
    [Bull Report]: {bull_report}
    [Bear Report]: {bear_report}
    [Manager Decision]: {final_decision}

    **Task:** Create a fun, emoji-rich "Investment Survival Guide" (Traditional Chinese).

    **Structure & Content Requirements:**

    ### 1. 🗂️ 身家調查 (Identity Card)
    - Extract from [Company Profile].
    - Format:
      - **我是誰**: One sentence simple intro (e.g., "I make iPhones").
      - **產業**: Sector.

    ### 2. ⏳ 時光機 (The FOMO Machine)
    - Look at [History Price].
    - **DO NOT OUTPUT THE CALAULATION PROCESS**
    - **Calculation**: Calculate the return if I invested **100,000 TWD** 5 years ago.
    - Formula: (Current - Price_5y) / Price_5y * 100,000 + 100,000.
    - **Visual**: "If you bought 5 years ago... 100K -> [Result] TWD! 💸"
    - **Analogy**: "That's worth [X] iPhone 17!" (Assume iPhone = 30k TWD).

    ### 3. 🌤️ 股市氣象台 (Market Weather)
    - Look at [Technical Analysis] (RSI, SMA).
    - **Rules**:
      - RSI > 70: 🔥 "Heatwave (Overbought)" - Warning: Don't touch, it's hot!
      - RSI < 30: 🥶 "Freezing (Oversold)" - Opportunity: Diamonds in the snow.
      - SMA Uptrend: ☀️ "Sunny (Uptrend)" - Good vibes.
    - Give a weather forecast status.

    ### 4. 🏷️ 超市比價王 (Price Tag)
    - Look at [Fundamental Data] (PE Ratio).
    - **Rules**:
      - PE > 50: 💎 "Hermès (Luxury)" - Expensive but premium.
      - PE < 15: 🏷️ "Outlet (Discount)" - Cheap, maybe flawed?
      - PE 15-50: 🛒 "Department Store (Fair)".
    - Give the verdict.

    ### 5. 🥊 多空擂台賽 (The Battle)
    - Summarize Bull vs Bear arguments into a dialogue.
    - 🔴 **熱血哥**: (One punchy sentence from Bull Report)
    - 🔵 **冷淡哥**: (One punchy sentence from Bear Report)
    - ⚖️ **裁判**: (Manager's Decision - Buy/Sell/Hold)

    **Tone:** Fun, engaging, use many emojis. NO complex jargon without explanation.
    """)

    chain = prompt | llm | StrOutputParser()
    result = chain.invoke({
        "market_data": state["market_data"], # 這裡面現在有歷史股價和 Profile
        "bull_report": state.get("bull_report"),
        "bear_report": state.get("bear_report"),
        "final_decision": state.get("final_decision")
    })

    return {"story_content": result}
