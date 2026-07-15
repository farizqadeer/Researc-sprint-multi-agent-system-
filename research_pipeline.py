# research_pipeline.py
from langgraph.graph import StateGraph, END
from langchain_groq import ChatGroq 
from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import tool
from typing import TypedDict, Annotated
import operator
import requests
import os
from dotenv import load_dotenv

load_dotenv()

llm = ChatGroq(
    model="llama-3.3-70b-versatile",
    api_key=os.getenv("GROQ_API_KEY"),
    temperature=0.3,
    max_tokens=1500,
    request_timeout=30,
)

# ─────────────────────────────────────────
# SHARED STATE
# ─────────────────────────────────────────

class PipelineState(TypedDict):
    topic: str
    research_notes: str
    key_insights: str
    final_article: str
    messages: Annotated[list, operator.add]
    current_stage: str

# ─────────────────────────────────────────
# TOOLS
# ─────────────────────────────────────────

@tool
def web_search(query: str) -> str:
    """Searches the web for current information on a topic."""
    # Using a free search API — replace with Tavily or Serper in production
    try:
        response = requests.get(
            "https://api.duckduckgo.com/",
            params={"q": query, "format": "json", "no_html": "1"},
            timeout=10
        )
        data = response.json()
        results = []
        if data.get("AbstractText"):
            results.append(f"Summary: {data['AbstractText']}")
        for topic in data.get("RelatedTopics", [])[:5]:
            if isinstance(topic, dict) and topic.get("Text"):
                results.append(topic["Text"])
        return "\n".join(results) if results else f"Search completed for: {query}. No direct results. Use your training knowledge."
    except Exception as e:
        return f"Search for '{query}' returned: General information available from training data."

tools = [web_search]
llm_with_tools = llm.bind_tools(tools)

# ─────────────────────────────────────────
# NODE 1 — Researcher Agent
# ─────────────────────────────────────────

RESEARCHER_PROMPT = """You are a Senior Research Analyst.
Your job is to gather comprehensive, factual information about the given topic.

Research approach:
1. Search for current state and recent developments
2. Search for key statistics and data points
3. Search for major players and organizations involved
4. Search for challenges and controversies
5. Search for future trends

Use the web_search tool multiple times with different queries.
Compile everything into detailed, structured research notes.
Be thorough — the writer depends entirely on your research."""

def researcher_node(state: PipelineState):
    messages = [
        SystemMessage(content=RESEARCHER_PROMPT),
        HumanMessage(content=f"Research this topic thoroughly: {state['topic']}")
    ]
    
    # ReAct loop — researcher can call search multiple times
    all_messages = list(messages)
    
    for _ in range(3):  # max 3 research rounds
        response = llm_with_tools.invoke(all_messages)
        all_messages.append(response)
        
        if not response.tool_calls:
            # LLM has finished researching
            break
        
        # Execute all search calls
        for tool_call in response.tool_calls:
            result = web_search.invoke(tool_call["args"])
            all_messages.append(ToolMessage(
                content=str(result),
                tool_call_id=tool_call["id"]
            ))
    
    research_notes = all_messages[-1].content
    
    return {
        "research_notes": research_notes,
        "current_stage": "researching_done",
        "messages": [HumanMessage(content=f"Research complete for: {state['topic']}")]
    }

# ─────────────────────────────────────────
# NODE 2 — Analyst Agent
# ─────────────────────────────────────────

ANALYST_PROMPT = """You are a Data and Insights Analyst.
You receive raw research notes and extract the most important insights.

Your job:
1. Identify the 5-7 most important facts or data points
2. Find patterns or themes across the research
3. Identify what is most surprising or significant
4. Determine what a business professional most needs to know
5. Flag any conflicting information or uncertainties

Output: A structured list of key insights with brief explanations.
Be selective — quality over quantity."""

def analyst_node(state: PipelineState):
    response = llm.invoke([
        SystemMessage(content=ANALYST_PROMPT),
        HumanMessage(content=f"""
        Topic: {state['topic']}
        
        Research Notes:
        {state['research_notes']}
        
        Extract the key insights from this research.
        """)
    ])
    
    return {
        "key_insights": response.content,
        "current_stage": "analysis_done"
    }

# ─────────────────────────────────────────
# NODE 3 — Writer Agent
# ─────────────────────────────────────────

WRITER_PROMPT = """You are a Professional Content Writer specializing in business and technology.
You receive research notes and key insights, then produce a polished article.

Article structure:
1. Compelling headline
2. Executive summary (2-3 sentences)
3. Current State (what is happening now)
4. Key Data Points (statistics and facts in a readable format)
5. Key Players (who matters in this space)
6. Challenges and Considerations
7. Future Outlook
8. Conclusion with actionable takeaway

Style: Professional, clear, no jargon unless explained. 
Length: 500-700 words.
Only use facts from the research provided — never add your own knowledge."""

def writer_node(state: PipelineState):
    research_notes = state['research_notes'][:3000]
    key_insights = state['key_insights'][:1500]
    response = llm.invoke([
        SystemMessage(content=WRITER_PROMPT),
        HumanMessage(content=f"""
        Topic: {state['topic']}
        
        Research Notes:
        {state['research_notes']}
        
        Key Insights:
        {state['key_insights']}
        
        Write the complete article now.
        """)
    ])
    
    return {
        "final_article": response.content,
        "current_stage": "writing_done"
    }

# ─────────────────────────────────────────
# BUILD THE GRAPH
# ─────────────────────────────────────────

graph = StateGraph(PipelineState)

graph.add_node("researcher", researcher_node)
graph.add_node("analyst", analyst_node)
graph.add_node("writer", writer_node)

graph.set_entry_point("researcher")
graph.add_edge("researcher", "analyst")
graph.add_edge("analyst", "writer")
graph.add_edge("writer", END)

pipeline = graph.compile()

# ─────────────────────────────────────────
# RUNNER FUNCTION
# ─────────────────────────────────────────

def run_pipeline(topic: str):
    result = pipeline.invoke({
        "topic": topic,
        "research_notes": "",
        "key_insights": "",
        "final_article": "",
        "messages": [],
        "current_stage": "starting"
    })
    return {
        "topic": topic,
        "research_notes": result["research_notes"],
        "key_insights": result["key_insights"],
        "final_article": result["final_article"]
    }