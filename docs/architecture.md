# ArchLens Architecture

## System Overview

ArchLens is a monorepo containing a FastAPI backend (Python 3.12+) and a React+Vite frontend, designed to provide static codebase analysis through a rich web interface.

---

## Component Diagram

```mermaid
C4Context
  title ArchLens System Context

  Person(dev, "Developer", "Uses the web UI to analyze codebases")

  System_Boundary(archlens, "ArchLens Monorepo") {
    System(fe, "Frontend", "React + Vite + Tailwind\nReact Flow graph visualization")
    System(be, "Backend", "FastAPI + Python 3.12\nStatic analysis engine")
    System(samples, "Samples", "spring-petclinic (Java)\npallets/flask (Python)")
  }

  System_Ext(fs, "Local Filesystem", "Codebase directories to analyze")

  Rel(dev, fe, "Uses", "HTTP/Browser")
  Rel(fe, be, "REST API calls", "HTTP JSON")
  Rel(be, fs, "Reads files", "I/O")
  Rel(be, samples, "Analyzes", "I/O")
```

---

## Backend Architecture

```mermaid
flowchart TD
    subgraph API["FastAPI Layer (app/api/)"]
        H["/health\nGET"]
        A["/analyze\nPOST"]
        G["/graph/:id\nGET"]
    end

    subgraph SVC["Services (app/services/)"]
        AS["AnalyzerService\nregistry + cache"]
        RS["RefactorService\nsuggestion generation"]
    end

    subgraph AZ["Analyzers (app/analyzers/)"]
        BASE["BaseAnalyzer\n(ABC)"]
        PY["PythonAnalyzer\nast module"]
        JA["JavaAnalyzer\njavalang"]
    end

    subgraph MDL["Models (app/models/)"]
        GR["GraphNode / GraphEdge\nDependencyGraph\nAnalysisResult"]
        RF["Smell / Suggestion\nSmellType / Severity"]
    end

    H -->|settings| CFG["core/config.py\npydantic-settings"]
    A --> AS
    G --> AS
    AS --> PY
    AS --> JA
    PY --> BASE
    JA --> BASE
    AS --> RS
    PY --> GR
    JA --> GR
    RS --> RF
```

---

## Frontend Architecture

```mermaid
flowchart LR
    subgraph App["App.tsx (root layout)"]
        LP["Left Panel\n(AnalyzePanel + SmellList)"]
        MC["Main Canvas\n(GraphCanvas / React Flow)"]
        RP["Right Panel\n(Sidebar tabs)"]
    end

    subgraph Hooks
        UA["useAnalysis\n(state + API calls)"]
    end

    subgraph API_Client["src/api/client.ts"]
        AX["axios instance"]
    end

    LP -->|path + language| UA
    UA -->|result| MC
    UA -->|result| RP
    UA --> AX
    AX -->|POST /analyze| BE["FastAPI Backend"]
    MC -->|node click| RP
```

---

## Data Flow: Analysis Request

```mermaid
sequenceDiagram
    participant U as User
    participant FE as React Frontend
    participant BE as FastAPI Backend
    participant AZ as PythonAnalyzer/JavaAnalyzer
    participant FS as Filesystem

    U->>FE: Enter path + click "Run Analysis"
    FE->>BE: POST /analyze {path, language}
    BE->>AZ: run_analysis(path, language)
    AZ->>FS: glob *.py / *.java
    FS-->>AZ: file list
    AZ->>FS: read_text() per file
    FS-->>AZ: source code
    AZ-->>AZ: ast.parse / javalang.parse
    AZ-->>BE: AnalysisResult (graph + smells)
    BE-->>BE: generate_suggestions()
    BE-->>FE: JSON response
    FE-->>U: Interactive dependency graph + smell list
```

---

## Smell Detection Pipeline

```mermaid
flowchart TD
    SRC["Source Files"] --> PARSE["Parse AST\nast / javalang"]
    PARSE --> NODES["Extract Nodes\n(modules, classes, interfaces)"]
    PARSE --> EDGES["Extract Edges\n(imports, inheritance)"]
    NODES --> GRAPH["DependencyGraph"]
    EDGES --> GRAPH
    GRAPH --> SMELL["detect_smells()"]
    SMELL --> CIRC["Circular Import\nDFS cycle detection"]
    SMELL --> GOD["God Module\n> 500 LOC"]
    SMELL --> LARGE["Large Class\n> 300 LOC"]
    SMELL --> DEEP["Deep Inheritance\n> 3 levels"]
    CIRC --> SUGGESTIONS["RefactorService\ngenerate_suggestions()"]
    GOD --> SUGGESTIONS
    LARGE --> SUGGESTIONS
    DEEP --> SUGGESTIONS
```

---

## Directory Structure

```
archlens/
├── backend/              FastAPI application
│   ├── app/
│   │   ├── api/          Route handlers
│   │   ├── analyzers/    Language-specific analyzers
│   │   ├── core/         Config + logging
│   │   ├── models/       Pydantic models
│   │   └── services/     Business logic
│   └── tests/            pytest test suite
├── frontend/             React + Vite + TypeScript
│   └── src/
│       ├── api/          Axios client
│       ├── components/   UI components
│       ├── hooks/        Custom React hooks
│       └── types/        TypeScript type definitions
├── samples/              Demo repos (shallow clones)
│   ├── java-spring/      spring-petclinic
│   └── python-flask/     pallets/flask
├── docs/                 Documentation
├── .github/workflows/    CI pipeline
└── Makefile             Development commands
```

---

## Key Design Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Python analysis | `ast` stdlib | Zero extra deps, handles Python 3.x syntax |
| Java analysis | `javalang` | Pure-Python, no JVM required |
| Graph storage | In-process dict | Simple for single-instance deployment; swap Redis for distributed |
| API style | REST | Simple, cacheable, easy to test with curl |
| Frontend graph | React Flow | Production-grade, supports interactive pan/zoom/minimap |
| Env config | pydantic-settings | Type-safe, env-var + .env file support, validator support |
