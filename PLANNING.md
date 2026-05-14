# TouristGuideLocal - Project Planning

**Archon Project ID:** 715a62d5-5d7d-4eb8-9294-554424590dcd

## 🎯 Project Overview

TouristGuideLocal is a **B2B SaaS platform for Croatian tourist hosts** (Airbnb hosts, villa owners, apartment rentals) built with FastAPI and Python. The platform enables hosts to offer **personalized, AI-powered local guide services** to their guests, creating enhanced guest experiences and additional revenue streams for hosts.

**Primary Users:** Tourist accommodation hosts in Croatia
**End Beneficiaries:** Groups of tourists staying at these accommodations  
**Initial Focus:** Lovran area, Istria Peninsula
**First Host:** Apartment at Oprić 71, Lovran 51450

## 🏗️ Architecture & Technology Stack

### Core Technologies
- **Backend:** FastAPI (Python 3.9+)
- **Database Architecture:**
  - **PostgreSQL with pgvector:** Primary database (relational + vector + spatial)
  - **Neo4j:** Graph relationships and partnership networks
- **Data Validation:** Pydantic
- **Testing:** Pytest
- **Code Quality:** Black (formatting), Type hints
- **Documentation:** Google-style docstrings

### Multi-Database Strategy

#### **PostgreSQL with pgvector** - Primary Database
```
Core Business Logic:
- Host accounts and subscriptions
- Guest group registrations and access codes  
- Booking/stay periods and duration
- Business partner integrations (restaurants, activities)
- Audit trails and analytics
- Croatian tourism data (attractions, events)

Vector & AI Features:
- Guest preference embeddings (pgvector)
- Attraction similarity vectors
- Semantic search capabilities
- Content embeddings for multi-language support
- Group dynamics analysis vectors

Advanced PostgreSQL Features:
- JSONB for flexible attraction metadata
- Full-text search for Croatian/English content
- PostGIS for location-based queries
- Materialized views for performance
```

#### **Neo4j** - Relationship Intelligence  
```
- Host ↔ Local Business partnerships
- Attraction ↔ Category ↔ Interest relationships  
- Guest preferences ↔ Recommendation paths
- Geographic proximity relationships (Lovran ↔ Opatija ↔ Rijeka)
- Social connections between attractions
- Seasonal availability patterns
```

### Project Structure
```
TouristGuideLocal/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI application entry point
│   ├── core/
│   │   ├── __init__.py
│   │   ├── config.py        # Configuration settings
│   │   ├── database.py      # Multi-database connections
│   │   └── security.py      # Authentication & authorization
│   ├── models/
│   │   ├── __init__.py
│   │   ├── host.py          # Host models
│   │   ├── guest_group.py   # Guest group models
│   │   ├── attraction.py    # Attraction models (Lovran-focused)
│   │   ├── partner.py       # Business partner models
│   │   └── recommendation.py # AI recommendation models
│   ├── api/
│   │   ├── __init__.py
│   │   ├── v1/
│   │   │   ├── __init__.py
│   │   │   ├── hosts.py     # Host management endpoints
│   │   │   ├── guests.py    # Guest group endpoints
│   │   │   ├── attractions.py # Croatian attractions API
│   │   │   ├── recommendations.py # AI recommendations
│   │   │   └── partners.py  # Business partner integration
│   │   └── deps.py          # Dependencies
│   ├── services/
│   │   ├── __init__.py
│   │   ├── host_service.py
│   │   ├── guest_service.py
│   │   ├── recommendation_service.py # AI recommendation engine with pgvector
│   │   ├── graph_service.py # Neo4j relationship queries
│   │   └── vector_service.py # PostgreSQL vector operations
│   ├── db/
│   │   ├── __init__.py
│   │   ├── postgresql/      # PostgreSQL with pgvector
│   │   └── neo4j/          # Graph database
│   └── utils/
│       ├── __init__.py
│       ├── croatian_data.py # Croatian tourism data helpers
│       └── multi_lang.py   # Multi-language support
├── tests/
│   ├── __init__.py
│   ├── conftest.py          # Pytest configuration
│   ├── test_hosts.py
│   ├── test_guests.py
│   ├── test_recommendations.py
│   └── test_lovran_data.py
├── data/
│   ├── lovran/              # Lovran area data
│   ├── croatia/             # Croatian tourism data
│   └── partners/            # Business partner data
├── requirements.txt
├── .env.example
├── .gitignore
├── README.md
├── PLANNING.md
└── TASK.md
```

## 🎨 Design Principles

### Code Quality
- **File Size Limit:** Maximum 500 lines per file
- **Modularity:** Clear separation of concerns across databases
- **Type Safety:** Use type hints throughout
- **Documentation:** Google-style docstrings for all functions
- **Testing:** Comprehensive pytest coverage for all database layers

### API Design
- **RESTful:** Follow REST conventions
- **Versioned:** API v1 structure
- **Validated:** Pydantic models for request/response
- **Multi-tenant:** Secure host isolation
- **Guest Access:** Temporary access codes with expiration

### Database Design
- **Multi-Database:** Leverage strengths of each database type
- **Relationships:** Proper connections across database systems
- **Performance:** Optimized queries and caching
- **Security:** Multi-tenant isolation and data protection

## 🚀 Key Features

### For Croatian Tourist Hosts
1. **Host Dashboard**
   - Manage current guest groups
   - Add local knowledge and attractions
   - Partner with local businesses (restaurants, activities)
   - Analytics on guest engagement and satisfaction

2. **Local Content Management**
   - Add insider tips and hidden gems around Lovran
   - Upload photos and descriptions
   - Set seasonal availability and recommendations
   - Price/discount integration with local partners

