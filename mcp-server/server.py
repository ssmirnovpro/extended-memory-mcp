#!/usr/bin/env python3

# Extended Memory MCP Server
# Copyright (c) 2024 Sergey Smirnov
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

"""
Legacy entry point for Extended Memory MCP Server
Maintains backwards compatibility with existing configurations.
"""

import asyncio
import sys
from pathlib import Path


def main():
    # Add src to path for development mode
    src_path = str(Path(__file__).parent.parent / "src")
    if src_path not in sys.path:
        sys.path.insert(0, src_path)

    # Import and run the main server
    from extended_memory_mcp.server import main as server_main

    asyncio.run(server_main())


if __name__ == "__main__":
    main()
