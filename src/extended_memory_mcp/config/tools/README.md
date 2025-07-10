# MCP Tools Configuration

This directory contains externalized MCP tool descriptions and schemas for easier maintenance and editing.

## Structure

```
config/tools/
├── descriptions/           # Individual markdown files for each tool
│   ├── save_context.md
│   ├── load_contexts.md
│   ├── forget_context.md
│   ├── list_all_projects.md
│   ├── get_popular_tags.md
├── schema/                # JSON schemas for tool inputs
│   └── input_schemas.json
├── descriptions_loader.py # Loader class for descriptions and schemas
└── README.md             # This file
```

## Editing Tool Descriptions

### For Developers
Simply edit the `.md` files in the `descriptions/` directory. Changes take effect immediately without code changes.

### For Non-Developers
1. Navigate to `config/tools/descriptions/`
2. Open the relevant `.md` file (e.g., `save_context.md`)
3. Edit the description content
4. Save the file
5. Changes are automatically loaded by the MCP server

## Markdown File Format

Each tool description file follows this structure:

```markdown
# tool_name 🔥

## Description
Brief description that becomes the MCP tool description...

## Workflow
Step-by-step usage instructions...

## When to Use
- Trigger conditions
- Use cases

## Examples
Good examples and anti-patterns...

## Best Practices
Guidelines for optimal usage...
```

## Key Benefits

1. **Easy Editing**: No need to modify Python code for description changes
2. **Version Control**: Clear git history for description changes  
3. **Rich Formatting**: Full markdown support with examples, lists, formatting
4. **Separation of Concerns**: Descriptions separate from code logic
5. **Fallback Support**: System falls back to hardcoded descriptions if files missing

## Technical Details

- **Loader**: `descriptions_loader.py` handles loading descriptions and schemas
- **Caching**: Descriptions are cached in memory for performance
- **Fallback**: If markdown files are missing, system uses hardcoded fallback descriptions
- **Auto-detection**: Loader automatically finds config directory relative to its location

## Adding New Tools

1. Create new `.md` file in `descriptions/` directory
2. Add tool schema to `schema/input_schemas.json`
3. Add tool name to the list in `mcp_protocol_handler.py` `_handle_tools_list()` method

## Schema Format

Input schemas are stored in JSON format in `schema/input_schemas.json`:

```json
{
  "tool_name": {
    "type": "object",
    "properties": {
      "param_name": {
        "type": "string",
        "description": "Parameter description"
      }
    },
    "required": ["required_param"]
  }
}
```

Changes to schemas require server restart, but description changes are loaded dynamically.
