# Researc-sprint-multi-agent-system-
# AI Research Pipeline — Multi-Agent System

An intelligent research automation system built with LangGraph, LangChain, and Llama 3.3 70B via Groq API. Three specialized AI agents — Researcher, Analyst, and Writer — collaborate autonomously to transform any topic into a polished, professional research report. The entire pipeline runs fully automated from a single user input, requiring zero manual intervention between agents.

## What This Project Does

The user opens the web interface, types any research topic, and clicks Generate Report. The system immediately starts a background pipeline where three AI agents work in sequence. The Researcher Agent uses a ReAct loop to search the web multiple times with different queries, adapting its search strategy based on what it finds at each step. Once research is complete, the Analyst Agent reads all the gathered notes and distills them into the 5 to 7 most important insights a business professional needs to know. Finally the Writer Agent receives both the raw research and the extracted insights, then produces a polished 500 to 700 word article structured with a compelling headline, executive summary, current state analysis, key data points, key players, challenges, future outlook, and an actionable conclusion. The result appears in a three-tab interface showing the Final Article, Key Insights, and Raw Research Notes separately.

## Tech Stack

This project is built on LangGraph for multi-node pipeline orchestration and typed state management, LangChain for LLM abstraction and tool binding, Llama 3.3 70B running on Groq's custom LPU hardware for free ultra-fast inference, Flask as the lightweight web server, Python threading for non-blocking pipeline execution, and the DuckDuckGo API for free web search inside the researcher agent. No paid API keys are required beyond the free Groq account.

## Architecture

The core of the project is a LangGraph StateGraph with three nodes connected by fixed edges in sequence — researcher to analyst to analyst to writer to END. A shared typed dictionary called PipelineState travels through all three nodes carrying six fields: topic, research_notes, key_insights, final_article, messages, and current_stage. Each node reads only the fields it needs and writes only the fields it owns, with LangGraph automatically preserving all other fields unchanged between nodes.

The Researcher node contains its own internal ReAct loop managed by a Python for loop limited to 3 rounds. In each round the LLM decides whether to call the web_search tool or stop. When it calls the tool, the search result is appended to the message list and fed back to the LLM in the next round. When the LLM returns a plain text response with no tool calls, the loop breaks and the research notes are saved to State. This internal loop keeps the graph clean at the high level while still allowing multiple iterative searches.

The Flask server runs the pipeline in a background thread so the UI never freezes during the 60 to 90 second execution. When the browser submits a topic, Flask immediately returns a unique job ID and the pipeline starts in the background. The browser polls the /status/job_id endpoint every 4 seconds to check progress. A watchdog thread runs in parallel and automatically marks any job as failed if it exceeds 3 minutes, preventing infinite hangs caused by rate limits.

Prompt length management is implemented in the writer node to prevent token overflow on Groq's free tier. Research notes are trimmed to 3000 characters and key insights to 1500 characters before being passed to the writer, keeping every API call within safe token limits while preserving all important information.

## Setup

First clone the repository and navigate into the project folder. Create a virtual environment with python -m venv venv and activate it with venv\Scripts\activate on Windows or source venv/bin/activate on Mac and Linux. You should see (venv) at the start of your terminal line confirming activation. Install all dependencies with pip install -r requirements.txt.

To get your free Groq API key, go to console.groq.com, sign up with no credit card required, click API Keys in the left sidebar, click Create API Key, and copy the key which starts with gsk_. Create a .env file in your project root and add GROQ_API_KEY=your_key_here. Finally run python main.py and open http://localhost:5002 in your browser.

## Troubleshooting

If the pipeline hangs for more than 3 minutes, the watchdog thread will automatically cancel the job. Try a shorter and more specific topic since broad topics generate longer research notes that can hit Groq's token-per-minute rate limit on the free tier. If you get ModuleNotFoundError for langchain_groq, your virtual environment is not activated — run the activation command again then pip install -r requirements.txt. If port 5002 is already in use, change the port number in the last line of main.py to any other number like 5003.

## Why These Technical Choices

LangGraph was chosen over CrewAI because it gives explicit, traceable control over state management and node transitions. Every data transfer between agents is visible in the typed PipelineState dictionary with no hidden magic. Groq was chosen over OpenAI and Anthropic because it provides genuinely free access to Llama 3.3 70B with no credit card, making this project fully reproducible by anyone who clones the repository. The polling architecture was chosen over WebSockets because it is simpler to implement, requires no additional dependencies, and is reliable enough for a pipeline that runs once per request.

## Author

M. Fariz Qadeer — AI Engineer
LinkedIn: linkedin.com/in/farizqadeer

## License

MIT License — free to use, modify, and distribute.
