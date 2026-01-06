from typing import TypedDict
from pydantic import BaseModel, Field

class AgentState(TypedDict):
    ticker: str             # 股票代碼
    market_data: str        # 搜集到的原始數據
    bull_report: str        # 多頭報告
    bear_report: str        # 空頭報告

    # 分開記錄兩者的分數與回饋
    bull_score: int
    bull_feedback: str
    bear_score: int
    bear_feedback: str

    final_decision: str     # 最終決策
    revision_count: int     # 修改次數計數器

    story_content: str

class ManagerReview(BaseModel):
    bull_score: int = Field(description="Score 0-100")
    bull_feedback: str = Field(description="Feedback")
    bear_score: int = Field(description="Score 0-100")
    bear_feedback: str = Field(description="Feedback")
    final_decision: str = Field(description="Final decision")
