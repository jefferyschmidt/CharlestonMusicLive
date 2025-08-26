# MusicLive - Multi-Site Live Music Event Collector

A BMAD (Business Analysis → Modeling → Architecture → Development) approach to building a web scraper that collects data for live music events across multiple geographic regions.

## Current Status: Complete BMAD Agent System ✅

The project has completed the full BMAD pipeline with automated agents for each stage of development.

## What's Built

### ✅ Complete BMAD Agent System

- **BA Agent** (`orchestrator/run_ba.py`): Generates PRD, Stories, and Glossary
- **DB Modeler** (`orchestrator/run_db_modeler.py`): Creates database schema and migrations
- **Architect Agent** (`orchestrator/run_architect.py`): Designs system architecture and patterns
- **Developer Agent** (`orchestrator/run_developer.py`): Implements features from requirements
- **Tester Agent** (`orchestrator/run_tester.py`): Runs tests and validates functionality
- **Deployer Agent** (`orchestrator/run_deployer.py`): Handles deployment and infrastructure
- **Master Orchestrator** (`orchestrator/run_bmad_pipeline.py`): Coordinates all agents in sequence

### ✅ Core Components

#### Collector & Extractors
- **Base Extractor Interface**: `ExtractResult` dataclass with normalized event fields
- **Sample Venue Extractor**: Functional parser using Selectolax for HTML parsing
- **Collector CLI**: Command-line tool for parsing fixtures and testing extractors

#### API (FastAPI)
- **Health Check**: Root endpoint with status
- **Venues API**: `GET /api/v1/sites/{site_slug}/venues` with search and pagination
- **Events API**: `GET /api/v1/sites/{site_slug}/events` with date/venue filtering
- **Admin Dashboard**: `GET /admin/status` for system health and metrics

#### Database
- **Schema**: Complete PostgreSQL schema with venues, events, attribution, raw artifacts, and geocoding cache
- **Migrations**: Flyway-based migrations for version control
- **Connection**: Neon PostgreSQL with connection pooling

## Quick Start

### Prerequisites
- Python 3.11+
- Poetry for dependency management
- PostgreSQL database (Neon recommended)
- Anthropic API key for AI agents

### Installation
```bash
# Install dependencies
poetry install --no-root

# Set up environment variables
cp .env.example .env
# Edit .env with your DATABASE_URL and ANTHROPIC_API_KEY
```

### Using the BMAD Agents

#### Individual Agents
```bash
# Business Analysis
poetry run python orchestrator/run_ba.py

# Database Modeling
poetry run python orchestrator/run_db_modeler.py

# Architecture Design
poetry run python orchestrator/run_architect.py

# Code Generation
poetry run python orchestrator/run_developer.py

# Testing & Validation
poetry run python orchestrator/run_tester.py

# Deployment Planning
poetry run python orchestrator/run_deployer.py
```

#### Complete BMAD Pipeline
```bash
# Run the complete pipeline (all agents in sequence)
poetry run python orchestrator/run_bmad_pipeline.py

# Options:
# - Select specific agents to run
# - Choose pipeline mode (full, interactive, dry run)
# - Skip agents if outputs already exist
```

### Running Tests
```bash
# Run all tests
poetry run pytest tests/ -v

# Run specific test categories
poetry run pytest tests/test_extractor_sample_venue.py -v
poetry run pytest tests/test_api_endpoints.py -v
```

### Using the Collector CLI
```bash
# Parse a sample HTML fixture
poetry run python collector/cli.py parse tests/fixtures/sample_venue/event_page.html \
  --site charleston \
  --source "https://example.com/sample-venue/events"

# Output as summary instead of JSON
poetry run python collector/cli.py parse tests/fixtures/sample_venue/event_page.html \
  --site charleston \
  --source "https://example.com/sample-venue/events" \
  --format summary
```

### Running the API
```bash
# Start the FastAPI server
poetry run uvicorn api.main:app --reload --port 8000

# Test endpoints
curl "http://localhost:8000/"
curl "http://localhost:8000/admin/status"
curl "http://localhost:8000/api/v1/sites/charleston/venues"
curl "http://localhost:8000/api/v1/sites/charleston/events"
```

## Project Structure

