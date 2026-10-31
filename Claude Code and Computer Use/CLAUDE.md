# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

A Python package of document-related tools (format conversion and processing), exposed to AI assistants through an MCP server built on `FastMCP` from the `mcp` SDK (pinned to `mcp[cli]==1.8.0`).

## Commands

The project uses `uv`. `uv run` uses `.venv` automatically, so activation is optional.

```bash
# Setup
uv venv
source .venv/bin/activate
uv pip install -e .

# Start the MCP server (stdio transport)
uv run main.py

# Tests
uv run pytest                                          # all tests
uv run pytest tests/test_document.py                   # one file
uv run pytest tests/test_document.py::TestBinaryDocumentToMarkdown::test_binary_document_to_markdown_with_pdf  # one test
```

No linter or formatter is configured.

## Architecture

- `main.py` creates the server (`FastMCP("docs")`) and is the only place where tools are registered. A function in `tools/` is not visible to MCP clients until it is imported and registered here.
- `tools/` holds plain Python functions, one module per area (`math.py`, `document.py`). They have no MCP dependency, so tests import and call them directly.
- `tools/document.py`: `binary_document_to_markdown(binary_data, file_type)` wraps `markitdown`, passing the extension via `StreamInfo`. It supports the `docx` and `pdf` extras installed by `markitdown[docx,pdf]`. It is currently **not** registered in `main.py` and does not yet follow the `Field`/docstring conventions below.
- `tests/fixtures/` contains `mcp_docs.docx` and `mcp_docs.pdf`, used by the document conversion tests.

## Defining MCP Tools

Register a tool in `main.py` by passing the function to the decorator factory:

```python
from tools.math import add
mcp.tool()(add)
```

FastMCP builds the tool schema from the function's signature, type hints, and docstring. These are the tool description and parameter docs the AI assistant sees, so write them carefully.

**Docstring (the tool description)** should:

1. Begin with a one-line summary.
2. Provide a detailed explanation of functionality.
3. Explain when to use (and when not to use) the tool.
4. Include usage examples with expected input/output.

**Parameters**: always give every function argument an appropriate type annotation (and a return type). FastMCP derives the tool's input schema from these types, so an unannotated or overly loose type (e.g. `Any`) produces a weak schema. Each parameter should also use pydantic `Field` for its description:

```python
from pydantic import Field

def my_tool(
    param1: str = Field(description="Detailed description of this parameter"),
    param2: int = Field(description="Explain what this parameter does"),
) -> ReturnType:
    """Comprehensive docstring here"""
    # Implementation
```

`tools/math.py:add` is the reference example of a fully conforming tool:

```python
def add(
    a: float = Field(description="First number to add"),
    b: float = Field(description="Second number to add"),
) -> float:
    """Add two numbers together.

    Takes two numerical inputs and returns their sum. This tool handles
    integers and floating point numbers.

    When to use:
    - When you need to perform simple addition
    - When you need precise numerical calculation

    Examples:
    >>> add(2, 3)
    5.0
    >>> add(2.5, 3.5)
    6.0
    """
    return a + b
```

Because `Field(...)` is the default value, calling a tool function directly in tests without passing every argument gives you a `FieldInfo` object instead of a value. Always pass every argument explicitly.
