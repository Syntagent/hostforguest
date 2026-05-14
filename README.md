# TouristGuideLocal - Croatian Tourism Host Platform

For server setup and GitHub distribution steps, see [DEPLOYMENT.md](DEPLOYMENT.md).

**Archon Project ID:** 715a62d5-5d7d-4eb8-9294-554424590dcd

A **B2B SaaS platform** for Croatian tourist hosts (Airbnb hosts, villa owners, apartment rentals) that enables them to offer **personalized, AI-powered local guide services** to their guests. The platform creates enhanced guest experiences and additional revenue streams for hosts.

## ðŸŒŸ Key Features

### For Croatian Tourist Hosts
- **Host Dashboard**: Manage current guest groups and local knowledge
- **Real-time Tourism Data**: Automatic updates from Croatian tourism sources using **Archon's Knowledge Base**
- **Local Content Management**: Add insider tips and hidden gems
- **Guest Group Management**: Create temporary access codes for guests
- **Business Partner Integration**: Connect with local restaurants and activities

### For Guest Groups  
- **Simple Group Onboarding**: Code-based access from host
- **AI-Powered Personalized Recommendations**: Based on group preferences
- **Real-time Information**: Live updates on attractions, events, and opening hours
- **Collaborative Group Planning**: Group voting and shared itinerary planning
- **Multi-language Support**: Croatian, English, German, Italian

### ðŸš€ Enhanced: Real-time Data Integration with Archon

The platform now features **unified real-time data integration** using Archon's existing crawler and knowledge base infrastructure:

#### Why Archon Over Crawl4AI?
- âœ… **No Duplicate Infrastructure**: Leverages existing Archon crawler instead of adding Crawl4AI
- âœ… **Unified Knowledge Base**: Single source of truth for all data
- âœ… **Better Resource Utilization**: No need for separate scraping infrastructure  
- âœ… **Integrated Workflow**: Seamless integration with existing Archon project management
- âœ… **Cost Effective**: Reduces infrastructure complexity and maintenance overhead

#### Real-time Features via Archon
- **Live Tourism Updates**: Queries Archon's knowledge base for Croatian tourism information
- **Intelligent Content Processing**: Uses Archon's RAG capabilities for content extraction
- **Smart Content Detection**: Automatic categorization of events, attractions, opening hours, and prices
- **Croatian Language Support**: Native Croatian content processing through Archon
- **Streaming Data Feeds**: Real-time updates leveraging Archon's infrastructure

#### Supported Croatian Tourism Sources
- **Croatia Tourism Board** (croatia.hr) - Available in Archon's knowledge base
- **Istria Tourism** (istra.hr) - Regional coverage through Archon
- **Kvarner Tourism** (kvarner.hr) - Lovran area focus via Archon
- **Local Tourism Offices** - Integrated through Archon's crawler

#### API Endpoints for Archon-based Real-time Data
```
# Primary Archon-based endpoints (recommended)
GET /api/v1/archon-realtime/updates          # Get recent tourism updates via Archon
GET /api/v1/archon-realtime/stream           # Live streaming data feed via Archon
GET /api/v1/archon-realtime/summary          # Archon data availability summary
POST /api/v1/archon-realtime/refresh         # Manual Archon data refresh
GET /api/v1/archon-realtime/archon/sources   # Available Archon sources
POST /api/v1/archon-realtime/archon/query    # Direct Archon knowledge base query

# Legacy Crawl4AI endpoints (for comparison)
GET /api/v1/realtime/updates                 # Get updates via Crawl4AI
GET /api/v1/realtime/stream                  # Stream via Crawl4AI
GET /api/v1/realtime/sources/status          # Crawl4AI source status
```

## ðŸ—ï¸ Technology Stack

### Core Technologies
- **Backend**: FastAPI (Python 3.9+)
- **Real-time Data**: **Archon Knowledge Base** - Unified crawler and data infrastructure
- **Database Architecture**:
  - **PostgreSQL with pgvector**: Primary database (relational + vector + spatial)
  - **Neo4j**: Graph relationships and partnership networks
- **AI & Machine Learning**: OpenAI, Google Gemini, Sentence Transformers
- **Data Validation**: Pydantic
- **Testing**: Pytest with comprehensive async support

### Enhanced Data Integration Stack
- **Archon Knowledge Base**: Primary data source with existing crawler infrastructure
- **Intelligent Content Processing**: RAG-based content extraction and analysis
- **Unified Infrastructure**: Single system for both project management and data collection
- **Smart Query Building**: Dynamic query generation for Croatian tourism content
- **Real-time Processing**: Leverages Archon's existing real-time capabilities

## ðŸ‡­ðŸ‡· Focus: Lovran Area, Croatia

**Primary Location**: Lovran, Croatia (Istrian Peninsula)  
**Coverage**: Opatija, Rijeka, Pula, Rovinj, UÄka Nature Park  
**First Host**: Apartment at OpriÄ‡ 71, Lovran 51450

