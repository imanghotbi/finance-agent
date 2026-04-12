# Finance Agent

Finance Agent is a Chainlit-based multi-agent stock analysis application for Iranian market symbols. It collects market, fundamental, social, and news data, runs a LangGraph workflow of specialized analysis nodes, and produces a final investment memo.

The project also persists:

- analyzed symbol data in MongoDB
- per-node LLM usage metadata in MongoDB
- final agent reports and final workflow state in MongoDB

## What It Does

Given a stock symbol such as `فملی` or `فولاد`, the app:

1. collects market and company data from external providers
2. prepares technical, fundamental, and social/news input payloads
3. runs specialized LLM nodes for each analysis area
4. merges those outputs into consensus reports
5. generates a final report
6. optionally renders a candlestick chart at the end if `plotly` is installed

## Architecture

The application is built around a LangGraph workflow:

- `intro_agent`
  - receives the symbol from the user
- `data_preparation`
  - refreshes or loads cached symbol data from MongoDB
- `technical_graph`
  - trend
  - oscillator
  - volatility
  - volume
  - support/resistance
  - smart money
  - technical consensus
- `fundamental_graph`
  - balance sheet
  - earnings quality
  - valuation
  - codal analysis
  - fundamental consensus
- `social_news_graph`
  - twitter
  - sahamyab
  - news
  - social/news consensus
- `reporter_agent`
  - creates the final investment memo

Key entrypoints:

- [`main.py`](/Users/mac/Desktop/finance_agent/main.py): Chainlit UI entrypoint
- [`src/workflow/graph_builder.py`](/Users/mac/Desktop/finance_agent/src/workflow/graph_builder.py): LangGraph construction
- [`src/services/prepare_data.py`](/Users/mac/Desktop/finance_agent/src/services/prepare_data.py): data fetch + analysis preparation pipeline

## Project Structure

```text
.
├── main.py
├── docker-compose.yml
├── public/
├── src/
│   ├── core/
│   ├── schema/
│   ├── services/
│   │   ├── providers/
│   │   ├── technical/
│   │   └── fundamental/
│   ├── utils/
│   └── workflow/
│       └── nodes/
└── README.md
```

## Main Components

### UI

- Chainlit chat interface in [`main.py`](/Users/mac/Desktop/finance_agent/main.py)
- renders intermediate reports for technical, fundamental, and social/news stages
- sends the final memo after the graph completes
- attempts to display a Plotly candlestick chart at the end

### Data Providers

External data is collected from:

- Rahavard
- Sahamyab
- Twitter RapidAPI
- Tavily
- Codal scraping via `aiohttp` + BeautifulSoup

### Persistence

MongoDB is used for:

- cached market analysis documents
- LLM usage logs
- final agent run state and final report

### LLM Layer

- LLM creation is centralized in [`src/utils/llm_factory.py`](/Users/mac/Desktop/finance_agent/src/utils/llm_factory.py)
- models can be selected dynamically per node via config
- structured output recovery and logging live in [`src/utils/helper.py`](/Users/mac/Desktop/finance_agent/src/utils/helper.py)

## Requirements

There is no dependency manifest in the repository at the moment, so packages need to be installed manually in your environment.

Core libraries used by the project:

- `chainlit`
- `langgraph`
- `langchain-core`
- `langchain-nvidia-ai-endpoints`
- `langchain-openai`
- `pydantic`
- `pydantic-settings`
- `motor`
- `pymongo`
- `pandas`
- `aiohttp`
- `beautifulsoup4`
- `jdatetime`
- `tenacity`

Optional:

- `plotly`
  - required only if you want the final candlestick chart to render

## Configuration

Settings are loaded from `.env` via `pydantic-settings`.

Required environment variables are derived from [`src/core/config.py`](/Users/mac/Desktop/finance_agent/src/core/config.py):

```env
MONGO_ENDPOINT=localhost:27017
MONGO_DB_NAME=finance_agent
MONGO_USERNAME=your_user
MONGO_PASSWORD=your_password

RAPID_API_KEY=your_rapid_api_key
PROXY_URL=http://your-proxy-if-needed
# also supported: socks5://user:pass@127.0.0.1:1080
TAVILY_API_KEY=your_tavily_api_key

MODEL_API_KEY=your_model_api_key
MODEL_NAME=qwen/qwen3-235b-a22b
MODEL_NAME_OVERRIDES={"introduction":"qwen/qwen3-32b","technical":"qwen/qwen3-235b-a22b","fundamental":"qwen/qwen3-235b-a22b","social_news":"qwen/qwen3-32b","reporter":"qwen/qwen3-235b-a22b"}
```

Optional Mongo collection names:

```env
MONGO_COLLECTION_NAME=market_analysis
MONGO_LLM_USAGE_COLLECTION_NAME=llm_usage
MONGO_AGENT_RUN_COLLECTION_NAME=agent_runs
```

## Running MongoDB

You can start MongoDB and Mongo Express with Docker Compose:

```bash
docker compose up -d
```

Exposed services:

- MongoDB: `localhost:27017`
- Mongo Express: `http://localhost:8081`

## Running the App

Start the Chainlit application from the project root:

```bash
chainlit run main.py
```

Then open the Chainlit UI in your browser and enter a stock symbol.

## Candlestick Chart

At the end of a completed analysis run, the UI attempts to render a candlestick chart from stored OHLC history.

Notes:

- the chart is built from `price_history` stored in MongoDB
- `plotly` must be installed for rendering to work
- if `plotly` is not installed, the app skips the chart instead of crashing

## Mongo Documents

### Analysis Cache

The main market analysis collection stores items such as:

- symbol metadata
- market snapshot
- technical analysis payload
- fundamental payload
- social/news payload
- `price_history`

### LLM Usage Logs

Each LLM execution stores usage metadata similar to:

```python
{
    "node_name": "...",
    "session_id": "...",
    "model_name": "...",
    "input_tokens": ...,
    "output_tokens": ...,
    "total_tokens": ...,
    "created_at": ...
}
```

### Final Agent Runs

The final agent run collection stores:

- `session_id`
- `symbol`
- `final_report`
- `final_state`
- `updated_at`

## Notes and Limitations

- there is currently no `requirements.txt` or `pyproject.toml`
- the app depends on external APIs and valid credentials
- there are currently no automated tests in the repository
- some provider integrations may require proxy access depending on your network

## Suggested Next Improvements

- add `requirements.txt` or `pyproject.toml`
- add integration tests for graph execution
- add schema validation for Mongo documents
- add better dependency/setup automation
- add chart period selection in the UI
