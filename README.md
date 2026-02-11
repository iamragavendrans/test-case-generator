# AI Test Case Generator

A production-ready, deterministic Test Case Generator that transforms raw software requirements into high-quality, executable test cases.

## 🎯 Product Vision

Accept raw software requirements → Intelligently parse & normalize → Generate specific, traceable test cases → QA-ready outputs

## ✨ Key Features

- **Requirement-First Processing**: Don't treat each line as a requirement. Split compound statements, merge related clauses
- **Deterministic Output**: Rule-based core ensures reproducible results
- **Full Traceability**: Every test case maps back to source requirements
- **Ambiguity Detection**: Surface unclear requirements with clarifying questions
- **Multiple Test Types**: Positive, Negative, Boundary, Edge, Security, API tests
- **Explainability**: Every transformation is logged and auditable

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     API Gateway / CLI                        │
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────┐
│                    Ingestion Service                         │
│  - Sanitize input  - Detect language  - Chunk text           │
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────┐
│               Normalization Service                           │
│  - Split compound statements                                 │
│  - Extract Actor-Action-Conditions-Outcome                   │
│  - Detect ambiguities                                         │
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────┐
│                Classification Service                        │
│  - Multi-label classification (Functional, Security, etc.)   │
│  - Priority hints                                             │
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────┐
│               Generation Service                             │
│  - Template-based test case generation                       │
│  - Multiple test types per requirement                       │
│  - Automation feasibility scoring                            │
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────┐
│              Traceability Store (Postgres)                   │
│  - Requirement ↔ Test Case mapping                           │
│  - Audit logs & provenance                                    │
└─────────────────────────────────────────────────────────────┘
```

## 🚀 Quick Start

### Option 1: Docker Compose (Recommended)

```bash
# Clone and navigate to directory
cd test-case-generator

# Start all services
docker-compose up -d

# Access the API
curl http://localhost:8000/health

# Generate test cases
curl -X POST http://localhost:8000/generate \
  -H "Content-Type: application/json" \
  -d '{"text": "User shall login with valid credentials"}'
```

### Option 2: Local Development

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
.\venv\Scripts\activate   # Windows

# Install dependencies
cd backend
pip install -r requirements.txt

# Download spaCy model
python -m spacy download en_core_web_sm

# Run API server
cd ..
uvicorn backend.main:app --reload

# Run CLI
python cli/cli.py generate "User shall login with credentials"
```

## 📖 Usage

### CLI Usage

```bash
# Single requirement
python cli/cli.py generate "User shall login with valid credentials"

# Verbose output
python cli/cli.py generate "System shall validate input" --verbose

# Batch processing
python cli/cli.py batch requirements.txt --output ./output
```

### API Usage

```python
import requests

response = requests.post(
    "http://localhost:8000/generate",
    json={
        "text": "User shall login with valid credentials and system shall authenticate"
    }
)

print(response.json())
```

### Export Formats

- **JSON**: Full structured output with provenance
- **CSV**: Tabular format for test management tools
- **Markdown**: Human-readable reports

## 📋 Input/Output Schemas

### Input
```json
{
  "text": "User shall login with valid credentials",
  "options": {
    "generate_security": true,
    "generate_api": true
  }
}
```

### Output (Canonical Schema)
```json
{
  "normalized_requirements": [
    {
      "requirement_id": "REQ-20240210-0001",
      "source_text": "User shall login with valid credentials",
      "normalized": {
        "actor": "User",
        "action": "login with valid credentials",
        "conditions": [],
        "expected_outcome": "successful login"
      },
      "classification": ["Functional"],
      "priority_hint": "Medium",
      "ambiguity": {
        "is_ambiguous": false,
        "issues": [],
        "clarifying_questions": [],
        "suggested_interpretations": []
      },
      "provenance": {
        "offsets": [{"start": 0, "end": 45}],
        "transformation_steps": ["split_compound"],
        "confidence": 0.95
      }
    }
  ],
  "test_cases": [
    {
      "test_case_id": "TTC-20240210-REQ-0001-POS-01",
      "title": "User when login with valid credentials expecting successful login",
      "mapped_requirement_id": "REQ-20240210-0001",
      "test_type": "Positive",
      "preconditions": ["User is on login page"],
      "steps": [
        {"step_number": 1, "action": "Enter valid credentials", "expected_intermediate": "Credentials accepted"},
        {"step_number": 2, "action": "Click login button", "expected_intermediate": "Login processed"},
        {"step_number": 3, "action": "Verify redirect", "expected_intermediate": "Dashboard displayed"}
      ],
      "test_data": {
        "inputs": {"username": "valid_user", "password": "valid_pass"},
        "environment": {"browser": "Chrome 120", "os": "Ubuntu 22.04"}
      },
      "expected_result": "User successfully logged in",
      "priority": "P1",
      "automation_feasibility": {
        "feasible": true,
        "notes": "Standard login flow - easy to automate",
        "estimated_effort": "Low"
      },
      "determinism_seed": "42",
      "explainability": {
        "generation_template_id": "POS_GEN_001",
        "rules_applied": ["template_POS_GEN_001", "test_type_POS"],
        "confidence": 0.95
      }
    }
  ],
  "audit_log": {
    "generation_timestamp": "2024-02-10T10:30:00Z",
    "generator_version": "1.0.0",
    "model_reference": "rule-based-v1",
    "validation_status": "passed",
    "errors": [],
    "change_history": []
  }
}
```