### Local Attractions Database
- **Historic & Cultural**: Lovran Old Town, Opatija Riviera, Pula Arena
- **Natural Experiences**: UÄka Nature Park, Lungomare promenade, hidden beaches  
- **Food & Wine**: Marun (chestnuts), Lovran cherries, Istrian wines
- **Activities**: Boat trips, wine tastings, hiking, cultural events

## ðŸš€ Quick Start

### Prerequisites
- Python 3.9+
- PostgreSQL with pgvector extension
- Neo4j database
- Virtual environment
- **Archon Integration**: Existing Archon project setup

### Installation

1. **Clone and setup**:
```bash
git clone <repository-url>
cd TouristGuideLocal
python -m venv venv
```

2. **Activate virtual environment**:
```bash
# Windows
venv\Scripts\activate

# Linux/Mac  
source venv/bin/activate
```

3. **Install dependencies**:
```bash
pip install -r requirements.txt
```

4. **Environment setup**:
```bash
cp env.example .env
# Edit .env with your database credentials and API keys
# Note: Crawl4AI dependency is optional since we use Archon
```

5. **Initialize databases**:
```bash
# PostgreSQL setup (with pgvector)
# Neo4j setup
# Run database migrations
```

### Running the Application (local development)

1. **Databases** (Postgres + Neo4j, once per boot):
```bash
docker compose up -d
```

2. **API + Next.js** (hot reload; from repo root):
```bash
npm install
npm run dev
```
Open **http://127.0.0.1:3055** for the app. API: **http://127.0.0.1:8000**, docs at **http://127.0.0.1:8000/api/v1/docs**.

3. **Optional:** `python start.py` if you use that entrypoint instead of uvicorn directly.

4. **Access the API**:
- **API Documentation (OpenAPI)**: http://127.0.0.1:8000/api/v1/docs
- **Archon Real-time Data Health**: http://localhost:8000/api/v1/archon-realtime/health
- **Archon Tourism Updates**: http://localhost:8000/api/v1/archon-realtime/updates

### Testing Archon Integration

```bash
# Run all tests
pytest

# Test Archon integration specifically
pytest tests/test_archon_realtime.py -v

# Test Archon vs Crawl4AI comparison
pytest tests/test_archon_realtime.py::TestArchonIntegrationComparison -v

# Test legacy Crawl4AI integration
pytest tests/test_crawl4ai_realtime.py -v
```

## ðŸ“‹ Development Workflow

### Archon Integration
All development follows the **unified Archon workflow**:

1. **Check Current Task**: Review task details in Archon
2. **Research**: Use Archon's knowledge base for documentation
3. **Implement**: Leverage Archon's existing infrastructure
4. **Test**: Create comprehensive tests for Archon integration
5. **Update**: Mark task progress in Archon

### Data Integration Approaches

**ðŸŽ¯ Recommended: Archon-based Integration**
```bash
# Query Archon's knowledge base directly
curl "http://localhost:8000/api/v1/archon-realtime/updates?city=Lovran"

# Get live stream via Archon
curl "http://localhost:8000/api/v1/archon-realtime/stream?regions=Istria"

# Check available Archon sources
curl "http://localhost:8000/api/v1/archon-realtime/archon/sources"
```

**ðŸ“‹ Alternative: Crawl4AI Integration (for comparison)**
```bash
# Traditional Crawl4AI approach
curl "http://localhost:8000/api/v1/realtime/updates?city=Lovran"

# Crawl4AI source status
curl "http://localhost:8000/api/v1/realtime/sources/status"
```

## ðŸ§ª Testing

### Test Coverage
- **Unit Tests**: All services and models
- **Integration Tests**: API endpoints and database operations
- **Archon Integration Tests**: Knowledge base queries and data processing
- **Comparison Tests**: Archon vs Crawl4AI performance and features
- **Performance Tests**: Concurrent request handling

### Running Tests
```bash
# All tests
pytest

# Specific test categories
pytest tests/test_archon_realtime.py          # Archon integration tests
pytest tests/test_crawl4ai_realtime.py        # Crawl4AI tests (legacy)
pytest tests/test_host_service.py             # Host service tests  
pytest tests/test_integration_full.py         # Full integration tests

# With coverage
pytest --cov=app tests/
```

## ðŸ“Š Real-time Data Monitoring

### Archon-based Data Sources Health
Monitor Croatian tourism data through Archon:

```bash
# Check Archon integration health
curl http://localhost:8000/api/v1/archon-realtime/health

# Get Archon data summary
curl http://localhost:8000/api/v1/archon-realtime/summary

# Query Archon knowledge base directly
curl -X POST "http://localhost:8000/api/v1/archon-realtime/archon/query?query=Croatian tourism events"
```