```
musiclive/
├── api/                    # FastAPI application
│   ├── main.py            # Main API with endpoints
│   └── templates/         # Jinja2 templates (future)
├── collector/             # Data collection system
│   ├── cli.py            # Command-line interface
│   └── extractors/       # HTML/JSON parsers
│       ├── base.py       # Extractor interface
│       └── sample_venue.py # Sample implementation
├── db/                    # Database schema and migrations
│   ├── migrations/        # Flyway SQL migrations
│   └── flyway.conf       # Flyway configuration
├── orchestrator/          # BMAD orchestration agents
│   ├── agents.py         # Agent definitions and configurations
│   ├── run_ba.py         # Business Analysis runner
│   ├── run_db_modeler.py # Database modeling runner
│   ├── run_architect.py  # Architecture design runner
│   ├── run_developer.py  # Code generation runner
│   ├── run_tester.py     # Testing and validation runner
│   ├── run_deployer.py   # Deployment planning runner
│   ├── run_bmad_pipeline.py # Master pipeline orchestrator
│   └── run_ba_questions.py # Requirements gathering
├── tests/                 # Test suite
│   ├── fixtures/          # Golden test data
│   ├── test_api_*.py     # API endpoint tests
│   ├── test_extractor_*.py # Extractor tests
│   └── test_db_schema.py # Database schema tests
└── docs/                  # Project documentation
    ├── PRD.md            # Product Requirements Document
    ├── Stories.md        # User story backlog
    └── Glossary.md       # Domain terminology
```

## BMAD Agent Capabilities

### 🤖 BA Agent
- Generates comprehensive PRD from project context
- Creates prioritized user story backlog with acceptance criteria
- Builds domain glossary and terminology
- Outputs: `docs/PRD.md`, `docs/Stories.md`, `docs/Glossary.md`

### 🏗️ Architect Agent
- Reviews current system architecture and patterns
- Designs new system components and establishes coding patterns
- Provides scalability and maintainability recommendations
- Outputs: `architectural_analysis_*.md`

### 👨‍💻 Developer Agent
- Analyzes existing codebase patterns and follows them exactly
- Generates complete, working implementation code
- Creates comprehensive tests for new functionality
- Outputs: `generated_implementation_*.py`, `generated_tests_*.py`

### 🧪 Tester Agent
- Runs full test suite or specific tests
- Analyzes test coverage and identifies gaps
- Validates code quality (linting, formatting)
- Generates comprehensive test reports
- Outputs: `test_report_*.txt`

### 🚀 Deployer Agent
- Reviews current deployment setup
- Creates CI/CD pipeline configurations
- Sets up Docker and infrastructure
- Configures monitoring and logging
- Outputs: `deployment_plan_*.md`

### 🎯 Master Orchestrator
- Coordinates all agents in sequence
- Manages agent handoffs and context passing
- Provides pipeline configuration options
- Generates comprehensive pipeline reports
- Outputs: `bmad_pipeline_report_*.md`

## Next Steps

### Immediate (BMAD Automation Complete)
1. ✅ **Complete Agent System**: All BMAD agents built and functional
2. ✅ **Pipeline Orchestration**: Master orchestrator coordinates entire workflow
3. ✅ **Sample Implementation**: Working extractor, API, and CLI

### Short Term
1. **Real Venue Extractors**: Use Developer Agent to generate extractors for actual Charleston venues
2. **Persistence Layer**: Use Developer Agent to connect extractors to database storage
3. **Rate Limiting**: Use Developer Agent to add politeness controls and robots.txt handling
4. **Raw Artifact Storage**: Use Developer Agent to implement R2/S3 storage

### Medium Term
1. **Geocoding Integration**: Use Developer Agent to connect to Geoapify
2. **Deduplication**: Use Developer Agent to implement cross-source event matching
3. **Admin UI**: Use Developer Agent to expand dashboard functionality
4. **Monitoring**: Use Developer Agent to add structured logging and metrics

## Architecture Decisions

- **DB-First**: Schema controlled by Flyway migrations, no ORM
- **UTC Storage**: All event times stored as UTC with timezone metadata
- **Source Attribution**: Every event links to its original source and ingest run
- **Fixture-Based Testing**: Deterministic tests using recorded HTML/JSON data
- **Multi-Site Ready**: Single database with site_id dimension for future expansion
- **BMAD Automation**: Complete development pipeline automated through AI agents

## Contributing

1. **Use the BMAD Pipeline**: Leverage the automated agents for development
2. **Follow Established Patterns**: Use Architect Agent to review and establish patterns
3. **Generate Tests**: Use Developer Agent to create comprehensive test coverage
4. **Validate Quality**: Use Tester Agent to ensure code quality and test coverage

## License

[Add your license here]

## 🕷️ **Intelligent Discovery System**

The MusicLive system includes an **intelligent discovery engine** that automatically finds venue calendars and event sources without manual configuration. This makes the system truly self-discovering and scalable.

### **How It Works**

#### **1. Multi-Strategy Source Discovery**
The system uses multiple strategies to find event sources:

- **🔍 Search Engine Discovery**: Searches Google/DuckDuckGo for "Charleston live music events calendar"
- **📊 Aggregator Discovery**: Scrapes known platforms like Eventbrite, Bandsintown, Songkick
- **🔗 Cross-Reference Discovery**: Follows links from discovered sources to find new venues
- **🏢 Business Directory Discovery**: Searches Yelp, Google Business, local chamber sites

#### **2. Intelligent Source Analysis**
Each discovered source is automatically analyzed using:

- **Calendar Detection**: Identifies event calendars, date pickers, and scheduling elements
- **Event Content Analysis**: Detects event-related keywords and patterns
- **Venue Type Classification**: Categorizes as concert venue, bar, restaurant, outdoor, etc.
- **JavaScript Requirement Detection**: Identifies if Playwright is needed for dynamic content
- **Confidence Scoring**: Assigns 0.0-1.0 confidence based on multiple factors

#### **3. Adaptive Extractor Selection**
The system automatically chooses the best extractor for each source:

- **Exact Matches**: Uses specialized extractors for known venues (e.g., Music Farm)
- **Pattern Matching**: Selects extractors based on venue type and structure
- **Learning & Adaptation**: Improves selection based on successful extractions
- **Fallback Strategies**: Uses generic extractors for unknown venue types

### **Using the Intelligent Crawler**

#### **Command Line Interface**
```bash
# Discover and crawl sources for Charleston
poetry run python collector/cli.py discover \
  --site charleston \
  --city "Charleston" \
  --state "SC" \
  --max-sources 20

# This will:
# 1. Search for Charleston live music venues
# 2. Analyze each discovered source
# 3. Choose appropriate extractors
# 4. Crawl and extract events
# 5. Store everything in the database
```

#### **Programmatic Usage**
```python
from collector.intelligent_crawler import run_intelligent_crawl

# Run a full crawl session
async def crawl_charleston():
    session = await run_intelligent_crawl("charleston", "Charleston", "SC")
    print(f"Discovered {session.sources_discovered} sources")
    print(f"Crawled {session.sources_crawled} sources")
    print(f"Found {session.total_events_found} events")
    print(f"Success rate: {session.successful_crawls}/{session.sources_crawled}")

# Run the crawler
asyncio.run(crawl_charleston())
```

### **Discovery Strategies**

#### **Search Engine Discovery**
```python
# Automatically searches for:
search_terms = [
    '"Charleston SC" "live music" "events calendar"',
    '"Charleston SC" "concert venue" "upcoming shows"',
    '"Charleston SC" "music venue" "tickets"',
    '"Charleston SC" "bar live music" "schedule"',
    '"Charleston SC" "restaurant live music" "events"'
]
```

#### **Known Aggregator Discovery**
```python
# Automatically checks:
aggregators = [
    "https://www.eventbrite.com/d/charleston--sc/live-music/",
    "https://www.bandsintown.com/?location=charleston%2Csc",
    "https://www.songkick.com/search?query=charleston%2Csc",
    "https://www.jambase.com/place/charleston-sc"
]
```

#### **Cross-Reference Discovery**
```python
# Follows relevant links from discovered sources:
relevant_keywords = [
    'events', 'calendar', 'shows', 'concerts', 'tickets',
    'venue', 'club', 'theater', 'bar', 'restaurant'
]
```

### **Venue Type Detection**

The system automatically categorizes venues based on content analysis:

#### **Concert Venues**
- **Indicators**: "concert", "venue", "theater", "amphitheater", "arena"
- **Characteristics**: Ticketing systems, detailed event calendars, artist information
- **Extractor**: Specialized concert venue extractor with advanced parsing

#### **Bar Venues**
- **Indicators**: "bar", "pub", "tavern", "lounge", "club"
- **Characteristics**: Drink menus, live music schedules, entertainment info
- **Extractor**: Bar-focused extractor with flexible time parsing

#### **Restaurant Venues**
- **Indicators**: "restaurant", "cafe", "bistro", "grill", "kitchen"
- **Characteristics**: Food menus, special events, dinner shows
- **Extractor**: Restaurant event extractor with food-related parsing

#### **Outdoor Venues**
- **Indicators**: "park", "plaza", "square", "beach", "outdoor"
- **Characteristics**: Weather-dependent scheduling, seasonal events
- **Extractor**: Outdoor venue extractor with weather considerations

### **Calendar Detection**

The system automatically identifies event calendars using multiple methods:

#### **HTML Structure Analysis**
```python
calendar_elements = [
    'calendar', 'datepicker', 'month', 'week', 'day',
    'event-calendar', 'schedule', 'upcoming', 'events'
]
```