## 🧪 Running Tests

```bash
# Run unit tests
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=backend --cov-report=html

# Run specific test
pytest tests/test_normalization.py -v
```

## 📁 Project Structure

```
test-case-generator/
├── backend/
│   ├── main.py           # FastAPI application
│   ├── requirements.txt  # Python dependencies
│   ├── Dockerfile        # Container configuration
│   ├── models/
│   │   └── schemas.py    # Pydantic models (canonical schema)
│   ├── services/
│   │   ├── ingestion.py      # Input ingestion
│   │   ├── normalization.py  # Actor-Action-Outcome normalization
│   │   ├── classification.py # Multi-label classification
│   │   └── generation.py     # Test case generation
│   └── api/              # API routes
├── cli/
│   └── cli.py            # Command-line interface
├── frontend/
│   └── src/              # React UI components
├── tests/                # Unit and integration tests
├── docs/                # Documentation
├── docker-compose.yml   # Docker orchestration
└── README.md           # This file
```

## 🔧 Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection | postgresql://postgres:postgres@db:5432/testcase_gen |
| `REDIS_URL` | Redis connection | redis://redis:6379/0 |
| `LLM_MODEL` | LLM model for augmentation | local-llama |
| `DETERMINISTIC_SEED` | Random seed for reproducibility | 42 |

### Generation Options

```python
config = GenerationConfig(
    generate_positive=True,
    generate_negative=True,
    generate_boundary=True,
    generate_edge=True,
    generate_security=False,
    generate_api=False,
    determinism_seed="42",
    include_automation_hints=True
)
```

## 🎨 Design Decisions & Alternatives

### 1. Rule-Based vs ML-Based Normalization

**Decision**: Rule-based core with ML augmentation option

**Rationale**: 
- Determinism and auditability are critical for QA tooling
- Easier to debug and explain transformations
- Can add ML for edge cases later

**Alternative**: Pure ML (BERT-based)
**Trade-off**: Better accuracy but harder to audit, requires more compute

### 2. Template-Based Test Generation

**Decision**: Pre-defined templates with variable substitution

**Rationale**:
- Consistent, reproducible outputs
- Easy to validate and debug
- Templates can be version-controlled

**Alternative**: LLM-generated free-form
**Trade-off**: More flexible but less deterministic

### 3. Single-File SQLite (V1) → Postgres (Prod)

**Decision**: Start simple, scale to relational DB

**Rationale**:
- Faster development iteration
- Clear upgrade path
- V1 doesn't need full database features

**Alternative**: Start with Postgres
**Trade-off**: More complex setup but no migration needed

## 🚧 Roadmap

### V1 (Current)
- [x] Rule-based normalization
- [x] CLI interface
- [x] Basic FastAPI backend
- [x] JSON/CSV/Markdown export
- [x] Unit tests

### V2 (Next)
- [ ] LLM integration for complex requirements
- [ ] Web UI with React
- [ ] Database persistence
- [ ] Batch processing with Redis queue
- [ ] Export to TestRail/Zephyr

### V3 (Future)
- [ ] Self-hosted LLM (Llama 2/3)
- [ ] Real-time collaboration
- [ ] Test execution integration
- [ ] Analytics dashboard

## 📄 License

MIT License - see LICENSE file for details

## 🤝 Contributing

1. Fork the repository
2. Create feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open Pull Request

## 📞 Support

- Documentation: `/docs`
- API Docs: `http://localhost:8000/docs`
- Issues: GitHub Issues
