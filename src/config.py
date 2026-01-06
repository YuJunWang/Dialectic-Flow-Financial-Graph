import os
from dotenv import load_dotenv

# 載入環境變數
load_dotenv()

class SystemConfig:
    GROQ_API_KEY = os.getenv("GROQ_API_KEY")

    PASS_THRESHOLD = 88  # 及格門檻
    MAX_REVISIONS = 3    # 最大修改次數
    MANAGER_TEMP = 0.1   # 經理的溫度
    AGENT_TEMP = 0.7     # 分析師的溫度

    API_DELAY = 10
    MODEL_NAME = "meta-llama/llama-4-maverick-17b-128e-instruct"
    # qwen/qwen3-32b
    # llama-3.3-70b-versatile
    # openai/gpt-oss-120b
    # meta-llama/llama-4-maverick-17b-128e-instruct
