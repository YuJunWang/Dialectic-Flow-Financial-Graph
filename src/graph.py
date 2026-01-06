from langgraph.graph import StateGraph, END
from .state import AgentState
from .agents import research_node, bull_agent_node, bear_agent_node, manager_node, storyteller_node
from .config import SystemConfig

# --- 路由邏輯 (Parallel Router) ---
def quality_gate(state: AgentState):
    """
    決定下一步：
    經理審核通過後，交給「說書人」製作懶人包。
    """
    bull_score = state.get("bull_score", 0)
    bear_score = state.get("bear_score", 0)
    revision_count = state["revision_count"]

    pass_threshold = SystemConfig.PASS_THRESHOLD
    max_revisions = SystemConfig.MAX_REVISIONS

    # 1. 審核通過
    if bull_score >= pass_threshold and bear_score >= pass_threshold:
        # print(f"✅ [Router] 雙方皆達高標 ({pass_threshold}+) -> 進入說書人 (Storyteller) 環節")
        return "storyteller_node" # 指向說書人

    # 2. 強制結束條件
    elif revision_count > max_revisions:
        # print("🛑 [Router] 修改次數耗盡 -> 強制進入說書人 (Storyteller) 環節")
        return "storyteller_node" # 指向說書人

    # 3. 未達標繼續寫
    else:
        # print(f"🔄 [Router] 未達標 (Bull:{bull_score}, Bear:{bear_score}) -> 打回重練")
        return ["bull_agent", "bear_agent"]

# --- 建立圖形 ---
def get_graph():
    wf = StateGraph(AgentState)
    wf.add_node("researcher", research_node)
    wf.add_node("bull_agent", bull_agent_node)
    wf.add_node("bear_agent", bear_agent_node)
    wf.add_node("manager", manager_node)
    wf.add_node("storyteller_node", storyteller_node)
    
    wf.set_entry_point("researcher")
    wf.add_edge("researcher", "bull_agent")
    wf.add_edge("researcher", "bear_agent")
    wf.add_edge("bull_agent", "manager")
    wf.add_edge("bear_agent", "manager")
    wf.add_conditional_edges("manager", quality_gate)
    wf.add_edge("storyteller_node", END)
    return wf.compile()
