# Examples

Prompts and expected output for common tasks. The MCP server section is captured from real runs; the rest are representative — actual output will vary with your model and codebase.

## Contents

1. [Code Generation](#code-generation)
2. [Refactoring](#refactoring)
3. [Debugging](#debugging)
4. [Testing](#testing)
5. [Documentation](#documentation)
6. [Code Review](#code-review)
7. [Project Setup](#project-setup)
8. [MCP Server](#mcp-server-beta)

---

## Code Generation

### Example 1: REST API Endpoint

**Prompt:**
```
> Create a FastAPI endpoint for creating and managing blog posts with CRUD operations
```

**Result:**
Creates `api/routes/posts.py` with:
- POST /posts - Create post
- GET /posts - List posts
- GET /posts/{id} - Get specific post
- PUT /posts/{id} - Update post
- DELETE /posts/{id} - Delete post

### Example 2: Database Models

**Prompt:**
```
> Create SQLAlchemy models for a blog system with Users, Posts, Comments, and Tags
```

**Result:**
Creates `models/blog.py` with:
- User model with relationships
- Post model with timestamps
- Comment model with foreign keys
- Tag model with many-to-many relationship

### Example 3: Utility Functions

**Prompt:**
```
> Create a Python module with utility functions for:
1. Email validation
2. Password hashing with bcrypt
3. JWT token generation and verification
4. File upload handling
```

**Result:**
Creates `utils/helpers.py` with all requested functions, proper error handling, and type hints.

---

## Refactoring

### Example 1: Add Type Hints

**Before:**
```python
def calculate_total(items, tax_rate):
    subtotal = sum(item['price'] * item['quantity'] for item in items)
    tax = subtotal * tax_rate
    return subtotal + tax
```

**Prompt:**
```
> Add type hints and improve the calculate_total function in billing.py
```

**After:**
```python
from typing import List, Dict
from decimal import Decimal

def calculate_total(
    items: List[Dict[str, Decimal]], 
    tax_rate: Decimal
) -> Decimal:
    """
    Calculate total price including tax.
    
    Args:
        items: List of items with 'price' and 'quantity' keys
        tax_rate: Tax rate as decimal (e.g., 0.08 for 8%)
        
    Returns:
        Total price including tax
        
    Raises:
        ValueError: If items is empty or tax_rate is negative
    """
    if not items:
        raise ValueError("Items list cannot be empty")
    if tax_rate < 0:
        raise ValueError("Tax rate cannot be negative")
        
    subtotal = sum(
        item['price'] * item['quantity'] 
        for item in items
    )
    tax = subtotal * tax_rate
    return subtotal + tax
```

### Example 2: Convert to Async

**Before:**
```python
def fetch_user_data(user_id):
    response = requests.get(f"{API_URL}/users/{user_id}")
    return response.json()
```

**Prompt:**
```
> Convert fetch_user_data to async using aiohttp
```

**After:**
```python
import aiohttp

async def fetch_user_data(user_id: int) -> dict:
    """Fetch user data asynchronously."""
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{API_URL}/users/{user_id}") as response:
            return await response.json()
```

### Example 3: Extract Configuration

**Prompt:**
```
> Refactor database.py to use environment variables instead of hardcoded values
```

**Result:**
- Extracts all hardcoded values
- Creates .env.example
- Updates code to use os.getenv()
- Adds python-dotenv dependency

---

## Debugging

### Example 1: Fix KeyError

**Prompt:**
```
> I'm getting "KeyError: 'user_id'" on line 45 of auth.py. The code is:
user_id = session_data['user_id']

How do I fix this gracefully?
```

**Response:**
```python
# Option 1: Use .get() with default
user_id = session_data.get('user_id')
if not user_id:
    raise AuthenticationError("User ID not found in session")

# Option 2: Use .get() with default value
user_id = session_data.get('user_id', None)

# Option 3: Try/except for more control
try:
    user_id = session_data['user_id']
except KeyError:
    logger.error("Session data missing user_id")
    raise AuthenticationError("Invalid session")
```

### Example 2: Memory Leak Investigation

**Prompt:**
```
> My Python application is using increasing amounts of memory over time. 
The main loop processes files in data_processor.py. Help me find the leak.
```

**Response provides:**
- Code review for common memory leak patterns
- Suggestions for using `del` and garbage collection
- Recommendations for profiling tools (memory_profiler)
- Example fixes for file handling

### Example 3: Performance Issues

**Prompt:**
```
> The generate_report function in reports.py is very slow with large datasets.
Can you optimize it?
```

**Response:**
- Identifies N+1 query problems
- Suggests database query optimization
- Recommends caching strategies
- Provides benchmarking code

---

## Testing

### Example 1: Generate Unit Tests

**Prompt:**
```
> Generate comprehensive pytest tests for the User class in models/user.py
```

**Result:**
Creates `tests/test_user.py` with:
- Test fixtures
- Test for user creation
- Test for validation
- Test for password hashing
- Test for edge cases
- Mock database interactions

### Example 2: Add Test Coverage

**Prompt:**
```
> Add tests for error cases in api/routes/auth.py that currently has 45% coverage
```

**Result:**
Adds tests for:
- Invalid credentials
- Expired tokens
- Missing headers
- Malformed requests

### Example 3: Integration Tests

**Prompt:**
```
> Create integration tests for the entire user registration flow
```

**Result:**
Creates `tests/integration/test_registration.py` with:
- End-to-end registration test
- Email verification test
- Duplicate user test
- Invalid data test

---

## Documentation

### Example 1: Generate README

**Prompt:**
```
> Generate a comprehensive README for my FastAPI project with:
- Installation instructions
- API endpoints documentation
- Environment variables
- Examples
```

**Result:**
Creates detailed README.md with all sections.

### Example 2: API Documentation

**Prompt:**
```
> Generate OpenAPI documentation for all endpoints in api/routes/
```

**Result:**
Updates route handlers with:
- Detailed docstrings
- Request/response examples
- Status codes
- Error responses

### Example 3: Add Docstrings

**Prompt:**
```
> Add Google-style docstrings to all functions in utils/helpers.py
```

**Result:**
```python
def validate_email(email: str) -> bool:
    """
    Validate email address format.
    
    Args:
        email: Email address string to validate
        
    Returns:
        True if email is valid, False otherwise
        
    Examples:
        >>> validate_email("user@example.com")
        True
        >>> validate_email("invalid.email")
        False
        
    Note:
        Uses RFC 5322 compliant regex pattern
    """
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))
```

---

## Code Review

### Example 1: Security Review

**Prompt:**
```
> Review api/routes/auth.py for security vulnerabilities
```

**Response identifies:**
- SQL injection risks
- Missing input validation
- Hardcoded secrets
- Insecure password storage
- Missing rate limiting
- CORS misconfiguration

### Example 2: Best Practices Review

**Prompt:**
```
> Review data_processor.py and suggest improvements following Python best practices
```

**Response covers:**
- PEP 8 compliance
- Type hints
- Error handling
- Documentation
- Code organization
- Performance optimizations

### Example 3: Dependency Review

**Prompt:**
```
> Review requirements.txt and suggest:
1. Updates to latest stable versions
2. Security vulnerabilities
3. Unused dependencies
```

**Response provides:**
- Updated version numbers
- Security advisories
- Cleanup suggestions

---

## Project Setup

### Example 1: FastAPI Project Structure

**Prompt:**
```
> Set up a complete FastAPI project structure with:
- API routes
- Database models
- Authentication
- Tests
- Configuration
- Docker setup
```

**Result:**
Creates entire project structure with:
```
project/
├── api/
│   ├── routes/
│   ├── models/
│   └── dependencies.py
├── core/
│   ├── config.py
│   └── security.py
├── tests/
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
└── README.md
```

### Example 2: CI/CD Setup

**Prompt:**
```
> Create GitHub Actions workflow for:
- Running tests
- Code linting
- Type checking
- Docker build
- Deploy to staging
```

**Result:**
Creates `.github/workflows/ci.yml` with complete pipeline.

### Example 3: Database Migration

**Prompt:**
```
> Set up Alembic for database migrations with initial User and Post models
```

**Result:**
- Installs Alembic
- Creates migration structure
- Generates initial migration
- Provides migration commands

---

## Workflow Examples

### Daily Development Workflow

```bash
# Morning: Start new feature
$ cd my-project
$ coding-agent chat

> Create a new feature branch setup for user notifications
> Generate notification model with SQLAlchemy
> Create API endpoint for sending notifications
> Add tests for notification functionality

# Afternoon: Code review
> Review the changes I made today for:
1. Security issues
2. Code quality
3. Missing tests

# Evening: Documentation
> Generate API documentation for new notification endpoints
> Update README with new features

$ exit
```

### Bug Fix Workflow

```bash
$ coding-agent chat

> I found a bug: users can't upload files larger than 1MB
> The error is in api/routes/upload.py line 23
> Help me fix this and add proper file size validation

# Agent provides fix
> Add tests to ensure this bug doesn't happen again
> Update documentation with file size limits

$ exit
```

### Refactoring Workflow

```bash
$ coding-agent chat

> I want to refactor the authentication system to:
1. Use JWT tokens instead of sessions
2. Add refresh token support
3. Implement token blacklisting
4. Update all affected endpoints

> Create migration guide for existing users
> Update tests for new authentication flow

$ exit
```

---

## Tips for Effective Prompts

### Be Specific
❌ "Make this better"
✅ "Refactor this function to use async/await and add error handling"

### Provide Context
❌ "Fix this error"
✅ "Fix AttributeError on line 42 in parser.py when processing empty CSV files"

### Break Down Complex Tasks
❌ "Build a complete authentication system"
✅ Step by step:
1. "Create user model with password hashing"
2. "Add JWT token generation"
3. "Create login endpoint"
4. "Add authentication middleware"

### Request Examples
✅ "Create a user registration function with example usage"

### Specify Coding Standards
✅ "Add type hints following PEP 484 and docstrings in Google style"

---

## Advanced Patterns

### 1. Template Generation

```
> Create a class template for API resources with:
- CRUD operations
- Validation
- Error handling
- Type hints
- Tests

Then apply it to create UserResource and PostResource
```

### 2. Code Migration

```
> Migrate database.py from SQLAlchemy 1.4 to 2.0:
1. Update session handling
2. Fix deprecated imports
3. Update query syntax
4. Maintain backwards compatibility
```

### 3. Performance Optimization

```
> Analyze api/routes/users.py for performance issues:
1. Identify N+1 queries
2. Add database indexes
3. Implement caching
4. Add query pagination
```

---

## Common Patterns

### Pattern 1: "Fix and Test"
```
> Fix the validation error in forms.py and add tests to prevent regression
```

### Pattern 2: "Implement Feature"
```
> Implement password reset functionality with:
- Email token generation
- Token validation
- Password update
- Email notification
```

### Pattern 3: "Modernize Code"
```
> Modernize legacy_api.py to use:
- Type hints
- Async/await
- Modern Python practices
- Better error handling
```

---

## MCP Server (Beta)

### Example 1: Basic Server Start

**Command:**
```bash
coding-agent serve
```

**Output:**
```
═══ MCP Server Starting ═══

Workspace: /Users/royu/development/my-project
Transport: stdio
Safe Mode: ✅ Enabled

Enabled Tools:
  ✅ File tools: read_file, list_files
  ✅ AI tools: explain_code

✓ Server initialized with 3 tool(s)
  • read_file: Read contents of a file from the workspace
  • list_files: List files in the workspace
  • explain_code: Explain what a code snippet does

Server running... Press Ctrl+C to stop
```

**Use Case:** Start MCP server with safe defaults for Claude Desktop integration.

---

### Example 2: Custom Workspace

**Command:**
```bash
coding-agent serve --workspace /path/to/specific/project
```

**Output:**
```
═══ MCP Server Starting ═══

Workspace: /path/to/specific/project
Transport: stdio
Safe Mode: ✅ Enabled

Enabled Tools:
  ✅ File tools: read_file, list_files
  ✅ AI tools: explain_code

✓ Server initialized with 3 tool(s)

Server running... Press Ctrl+C to stop
```

**Use Case:** Serve a specific project directory instead of current directory.

---

### Example 3: Enable History Tools

**Command:**
```bash
coding-agent serve --enable-history-tools
```

**Output:**
```
═══ MCP Server Starting ═══

Workspace: /Users/royu/development/my-project
Transport: stdio
Safe Mode: ❌ Disabled

Enabled Tools:
  ✅ File tools: read_file, list_files
  ✅ AI tools: explain_code
  ✅ History tools: search_history

✓ Server initialized with 4 tool(s)
  • read_file: Read contents of a file from the workspace
  • list_files: List files in the workspace
  • explain_code: Explain what a code snippet does
  • search_history: Search conversation history

Server running... Press Ctrl+C to stop
```

**Use Case:** Enable history tools for searching past conversations (disables Safe Mode).

---

### Example 4: Claude Desktop Integration

**Step 1: Configure Claude Desktop**

Edit `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "coding-agent": {
      "command": "/path/to/coding-agent/venv/bin/coding-agent",
      "args": ["serve", "--workspace", "/Users/royu/development/my-project"],
      "env": {}
    }
  }
}
```

**Step 2: Restart Claude Desktop**

Quit and reopen Claude Desktop app.

**Step 3: Verify Connection**

In Claude Desktop, you should see:
- 🔌 "3 tools available" indicator
- Tools: `read_file`, `list_files`, `explain_code`

**Step 4: Use Tools**

Talk to Claude:
```
"Can you read the README.md file from the workspace?"
```

Claude will use the `read_file` tool to access your project files.

---

### Example 5: MCP Inspector Testing

**Step 1: Install MCP Inspector**
```bash
npm install -g @modelcontextprotocol/inspector
```

**Step 2: Start Inspector**
```bash
npx @modelcontextprotocol/inspector \
  /path/to/coding-agent/venv/bin/coding-agent \
  serve --workspace /Users/royu/development/my-project
```

**Step 3: Test Tools**

The Inspector will open a web interface where you can:
1. See all available tools
2. View tool schemas
3. Execute tools with custom parameters
4. See responses in real-time

**Example Tool Execution:**

Tool: `read_file`
```json
{
  "file_path": "src/main.py",
  "start_line": 1,
  "end_line": 50
}
```

Response:
```json
{
  "content": "import asyncio\nimport sys\n...",
  "lines_read": 50,
  "total_lines": 150
}
```

---

### Example 6: Safe Mode vs Full Access

**Safe Mode (Default):**
```bash
coding-agent serve
```
- ✅ read_file - Read files
- ✅ list_files - List files
- ✅ explain_code - AI explanations
- ❌ write_file - Disabled
- ❌ generate_code - Disabled
- ❌ search_history - Disabled

**Full Access:**
```bash
coding-agent serve --no-safe-mode --enable-history-tools
```
- ✅ All file operations
- ✅ All AI operations
- ✅ History access
- ⚠️  Use with caution!

---

### Example 7: Tool Usage Scenarios

**Scenario 1: Code Review**

Claude with `read_file` tool:
```
"Read src/api/auth.py and review it for security issues"
```

**Scenario 2: Project Exploration**

Claude with `list_files` tool:
```
"List all Python files in the src directory"
```

**Scenario 3: Code Understanding**

Claude with `explain_code` tool:
```python
def fibonacci(n):
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)
```
"Explain what this code does and suggest improvements"

---

### Example 8: Troubleshooting

**Problem: "Server not starting"**

**Check 1: Python environment**
```bash
which coding-agent
# Should be: /path/to/venv/bin/coding-agent
```

**Check 2: Installation**
```bash
pip show coding-agent-cli
# Should show version info
```

**Check 3: Workspace path**
```bash
coding-agent serve --workspace $(pwd)
# Use absolute path
```

**Problem: "Claude Desktop not seeing tools"**

**Check 1: Config file location**
```bash
cat ~/Library/Application\ Support/Claude/claude_desktop_config.json
# Should contain coding-agent server config
```

**Check 2: Command path**
```bash
# Make sure command path is absolute, not relative
"command": "/full/path/to/coding-agent"
```

**Check 3: Restart Claude**
- Fully quit Claude Desktop (Cmd+Q)
- Reopen Claude Desktop
- Wait 5-10 seconds for connection

---

## Next steps

- [Usage Guide](USAGE_GUIDE.md) for detailed command reference
- [Contributing Guide](CONTRIBUTING.md) if you want to work on the tool itself
- [GitHub Issues](https://github.com/iroy2000/coding-agent/issues) for the current roadmap and known bugs