3. **Guest Group Management**
   - Create temporary access codes for guests
   - Set group preferences and constraints
   - Monitor guest activity and satisfaction
   - Generate post-stay reports and feedback

### For Guest Groups
1. **Simple Group Onboarding**
   - Code-based access from host
   - Group preference survey (ages, interests, mobility, budget)
   - Stay duration and schedule input
   - Multi-language support

2. **AI-Powered Personalized Recommendations**
   - Recommendations based on group profile
   - Real-time weather and availability integration
   - Distance and transportation options from Lovran
   - Partner discounts and special offers

3. **Collaborative Group Planning**
   - Group voting on activities
   - Shared itinerary planning
   - Real-time updates and changes
   - Offline access for areas with poor connectivity

## 🇭🇷 Lovran Area Focus (Phase 1)

### Geographic Scope
- **Primary Location:** Lovran, Croatia (Istrian Peninsula)
- **Nearby Areas:** Opatija, Rijeka, Medveja, Lovranska Draga
- **Day Trip Destinations:** Pula, Rovinj, Poreč, Plitvice Lakes
- **Natural Attractions:** Učka Nature Park, Lungomare promenade

### Local Attractions Database
#### **Historic & Cultural**
- Lovran Old Town (medieval architecture, St. George Church)
- Opatija Riviera (Habsburg-era villas, Croatian Walk of Fame)
- Pula Arena and Roman sites (day trip)
- Rovinj old town and St. Euphemia Church

#### **Natural Experiences**
- Učka Nature Park (hiking trails, panoramic views)
- Lungomare coastal promenade (12km walk)
- Hidden swimming spots along rocky coast
- Medveja and Lovranska Draga beaches

#### **Food & Wine**
- Local specialties: Marun (chestnuts), Lovran cherries, wild asparagus
- Kozlović Winery (premium Istrian wines)
- Traditional konobas and seafood restaurants
- Seasonal food festivals (Marunada, Cherry Days)

#### **Activities**
- Boat trips to nearby islands (Cres, Krk)
- Wine tasting tours in Istria
- Hiking and nature walks
- Cultural events and summer festivals

### Local Business Integration
- **Restaurants:** Traditional konobas, seafood restaurants
- **Activities:** Boat tours, wine tastings, hiking guides
- **Transportation:** Local taxi services, boat transfers
- **Cultural:** Museums, galleries, seasonal events

## 🔧 Development Workflow

### Task Management
- **Archon Integration:** All tasks tracked in Archon system
- **Task Lifecycle:** todo → doing → review → done
- **Documentation:** Update TASK.md for all work items
- **Focus:** Start with Lovran area, expand gradually

### Code Development
1. **Start:** Check current task in Archon
2. **Research:** Use Context7 for documentation lookup
3. **Implement:** Follow multi-database architecture patterns
4. **Test:** Create comprehensive pytest tests for all DB layers
5. **Update:** Mark task progress in Archon

### Quality Assurance
- **Linting:** Black formatting, PEP8 compliance
- **Testing:** Minimum 3 test cases per feature (success, edge case, failure)
- **Documentation:** Update README.md when needed
- **Review:** Code review before task completion

## 🌐 Environment Setup

### Development Environment
- **Python:** 3.9+ with virtual environment
- **Databases:** PostgreSQL with pgvector extension, Neo4j
- **Dependencies:** Managed via requirements.txt
- **Configuration:** Environment variables via .env
- **Croatian Data:** Local tourism data integration

### Windows Compatibility
- **Shell:** PowerShell commands with `;` separator
- **Paths:** Windows-compatible file paths
- **Virtual Environment:** `venv` activation scripts

## 📝 Naming Conventions

### Files & Directories
- **Snake case:** `host_service.py`, `guest_group_model.py`
- **Descriptive:** Clear, meaningful names
- **Consistent:** Follow established patterns
- **Croatian:** `lovran_attractions.py`, `croatia_partners.py`

### Code Elements
- **Classes:** PascalCase (`HostModel`, `GuestGroupService`)
- **Functions:** snake_case (`get_host_by_id`, `create_guest_group`)
- **Variables:** snake_case (`host_id`, `attraction_list`)
- **Constants:** UPPER_SNAKE_CASE (`LOVRAN_COORDS`, `MAX_GROUP_SIZE`)

## 🎯 Success Metrics

### Technical Goals
- **Performance:** API response times < 200ms
- **Reliability:** 99.9% uptime
- **Scalability:** Handle 100+ concurrent host accounts
- **AI Accuracy:** >85% guest satisfaction with recommendations

### Business Goals
- **Host Adoption:** 50+ hosts in Lovran area by end of year
- **Guest Satisfaction:** >4.5/5 average rating
- **Local Partnerships:** 20+ integrated local businesses
- **Revenue:** Sustainable SaaS model for hosts

## 🚀 Development Roadmap

### Phase 1: Lovran MVP (Current)
- Host registration and basic dashboard
- Simple guest group creation with access codes
- Basic recommendation engine (relational DB only)
- Lovran area attractions database
- First host: Oprić 71, Lovran 51450

### Phase 2: AI Enhancement
- Graph database for relationship intelligence
- Vector database for AI recommendations
- Multi-language support (Croatian/English/German/Italian)
- Advanced group dynamics analysis

### Phase 3: Expansion
- Extend to broader Istria region
- Mobile app for guests
- Real-time availability integration
- Analytics and business intelligence

This planning document serves as the foundation for developing TouristGuideLocal as a B2B platform for Croatian tourist hosts, starting with the beautiful Lovran area as our pilot location. 