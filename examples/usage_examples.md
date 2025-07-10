# Memory MCP Server Usage Examples

## Basic Operations

### Saving Context
```python
# Automatic saving with importance analysis
await save_context(
    content="We decided to use SQLite for memory storage",
    project_id="memory_mcp"
)

# Manual parameter specification
await save_context(
    content="User prefers concise technical explanations",
    project_id="memory_mcp",
    context_type="preference", 
    importance_level=7,
    tags=["communication", "style"]
)
```

### Loading Session Context
```python
# Load full project context
result = await load_session_context(project_id="memory_mcp")

# Limited loading
result = await load_session_context(
    project_id="memory_mcp",
    max_items=20,
    include_personal=True
)
```

## Project Management

### Project ID Specification
```python
# Project ID is specified by Claude in MCP tool calls
result = await load_session_context(project_id="my_project")
result = await save_context(
    content="Important architectural decision",
    project_id="my_project"
)
```

## Claude Integration Scenarios

### Scenario 1: New Session Start
```
User: Hello, Claude! Let's continue our work.

Claude: 
1. Automatically calls load_session_context()
2. Determines the project from user's prompt
3. Loads relevant context
4. Responds: "Hello! Continuing work on memory_mcp project. 
   I remember we're using SQLite for storage and working 
   on automatic project detection..."
```

### Scenario 2: Important Decision Making
```
User: Claude, we decided to add encryption for SQLite database.

Claude:
1. Analyzes importance (high - contains "decided")
2. Determines type (decision)
3. Automatically calls save_context() with importance_level=8
4. Responds: "Understood, saved this decision to memory. 
   SQLite database encryption - excellent choice for security."
```

### Scenario 3: Project Switching
```
User: Now let's work on my_frontend_project.

Claude:
1. User indicates project_id in their message
2. Calls load_session_context("my_frontend_project")
3. Loads project context
4. Responds: "Switched to my_frontend_project. 
   I remember we're using React + TypeScript..."
```

## Context Types

### `decision` - Architectural Decisions
```python
await save_context(
    content="Chose FastAPI for HTTP API instead of Flask",
    context_type="decision",
    importance_level=8,
    tags=["fastapi", "architecture", "api"]
)
```

### `preference` - User Preferences
```python
await save_context(
    content="User prefers detailed explanations with code examples",
    context_type="preference", 
    importance_level=6,
    tags=["communication", "code", "examples"]
)
```

### `personality` - AI Personality Traits
```python
await save_personality_trait(
    trait_type="communication_style",
    trait_value="concise, technical, with examples",
    confidence_score=0.9
)
```

### `status` - Current Project State
```python
await save_context(
    content="Basic MCP server structure ready, testing integration",
    context_type="status",
    importance_level=7,
    tags=["progress", "testing", "integration"]
)
```

## Memory Search

### Semantic Search
```python
# Search by keywords
results = await search_context(
    query="SQLite encryption",
    project_id="memory_mcp",
    min_importance=6
)

# Search decisions
results = await search_context(
    query="architectural decision",
    context_types=["decision"],
    limit=5
)
```

## Memory Management

### Archiving Old Context
```python
# Archive context older than 30 days
await archive_old_context(
    project_id="memory_mcp",
    before_date=datetime.now() - timedelta(days=30),
    preserve_critical=True
)
```

### Memory Cleanup
```python
# Remove low importance context
await cleanup_low_importance(
    project_id="memory_mcp", 
    max_importance=3
)
```

## Claude Desktop Integration

### Automatic Prompts for Claude
```
System: At the beginning of each session, automatically call load_session_context() 
with the project_id specified by the user and briefly summarize the loaded context.

When detecting important information (decisions, preferences, architectural 
choices), automatically save them through save_context().

Project ID is always specified by the user explicitly, no auto-detection is used.
```

### MCP Tool Call Examples in Claude
```json
// Automatic decision saving
{
  "tool": "save_context",
  "arguments": {
    "content": "Decided to use aiosqlite for async database operations",
    "project_id": "memory_mcp",
    "context_type": "decision",
    "importance_level": 8,
    "tags": ["aiosqlite", "async", "database"]
  }
}

// Session context loading
{
  "tool": "load_session_context", 
  "arguments": {
    "project_id": "memory_mcp",
    "max_items": 30,
    "include_personal": true
  }
}
```

## Advanced Scenarios

### Saving Reasoning Chains
```python
# Save decision-making process
await save_context(
    content="""
    Considered options:
    1. PostgreSQL - too heavy for local usage
    2. JSON files - no efficient search capabilities  
    3. SQLite - perfect balance of simplicity and functionality
    
    Chose SQLite with FTS5 for full-text search.
    """,
    context_type="decision",
    importance_level=9,
    tags=["database", "comparison", "sqlite", "reasoning"]
)
```

### Tracking Project Evolution
```python
# Update project status
await save_context(
    content="Project moved from research phase to active development",
    context_type="status", 
    importance_level=8,
    tags=["milestone", "development", "phase"]
)
```