### Performance Metrics
- **Response Time**: < 200ms for API endpoints
- **Data Freshness**: Updates via Archon's knowledge base refresh cycle
- **Extraction Accuracy**: > 85% content quality score
- **Infrastructure Efficiency**: Single unified system vs duplicate infrastructure

## ðŸ”§ Configuration

### Environment Variables
```bash
# Database Configuration
DATABASE_URL=postgresql+asyncpg://user:pass@localhost/touristguide
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password

# AI Services
OPENAI_API_KEY=your_openai_key
GOOGLE_AI_API_KEY=your_google_key

# Archon Integration (recommended)
ARCHON_PROJECT_ID=715a62d5-5d7d-4eb8-9294-554424590dcd
ARCHON_API_ENDPOINT=your_archon_endpoint

# Crawl4AI Configuration (optional/legacy)
CRAWL4AI_RATE_LIMIT_DELAY=2
CRAWL4AI_TIMEOUT_SECONDS=45
CRAWL4AI_QUALITY_THRESHOLD=0.8
```

### Data Integration Configuration
```python
# Archon-based configuration (recommended)
ARCHON_CONFIG = {
    "knowledge_base_queries": [
        "Croatian tourism events attractions",
        "Istria Kvarner tourism information",
        "Lovran Opatija tourism updates"
    ],
    "content_types": ["events", "attractions", "opening_hours", "prices"],
    "regions": ["Istria", "Kvarner"],
    "cities": ["Lovran", "Opatija", "Pula", "Rovinj"]
}

# Crawl4AI configuration (legacy)
CRAWL4AI_CONFIG = {
    "browser_type": "chromium",
    "headless": True,
    "extraction_strategies": ["css_schema", "regex_fallback", "croatian_tourism"]
}
```

## ðŸ“ˆ Roadmap

### Current Phase: Unified Archon Integration âœ…
- âœ… Host registration and dashboard
- âœ… Guest group creation with access codes  
- âœ… **Archon-based real-time Croatian tourism data integration**
- âœ… **Unified infrastructure leveraging existing Archon crawler**
- âœ… **Knowledge base queries for tourism information**
- âœ… Lovran area attractions database
- âœ… Multi-language support (Croatian/English/German/Italian)
- âœ… **Comparison framework: Archon vs Crawl4AI**

### Phase 2: Enhanced Archon Capabilities (In Progress)
- ðŸ”„ Graph database for relationship intelligence
- ðŸ”„ Vector database for AI recommendations  
- ðŸ”„ Advanced group dynamics analysis
- âœ… **Archon knowledge base integration**
- ðŸ”„ **Enhanced RAG queries for tourism content**

### Phase 3: Expansion (Planned)
- ðŸ“‹ Extend to broader Istria region
- ðŸ“‹ Mobile app for guests
- ðŸ“‹ Analytics and business intelligence
- ðŸ“‹ **Advanced Archon workflow integration**

## ðŸ¤ Contributing

### Development Standards
- **File Size Limit**: Maximum 500 lines per file
- **Type Safety**: Use type hints throughout
- **Documentation**: Google-style docstrings
- **Testing**: Minimum 3 test cases per feature (success, edge case, failure)
- **Archon Integration**: Prioritize Archon-based solutions over external tools

### Code Quality
- **Formatting**: Black formatter, PEP8 compliance
- **Testing**: Comprehensive pytest coverage for all integration layers
- **Archon Integration**: Include tests for knowledge base queries and data processing

## ðŸ“ž Support

- **Project Documentation**: See `PLANNING.md` for detailed architecture
- **Task Management**: See `TASK.md` for current development status  
- **Real-time Data**: See API documentation at `/docs` when running locally
- **Archon Integration**: Unified approach leveraging existing infrastructure

## ðŸŽ¯ Architecture Decision: Archon vs Crawl4AI

### Why We Chose Archon Integration

**âœ… Advantages of Archon Approach:**
- **Unified Infrastructure**: Single system for project management and data collection
- **No Duplication**: Leverages existing Archon crawler capabilities
- **Better Resource Utilization**: Reduces infrastructure complexity
- **Integrated Workflow**: Seamless integration with existing project setup
- **Cost Effective**: Lower maintenance overhead
- **Knowledge Base**: Rich, pre-processed content available

**ðŸ“‹ Crawl4AI Comparison (Available for Reference):**
- **Dedicated Scraping**: Specialized web scraping capabilities
- **Advanced Extraction**: Multiple extraction strategies
- **Independent Operation**: Standalone scraping infrastructure
- **Higher Overhead**: Additional infrastructure and maintenance

**ðŸŽ¯ Recommendation**: Use Archon-based endpoints (`/api/v1/archon-realtime/*`) for production. Crawl4AI endpoints (`/api/v1/realtime/*`) remain available for comparison and specific use cases.

---

**Built with â¤ï¸ for Croatian tourism hosts and their guests**  
*Leveraging Archon's unified infrastructure to create exceptional travel experiences in beautiful Croatia*
