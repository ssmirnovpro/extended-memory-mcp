# Extended Memory MCP

[![PyPI version](https://badge.fury.io/py/extended-memory-mcp.svg)](https://badge.fury.io/py/extended-memory-mcp)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

**Extended Memory MCP is a Model Context Protocol (MCP) tool that provides cross-session memory storage for Claude Desktop app.**

This tool solves a fundamental problem: when your Claude conversation reaches token limits or you start a new chat, all context is lost. Claude forgets your project details, previous decisions, and working relationships. You have to re-explain everything from scratch.

Extended Memory MCP automatically saves and restores:
- Your project context and current work status
- Architectural decisions and their reasoning
- Claude's communication style and your working preferences  
- Complete isolation between different projects

**This is specifically designed for Desktop Claude app users** who want persistent memory across conversation sessions. It's not a CLI tool - it runs as an MCP server that integrates directly with the Desktop Claude app through the Model Context Protocol.

## 🚀 Quick Start

### Requirements
- **Python 3.8+** 
- **Desktop Claude app**

### Step 1: Installation

#### Option A: Install from PyPI (Recommended)
```bash
pip install extended-memory-mcp
```

#### Option B: Install from Source (Development)
```bash
git clone https://github.com/ssmirnovpro/extended-memory-mcp.git
cd extended-memory-mcp
pip install -e ".[dev]"
```

### Step 2: Desktop Claude App Configuration

**Edit your Desktop Claude app MCP configuration:**
1. Open Desktop Claude app
2. Go to **Settings** → **Developer** → **Edit Config**
3. Add the Extended Memory MCP server to your configuration

**Configuration:**
```json
{
  "mcpServers": {
    "extended-memory": {
      "command": "python3",
      "args": ["-m", "extended_memory_mcp.server"],
      "env": {
        "LOG_LEVEL": "INFO"
      }
    }
  }
}
```

**Configuration for source installation (if you installed from GitHub):**
```json
{
  "mcpServers": {
    "extended-memory": {
      "command": "python3", 
      "args": ["/path/to/extended-memory-mcp/mcp-server/server.py"],
      "env": {
        "LOG_LEVEL": "INFO"
      }
    }
  }
}
```

**If you already have other MCP servers configured, add the `extended-memory` entry to your existing `mcpServers` section.**

### Step 3: Additional Installation Options

#### Install with Redis Support
```bash
pip install extended-memory-mcp[redis]
```

#### Install Development Version
```bash
pip install extended-memory-mcp[dev]
```

#### Configuration Parameters

| Parameter | Purpose | Default Value |
|-----------|---------|---------------|
| `STORAGE_CONNECTION_STRING` | Database location | `~/.local/share/extended-memory-mcp/memory.db` (macOS/Linux) |
| `LOG_LEVEL` | Logging verbosity | `INFO` |

#### Platform-Specific Notes

**macOS & Linux:** Can use default storage location (auto-created in user data directory)

**Windows:** Recommended to set explicit `STORAGE_CONNECTION_STRING` path:
```json
"env": {
  "STORAGE_CONNECTION_STRING": "sqlite:///C:/Users/YourName/extended-memory/memory.db"
}
```

#### Redis Storage (Experimental)

For advanced users wanting Redis instead of SQLite:
```json
"env": {
  "STORAGE_CONNECTION_STRING": "redis://localhost:6379/0"
}
```
*Note: Redis support is experimental. Performance characteristics are not fully tested.*

### Step 3: Verification

1. **Restart Claude Desktop**
2. **Check MCP Connection** - In Claude, the extended-memory server should appear in Developer Settings
3. **Test Memory** - Ask Claude: "Save that we're working on project X with React architecture"
4. **Verify Persistence** - Start a new conversation and ask Claude about your projects

## 🔒 Privacy & Local Storage

**Extended Memory MCP is a "dumb" storage client** - your data remains completely local and private:
- ✅ **No cloud sync** - All data stored on your machine only
- ✅ **No analysis** - Data is stored as-is without processing or analysis  
- ✅ **No telemetry** - Zero external communication or data collection
- ✅ **Full control** - You own and control all memory data

## 🔧 Project Organization & Usage

### Project Isolation

Memory is organized by projects with strict isolation between them. Each project maintains its own separate context, decisions, and history.

**Default behavior:** All conversations use the `general` project scope unless explicitly specified.

**For proper project isolation:**
Include the project identifier in your Claude custom instructions:
```
You have external memory; follow its instructions for effective usage. When working with external memory, always specify that this is project "<your-short-project-id-here>" as its project_id for read and write operations.
```

Replace `<your-short-project-id-here>` with your actual project identifier (e.g., `mobile_app`, `blog_redesign`, `work_project`).

**Important:** Projects are not auto-detected. Without explicit project_id specification, all conversations use the `general` scope.

### How the Memory Tool Works

Extended Memory provides Claude with memory management tools, but Claude decides when and how to use them. The AI may choose not to load memory automatically, especially for general conversations that don't seem memory-related.

**If Claude doesn't recall previous context, you can prompt:**
- "Load my project context"
- "What do you remember about this project?"
- "Check our previous work on this"

Claude has several memory tools available:
- `save_context` - Save important information with tags
- `load_contexts` - Load previous context and conversations
- `forget_context` - Remove outdated information
- `list_all_projects` - View all your projects
- `get_popular_tags` - Find commonly used tags

## 🤝 Community & Support

- **🐛 Issues** - [Report bugs or request features](https://github.com/ssmirnovpro/extended-memory-mcp/issues)
- **💬 Discussions** - [Ask questions and share ideas](https://github.com/ssmirnovpro/extended-memory-mcp/discussions)

## 🔒 Privacy & Security

- **Local-First**: All data stored locally on your machine
- **No Telemetry**: No data collection or external communication
- **Open Source**: Full transparency - audit the code yourself
- **GDPR Compliant**: You control your data completely

## 📄 License

This project is licensed under the MIT License.

**For Everyone**: Free to use, modify, and distribute without restrictions. Use it in commercial or personal projects - no strings attached.

See [LICENSE](LICENSE) for full details.

## 🌟 Star History

[![Star History Chart](https://api.star-history.com/svg?repos=ssmirnovpro/extended-memory-mcp&type=Date)](https://star-history.com/#ssmirnovpro/extended-memory-mcp&Date)

---

**Made with ❤️ for the AI community**

*Extended Memory MCP - Because your AI assistant should remember.*