#### **Date Pattern Recognition**
```python
date_patterns = [
    r'\b(?:january|february|march|april|may|june|july|august|september|october|november|december)\s+\d{1,2}',
    r'\b(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)\s+\d{1,2}',
    r'\d{1,2}/\d{1,2}/\d{4}',
    r'\d{4}-\d{2}-\d{2}',
    r'\b(?:today|tomorrow|this week|next week)\b'
]
```

#### **Event Indicator Detection**
```python
event_indicators = [
    'doors', 'show starts', 'performance',
    'buy tickets', 'rsvp', 'get tickets'
]
```

### **Learning & Adaptation**

The system continuously learns and improves:

#### **Successful Pattern Learning**
- Tracks which extractors work best for which venue types
- Builds a mapping of domains to successful extractors
- Improves confidence scoring based on extraction success

#### **Failed Pattern Analysis**
- Identifies common failure patterns
- Avoids similar problematic sources in future crawls
- Suggests improvements to extractors

#### **Performance Metrics**
```python
extraction_stats = {
    'total_attempts': 150,
    'successful_extractions': 120,
    'failed_extractions': 30,
    'success_rate': 0.8,
    'events_per_source': 8.5
}
```

### **Rate Limiting & Politeness**

The system is designed to be respectful of websites:

#### **Automatic Rate Limiting**
- Configurable delays between requests (default: 1 second)
- Respects robots.txt when available
- User-agent identification as MusicLiveBot

#### **Error Handling**
- Graceful handling of network errors
- Retry logic for temporary failures
- Comprehensive error logging and reporting

### **Configuration Options**

#### **Discovery Limits**
```python
crawler = IntelligentCrawler("charleston", "Charleston", "SC")
crawler.max_sources_to_discover = 50      # Sources to discover
crawler.max_sources_to_crawl = 20         # Sources to actually crawl
crawler.min_confidence_threshold = 0.4    # Minimum confidence to crawl
crawler.rate_limit_delay = 1.0            # Seconds between requests
```

#### **Source Prioritization**
```python
# High priority: Venues with high confidence and calendar detection
high_priority = [s for s in sources if s.confidence_score > 0.7 and s.calendar_detected]

# Medium priority: Known aggregators and ticketing platforms
medium_priority = [s for s in sources if s.source_type in ['ticketing', 'aggregator'] and s.confidence_score > 0.5]

# Lower priority: Other sources above threshold
other_sources = [s for s in sources if s not in prioritized and s.confidence_score > threshold]
```

### **Example Discovery Results**

```json
{
  "discovery": {
    "sources": [
      {
        "url": "https://musicfarm.com/events",
        "name": "Music Farm Charleston",
        "source_type": "venue",
        "confidence_score": 0.95,
        "venue_name": "Music Farm Charleston",
        "calendar_detected": true,
        "event_count": 12,
        "requires_browser": false
      },
      {
        "url": "https://www.eventbrite.com/d/charleston--sc/live-music/",
        "name": "Charleston Live Music Events",
        "source_type": "ticketing",
        "confidence_score": 0.88,
        "venue_name": null,
        "calendar_detected": true,
        "event_count": 45,
        "requires_browser": false
      }
    ],
    "total_discovered": 23,
    "discovery_method": "multi_strategy",
    "execution_time": 45.2
  },
  "crawl": {
    "sources_crawled": 20,
    "total_events_found": 156,
    "successful_crawls": 18,
    "failed_crawls": 2,
    "success_rate": 0.9
  }
}
```

### **Benefits of Intelligent Discovery**

1. **🔄 Zero Configuration**: No need to manually specify venue websites
2. **📈 Automatic Scaling**: Discovers new venues as they appear
3. **🧠 Smart Learning**: Improves over time based on success patterns
4. **🌍 Geographic Expansion**: Easy to add new cities and regions
5. **⚡ Real-time Updates**: Continuously finds and crawls new sources
6. **🎯 Quality Filtering**: Only crawls high-confidence sources
7. **🛡️ Polite Crawling**: Respects websites and rate limits

### **Future Enhancements**

- **Machine Learning**: Train models on successful extraction patterns
- **Social Media Integration**: Discover events from Facebook, Instagram, Twitter
- **Email Newsletter Parsing**: Extract events from venue newsletters
- **API Integration**: Connect to venue APIs for real-time data
- **Geographic Clustering**: Group venues by neighborhood/area
- **Event Deduplication**: Identify and merge duplicate events across sources

---

**The intelligent discovery system makes MusicLive truly autonomous - it finds venues, learns their structure, and extracts events without any manual intervention!** 🚀✨
