### CompletionGeneration Metadata Example

Source: https://deepwiki.com/Chainlit/chainlit/4-step-and-message-system

An example of `CompletionGeneration` metadata for completion-based LLM calls, as used in LlamaIndex integrations. It captures the model, prompt, completion content, and token count.

```python
# From llama_index/callbacks.py lines 186-192
step.generation = CompletionGeneration(
    model=model,
    prompt=formatted_prompt,
    completion=content,
    token_count=token_count,
)
```

--------------------------------

### Manage Python Dependencies with uv

Source: https://deepwiki.com/Chainlit/chainlit/11-developer-guide

Install Python dependencies using uv package manager with optional extras for tests, type checking, development tools, and custom data backends. Includes development mode to skip project installation. Commands must be run from the backend directory.

```shell
cd backend
uv sync --extra tests --extra mypy --extra dev --extra custom-data
```

```shell
uv sync --no-install-project --no-editable
```

--------------------------------

### ChatGeneration Metadata Example

Source: https://deepwiki.com/Chainlit/chainlit/4-step-and-message-system

An example of how `ChatGeneration` metadata is captured for chat-based LLM calls, often seen in LangChain integrations. It includes details like provider, model, tools, settings, and message history.

```python
# From langchain/callbacks.py lines 598-625
current_step.generation = ChatGeneration(
    provider=provider,
    model=model,
    tools=tools,
    variables=variables,
    settings=llm_settings,
    duration=duration,
    token_throughput_in_s=throughput,
    tt_first_token=chat_start.get("tt_first_token"),
    messages=[
        self._convert_message(m) for m in chat_start["input_messages"]
    ],
    message_completion=message_completion,
)
```

--------------------------------

### Install JavaScript Dependencies with pnpm

Source: https://deepwiki.com/Chainlit/chainlit/11-developer-guide

Install frontend workspace packages using pnpm package manager with the configured .npmrc settings. Supports independent package versioning across the monorepo.

```shell
pnpm install
```

--------------------------------

### GET /project/settings

Source: https://deepwiki.com/Chainlit/chainlit/3-backend-system

Retrieves merged configuration settings for the current user and chat profile. It loads language-specific markdown, calls registered callbacks for chat profiles and starters, applies configuration overrides, and returns UI, features, persistence, and thread resumability settings.

```APIDOC
## GET /project/settings

### Description
Retrieves merged configuration settings for the current user and chat profile. It loads language-specific markdown, calls registered callbacks for chat profiles and starters, applies configuration overrides, and returns UI, features, persistence, and thread resumability settings.

### Method
GET

### Endpoint
/project/settings

### Parameters
#### Query Parameters
- **language** (string) - Optional - The language for markdown file loading.
- **chat_profile** (string) - Optional - The name of the chat profile to apply overrides for.

### Response
#### Success Response (200)
- **ui** (object) - User interface configuration.
- **features** (object) - Feature flags and settings.
- **project** (object) - Project-specific settings.
- **dataPersistence** (object) - Data persistence configuration.
- **threadResumable** (object) - Thread resumability settings.

#### Response Example
```json
{
  "ui": {},
  "features": {},
  "project": {},
  "dataPersistence": {},
  "threadResumable": {}
}
```
```

--------------------------------

### GET /project/settings

Source: https://deepwiki.com/Chainlit/chainlit/12-configuration-reference

Retrieves the current project settings with any active chat profile overrides applied. Used by the frontend to initialize UI and features.

```APIDOC
## GET /project/settings

### Description
Returns current project settings with dynamic overrides based on the active chat profile.

### Method
GET

### Endpoint
/project/settings

### Parameters
#### Query Parameters
- **chat_profile** (string) - Optional - Specifies which chat profile's overrides to apply

### Response
#### Success Response (200)
- **ui** (object) - UI configuration settings
- **features** (object) - Feature flags and settings
- **authentication** (object) - Auth provider configuration

#### Response Example
{
  "ui": {
    "name": "Advanced Assistant",
    "cot": "tool_call"
  },
  "features": {
    "mcp": {
      "enabled": true
    }
  }
}
```

--------------------------------

### Display Command Button Examples - TypeScript

Source: https://deepwiki.com/Chainlit/chainlit/10-actions-and-interactivity

Illustrates how to define commands with `button: true` to display them as persistent buttons and `persistent: true` to keep them selected after message submission. These examples are used in the Chainlit UI.

```typescript
// Button command stays visible after selection
{ id: "Search", icon: "globe", description: "Web search", button: true }

// Persistent button stays selected after sending message
{ id: "Canvas", icon: "pen-line", description: "Collaborate", 
  button: true, persistent: true }
```

--------------------------------

### Run Python Backend Tests with Coverage

Source: https://deepwiki.com/Chainlit/chainlit/11-developer-guide

Execute pytest with coverage reporting for the chainlit backend package. Requires test dependencies to be installed via uv. Generates coverage metrics for CI integration.

```shell
cd backend
uv run pytest --cov=chainlit/
```

--------------------------------

### GET /project/file/{file_id}

Source: https://deepwiki.com/Chainlit/chainlit/3-backend-system

Serves uploaded files with authorization. It retrieves the session, verifies user ownership, looks up the file, and returns it as a FileResponse.

```APIDOC
## GET /project/file/{file_id}

### Description
Serves uploaded files with authorization. It retrieves the session, verifies user ownership, looks up the file, and returns it as a FileResponse.

### Method
GET

### Endpoint
/project/file/{file_id}

### Parameters
#### Path Parameters
- **file_id** (string) - Required - The ID of the file to retrieve.

#### Query Parameters
- **session_id** (string) - Required - The ID of the session the file belongs to.

### Response
#### Success Response (200)
- **FileResponse** - The file content with appropriate Content-Type header.

#### Response Example
(Returns a file stream, not a JSON object)
```

--------------------------------

### STDIO MCP Transport: Valid and Invalid Commands

Source: https://deepwiki.com/Chainlit/chainlit/9-platform-integrations

Examples demonstrating valid and invalid commands for the stdio MCP transport. Valid commands must begin with an executable whitelisted in `allowed_executables` in `config.toml`. Invalid commands use executables not present in the whitelist.

```text
# Valid commands (if npx is allowed):
"npx @modelcontextprotocol/server-filesystem /path/to/data"
"uvx mcp-server-git --repository /path/to/repo"

# Invalid command (not in allowed list):
"python custom_mcp_server.py"
```

--------------------------------

### Basic LangChain Integration with Chainlit

Source: https://deepwiki.com/Chainlit/chainlit/7-llm-integration

Demonstrates integrating LangChain's ChatOpenAI model with Chainlit. It utilizes LangchainTracer to automatically create steps for LLM calls within the Chainlit UI. This setup allows for visualizing the LLM interactions as part of the chat history.

```python
import chainlit as cl
from langchain_openai import ChatOpenAI
from langchain.schema import HumanMessage
from chainlit.langchain import LangchainTracer

@cl.on_chat_start
async def start():
    llm = ChatOpenAI(model="gpt-4")
    
@cl.on_message
async def main(message: cl.Message):
    tracer = LangchainTracer()
    llm = ChatOpenAI(model="gpt-4")
    
    response = await llm.ainvoke(
        [HumanMessage(content=message.content)],
        config={"callbacks": [tracer]}
    )
    
    await cl.Message(content=response.content).send()
```

--------------------------------

### GET /auth/config

Source: https://deepwiki.com/Chainlit/chainlit/12-configuration-reference

Returns authentication configuration including active OAuth providers and their settings.

```APIDOC
## GET /auth/config

### Description
Retrieves the current authentication provider configuration including OAuth client IDs and domains.

### Method
GET

### Endpoint
/auth/config

### Response
#### Success Response (200)
- **providers** (array) - List of configured OAuth providers
- **global_prompt** (string) - Optional global OAuth prompt setting

#### Response Example
{
  "providers": [
    {
      "type": "GITHUB",
      "client_id": "your_client_id",
      "domain": null
    }
  ],
  "global_prompt": "consent"
}
```

--------------------------------

### Test MCP Callback Registration with Asyncio

Source: https://deepwiki.com/Chainlit/chainlit/9-platform-integrations

The Python example provides an asynchronous test function that registers a callback using the @on_mcp_connect decorator and verifies its presence in the configuration. It imports necessary modules, defines a mock handler, and asserts that the callback is correctly attached. This snippet helps developers ensure their MCP connection handling logic is properly wired during testing.

```Python
# Example: Testing callback registration
async def test_on_mcp_connect(test_config: ChainlitConfig):
    from chainlit.callbacks import on_mcp_connect
    from mcp import ClientSession
    
    @on_mcp_connect
    async def handle_connect(connection, session: ClientSession):
        # Test implementation
        pass
    
    assert test_config.code.on_mcp_connect is not None
```

--------------------------------

### GET /project/file/{file_id}

Source: https://deepwiki.com/Chainlit/chainlit/10

Downloads a file by its ID. Checks session ownership and returns the file if authorized.

```APIDOC
## GET /project/file/{file_id}

### Description
Downloads a file specified by file_id. The requesting user must own the session associated with the file.

### Method
GET

### Endpoint
/project/file/{file_id}

### Parameters
#### Path Parameters
- **file_id** (string) - Required - The unique identifier of the file

#### Query Parameters
- **session_id** (string) - Required - The session identifier

### Request Example
```
GET /project/file/file123?session_id=session123
```

### Response
#### Success Response (200)
- Returns the file as a `FileResponse`

#### Response Example
```
<file_content>
```

### Error Responses
- **401 Unauthorized** - Invalid or missing session
- **403 Forbidden** - User does not own the session
- **404 Not Found** - File not found

```

--------------------------------

### GET /project/translations

Source: https://deepwiki.com/Chainlit/chainlit/12-configuration-reference

Returns translation JSON for the UI based on the requested language with fallback logic.

```APIDOC
## GET /project/translations

### Description
Returns UI translation strings for the specified language with fallback to parent language or English.

### Method
GET

### Endpoint
/project/translations

### Parameters
#### Query Parameters
- **lang** (string) - Required - IETF BCP 47 language tag (e.g., "fr-FR", "es-419")

### Response
#### Success Response (200)
- Key-value pairs of translation strings

#### Response Example
{
  "welcome_message": "Bienvenue",
  "send_button": "Envoyer"
}
```

--------------------------------

### Get Configured OAuth Providers in Python

Source: https://deepwiki.com/Chainlit/chainlit/8

Returns a list of IDs for OAuth providers that are fully configured with their required environment variables. It filters the global list of providers based on their `is_configured` status.

```python
def get_configured_oauth_providers():
    return [p.id for p in providers if p.is_configured()]
```

--------------------------------

### Display Custom Elements with AskElementMessage

Source: https://deepwiki.com/Chainlit/chainlit/4-step-and-message-system

Illustrates the use of AskElementMessage to display custom UI elements and wait for user interaction. The example shows a form with text fields. If the form is submitted, the response contains the form data.

```python
element = CustomElement(
    name="form",
    props={"fields": [{"name": "email", "type": "text"}]},
    content=""
)

response = await AskElementMessage(
    content="Please fill out the form:",
    element=element,
    timeout=90,
).send()

if response and response.get("submitted"):
    form_data = response.get("data")
```

--------------------------------

### GET /project/thread/{thread_id}

Source: https://deepwiki.com/Chainlit/chainlit/3

Retrieves a specific thread. Requires user authentication and thread author verification.

```APIDOC
## GET /project/thread/{thread_id}

### Description
Retrieves a specific thread. This endpoint requires user authentication and thread author verification.

### Method
GET

### Endpoint
/project/thread/{thread_id}

### Parameters
#### Path Parameters
- **thread_id** (string) - Required - The unique identifier of the thread to retrieve.

#### Query Parameters
None

#### Request Body
None

### Request Example
None

### Response
#### Success Response (200)
- **thread** (object) - The retrieved thread object.

#### Response Example
{
  "thread": {
    "id": "thread_123",
    "name": "My Chat",
    "createdAt": "2023-10-27T10:00:00Z",
    "updatedAt": "2023-10-27T10:05:00Z",
    "userId": "user_abc",
    "metadata": {}
  }
}
```

--------------------------------

### GET /project/share/{thread_id}

Source: https://deepwiki.com/Chainlit/chainlit/3-backend-system

Serves shared threads with custom authorization logic. It fetches the thread, checks its shared status, calls an optional callback for further authorization, and returns the thread or an error.

```APIDOC
## GET /project/share/{thread_id}

### Description
Serves shared threads with custom authorization logic. It fetches the thread, checks its shared status, calls an optional callback for further authorization, and returns the thread or an error.

### Method
GET

### Endpoint
/project/share/{thread_id}

### Parameters
#### Path Parameters
- **thread_id** (string) - Required - The ID of the thread to share.

### Response
#### Success Response (200)
- **Thread Object** - The shared thread data, with sensitive metadata stripped.

#### Response Example
```json
{
  "id": "thread-abcde",
  "createdAt": "2023-01-01T12:00:00Z",
  "updatedAt": "2023-01-01T12:05:00Z",
  "messages": [
    {
      "type": "element",
      "content": {
        "type": "text",
        "text": "Hello!"
      },
      "isUserMessage": true
    }
  ],
  "metadata": {
    "is_shared": true
  }
}
```

#### Error Response (404)
Returned if the thread is not found or not authorized to be shared.
```

--------------------------------

### GET /project/file/{file_id}

Source: https://deepwiki.com/Chainlit/chainlit/10-actions-and-interactivity

Retrieves an uploaded file using its unique identifier, with access control to ensure only the uploader can access it.

```APIDOC
## GET /project/file/{file_id}

### Description
Retrieves an uploaded file using its unique identifier. Access is restricted to the user who originally uploaded the file within a valid session.

### Method
GET

### Endpoint
/project/file/{file_id}

### Parameters
#### Path Parameters
- **file_id** (string) - Required - The unique identifier of the file to retrieve.

#### Query Parameters
- **session_id** (string) - Required - The identifier for the user session.

### Response
#### Success Response (200)
- **File Content** (binary) - The content of the requested file.

#### Response Example
*(Returns the binary content of the file)*
```

--------------------------------

### GET /project/share/{thread_id}

Source: https://deepwiki.com/Chainlit/chainlit/3

Allows viewing a shared thread if the 'is_shared' flag is true or if the `on_shared_thread_view` callback returns true. Returns 404 if access is denied.

```APIDOC
## GET /project/share/{thread_id}

### Description
Allows viewing a shared thread if the `metadata.is_shared` flag is `True`, or if the `on_shared_thread_view` callback returns `True`. Returns a 404 status code when access is denied to prevent leaking thread existence.

### Method
GET

### Endpoint
/project/share/{thread_id}

### Parameters
#### Path Parameters
- **thread_id** (string) - Required - The unique identifier of the shared thread to view.

#### Query Parameters
None

#### Request Body
None

### Request Example
None

### Response
#### Success Response (200)
- **thread** (object) - The shared thread object with sensitive metadata stripped.

#### Response Example
{
  "thread": {
    "id": "thread_123",
    "name": "Shared Chat",
    "createdAt": "2023-10-27T10:00:00Z",
    "updatedAt": "2023-10-27T10:05:00Z",
    "userId": "user_abc",
    "metadata": {
      "is_shared": true
    }
  }
}
```

--------------------------------

### GET /project/file/{file_id}

Source: https://deepwiki.com/Chainlit/chainlit/3

Retrieves a specific file by its ID. Access is restricted to authenticated users whose identifier matches the session owner, ensuring data privacy and security.

```APIDOC
## GET /project/file/{file_id}

### Description
Enables the download of a specific file previously uploaded to a project. Access is strictly controlled to ensure that only the authenticated user who owns the session can download their own files.

### Method
GET

### Endpoint
`/project/file/{file_id}?session_id={session_id}`

### Parameters
#### Path Parameters
- **file_id** (string) - Required - The unique identifier of the file to download.

#### Query Parameters
- **session_id** (string) - Required - The unique identifier for the user's session.

### Request Example
(No specific request body, typically a GET request with query parameters).

### Response
#### Success Response (200)
- The response will be the content of the requested file, with appropriate `Content-Type` and `Content-Disposition` headers.

#### Response Example
(The response body will be the file content itself, e.g., the bytes of a PDF or text file. Headers like `Content-Type: application/pdf` and `Content-Disposition: attachment; filename="example.pdf"` would typically be included).
```

--------------------------------

### Get OAuth Provider by ID in Python

Source: https://deepwiki.com/Chainlit/chainlit/8

Retrieves an OAuth provider object from a list by matching its ID. It iterates through a predefined list of providers and returns the first one that matches the given provider string. If no match is found, it returns None.

```python
def get_oauth_provider(provider: str) -> Optional[OAuthProvider]:
    for p in providers:
        if p.id == provider:
            return p
    return None
```

--------------------------------

### Custom Shared Thread Authorization Callback

Source: https://deepwiki.com/Chainlit/chainlit/3

Python example showing how to implement a custom authorization function for shared threads using the @cl.on_shared_thread_view decorator. Returns True to allow access based on thread metadata or viewer attributes, otherwise False.

```Python
@cl.on_shared_thread_view
async def allow_shared_view(thread: ThreadDict, viewer: Optional[User]) -> bool:
    """
    Custom authorization logic for shared threads.
    
    Args:
        thread: The thread being accessed
        viewer: The user viewing (may be None for anonymous)
    
    Returns:
        True to allow access, False to deny
    """
    metadata = thread.get("metadata") or {}
    
    # Example: Allow if thread is in "public" chat profile
    if metadata.get("chat_profile") == "public":
        return True
    
    # Example: Allow authenticated users in certain organizations
    if viewer and viewer.metadata.get("org") == "partner_org":
        return True
    
    return False
```

--------------------------------

### Enforce File Access Control in Python Backend

Source: https://deepwiki.com/Chainlit/chainlit/10-actions-and-interactivity

Ensures that only the user who uploaded a file can retrieve it via the GET endpoint. The snippet validates the session and compares user identifiers, raising HTTP 401 errors on unauthorized access. Used in backend/chainlit/server.py.

```Python
# In GET /project/file/{file_id}\nsession = WebsocketSession.get_by_id(session_id)\nfile_dict = session.files.get(file_id)\n\nif not current_user or not session.user:\n    raise HTTPException(401, "Unauthorized")\n\nif session.user.identifier != current_user.identifier:\n    raise HTTPException(401, "Unauthorized")
```

--------------------------------

### Fetch GitHub User Emails via OAuth API

Source: https://deepwiki.com/Chainlit/chainlit/8

Asynchronously retrieves user email addresses from GitHub's API using an OAuth token. Sends GET request to the emails endpoint and updates user metadata with the response. Requires valid OAuth token and user:email scope permission.

```python
# Second request: Get emails
emails_response = await client.get(
    urllib.parse.urljoin(self.user_info_url + "/", "emails"),
    headers={"Authorization": f"token {token}"},
)
emails = emails_response.json()
github_user.update({"emails": emails})
```

--------------------------------

### Initialize ChainlitDataLayer with S3 Storage

Source: https://deepwiki.com/Chainlit/chainlit/6

Shows how to import the ChainlitDataLayer and an S3 storage client, then instantiate the data layer with a PostgreSQL connection string, S3 bucket configuration, and optional debug logging enabled.

```python
from chainlit.data import ChainlitDataLayer
from chainlit.data.storage_clients import S3StorageClient

# Initialize with connection string
data_layer = ChainlitDataLayer(
    database_url="postgresql://user:pass@localhost/chainlit",
    storage_client=S3StorageClient(bucket="my-bucket"),
    show_logger=True  # Enable debug logging
)

```

--------------------------------

### LangChain Final Answer Streaming Logic in Chainlit

Source: https://deepwiki.com/Chainlit/chainlit/4

This Python code describes Chainlit's `LangchainTracer` logic for streaming final answers from agents. It uses a `FinalStreamHelper` to detect the start of the final answer by tracking specific tokens and then streams these tokens to a dedicated `Message` object, differentiating them from intermediate step outputs.

```python
# Tracks answer prefix tokens (default: ["Final", "Answer", ":"])
# Detects when final answer begins by comparing last N tokens
# Creates a Message object (self.final_stream) when answer detected
# Streams tokens to this message instead of step output
```

--------------------------------

### Present User Choices with AskActionMessage

Source: https://deepwiki.com/Chainlit/chainlit/4-step-and-message-system

Shows how to use the AskActionMessage class to present buttons for user selection. Actions are defined with names, labels, and values. The response contains the 'value' of the selected action.

```python
response = await AskActionMessage(
    content="Choose an option:",
    actions=[
        Action(name="option1", label="Option 1", value="1"),
        Action(name="option2", label="Option 2", value="2"),
    ],
    timeout=90,
).send()

if response:
    selected = response["value"]  # "1" or "2"
```

--------------------------------

### Basic OpenAI Instrumentation with Chainlit

Source: https://deepwiki.com/Chainlit/chainlit/7-llm-integration

Shows how to instrument the OpenAI Python client for seamless integration with Chainlit. Calling `instrument_openai()` once enables automatic step creation for all OpenAI API calls, simplifying the process of tracking LLM interactions in the UI without manual step management.

```python
import chainlit as cl
from openai import AsyncOpenAI
from chainlit.openai import instrument_openai

instrument_openai()  # Call once at module level

client = AsyncOpenAI()

@cl.on_message
async def main(message: cl.Message):
    response = await client.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": message.content}]
    )
    
    await cl.Message(content=response.choices[0].message.content).send()
```

--------------------------------

### Build Frontend and Copilot Assets

Source: https://deepwiki.com/Chainlit/chainlit/11-developer-guide

Build both the main frontend application and copilot widget using Vite. Produces static assets in dist directories for embedding into the Python package via the Hatch build hook.

```shell
pnpm buildUi
```

--------------------------------

### Publishing to PyPI via GitHub CLI

Source: https://deepwiki.com/Chainlit/chainlit/11-developer-guide

Command to trigger the `publish.yaml` GitHub Actions workflow to deploy a release to PyPI. It uses the `gh workflow run` command with a specific ref (e.g., `main`).

```shell
gh workflow run publish.yaml --ref main
```

--------------------------------

### OAuth Prompt Parameter

Source: https://deepwiki.com/Chainlit/chainlit/8

Documentation for the optional `prompt` parameter that controls the authentication experience.

```APIDOC
## OAuth Prompt Parameter

### Description
Optional `prompt` parameter that controls the authentication experience.

### Precedence
1. Provider-specific environment variable: `OAUTH_{PROVIDER}_PROMPT`
2. Global OAuth prompt: `OAUTH_PROMPT`
3. Provider's `default_prompt` attribute (if set)

### Common Prompt Values
- **"login"**: Forces re-authentication even if user has active session
- **"consent"**: Forces re-consent of permissions
- **"select_account"**: Allows user to choose between multiple accounts
- **"none"**: No prompts, fails if interaction required
```

--------------------------------

### Publishing to TestPyPI via GitHub CLI

Source: https://deepwiki.com/Chainlit/chainlit/11-developer-guide

Command to trigger the `publish.yaml` GitHub Actions workflow to deploy a release to TestPyPI. It uses the `gh workflow run` command with a specific ref and a force flag for `use_testpypi`.

```shell
gh workflow run publish.yaml --ref <branch> -f use_testpypi=true
```

--------------------------------

### Initialize SQLite Data Layer for Local Development

Source: https://deepwiki.com/Chainlit/chainlit/6

Sets up the SQLAlchemy data layer using SQLite for local development. It connects to a local 'chainlit.db' file and does not configure an external storage provider.

```python
from chainlit.data import SQLAlchemyDataLayer

data_layer = SQLAlchemyDataLayer(
    conninfo="sqlite+aiosqlite:///./chainlit.db",
    storage_provider=None  # No storage client for local dev
)
```

--------------------------------

### Instrument OpenAI/Mistral SDK Calls for Chainlit

Source: https://deepwiki.com/Chainlit/chainlit/4-step-and-message-system

Direct instrumentation for OpenAI and Mistral integrations wraps SDK calls to automatically create and send steps to Chainlit. The `on_new_generation` function captures generation details, timing, and constructs a 'llm' type step, sending it to the UI.

```python
# From openai/__init__.py lines 19-52
def on_new_generation(generation, timing):
    previous_steps = local_steps.get()
    parent_id = previous_steps[-1].id if previous_steps else None
    
    step = Step(
        name=generation.model if generation.model else generation.provider,
        type="llm",
        parent_id=parent_id,
    )
    step.generation = generation
    step.start = timestamp_utc(timing.get("start"))
    step.end = timestamp_utc(timing.get("end"))
    
    if isinstance(generation, ChatGeneration):
        step.input = generation.messages
        step.output = generation.message_completion
    else:
        step.input = generation.prompt
        step.output = generation.completion
    
    asyncio.create_task(step.send())
```

--------------------------------

### Storage Provider Configuration

Source: https://deepwiki.com/Chainlit/chainlit/12-configuration-reference

Environment variables required for configuring various cloud storage providers.

```APIDOC
## Storage Provider Configuration

### Description
Environment variables for configuring S3, GCS, and Azure Blob storage providers.

### Variables
- **S3_ENDPOINT** (string) - S3-compatible endpoint URL
- **S3_REGION** (string) - AWS region
- **S3_ACCESS_KEY_ID** (string) - AWS access key ID
- **S3_SECRET_ACCESS_KEY** (string) - AWS secret access key
- **S3_BUCKET** (string) - S3 bucket name
- **GCS_BUCKET** (string) - Google Cloud Storage bucket name
- **AZURE_ACCOUNT_URL** (string) - Azure Storage account URL
- **AZURE_CONTAINER** (string) - Azure Blob container name
```

--------------------------------

### LangChain Integration: Tracer and Step Mapping

Source: https://deepwiki.com/Chainlit/chainlit/4-step-and-message-system

Explains the integration pattern with LangChain using the `LangchainTracer` class. It provides a key mapping between LangChain's run types (e.g., 'agent', 'chain') and Chainlit's step types (e.g., 'run', 'llm', 'tool').

```python
# From backend/chainlit/langchain/callbacks.py526-570

# Key mapping:
# LangChain run_type| Chainlit step type  
# ---|---
# "agent"| "run"  
# "chain" (root)| "run"  
# "llm"| "llm"  
# "retriever"| "tool"  
# "tool"| "tool"  
# "embedding"| "embedding"
```

--------------------------------

### Set Available Commands - Python

Source: https://deepwiki.com/Chainlit/chainlit/10-actions-and-interactivity

Demonstrates how the backend can dynamically set the list of available commands using `emitter.set_commands()`. These commands are then sent to the frontend via Socket.IO.

```python
commands = [
    {"id": "Picture", "icon": "image", "description": "Use DALL-E"},
    {"id": "Search", "icon": "globe", "description": "Find on the web", 
     "button": True}
]

await cl.context.emitter.set_commands(commands)
```

--------------------------------

### Manual Step Creation: Context Manager

Source: https://deepwiki.com/Chainlit/chainlit/4

This pattern demonstrates creating a step using a context manager (`async with`). Input and output are assigned within the block, and the step is automatically sent and updated upon exiting the block.

```python
async with Step(name="fetch_data", type="tool") as step:
    step.input = {"url": url}
    data = await fetch(url)
    step.output = data
```

--------------------------------

### OAuth Provider Configuration

Source: https://deepwiki.com/Chainlit/chainlit/12-configuration-reference

Environment variable patterns for configuring various OAuth providers.

```APIDOC
## OAuth Provider Configuration

### Description
Standard environment variable patterns for OAuth provider configuration.

### Supported Providers
GITHUB, GITHUB_ENTERPRISE, GOOGLE, AZURE_AD, AZURE_AD_HYBRID, OKTA, AUTH0, DESCOPE, COGNITO, GITLAB

### Variable Patterns
- **OAUTH_<PROVIDER>_CLIENT_ID** - OAuth client ID
- **OAUTH_<PROVIDER>_CLIENT_SECRET** - OAuth client secret
- **OAUTH_<PROVIDER>_DOMAIN** - Provider domain (for Auth0, Okta)
- **OAUTH_<PROVIDER>_SCOPE** - OAuth scope
- **OAUTH_<PROVIDER>_PROMPT** - OAuth prompt parameter
- **OAUTH_PROMPT** - Global OAuth prompt override

### Example Configurations
```
OAUTH_GITHUB_CLIENT_ID=your_client_id
OAUTH_GITHUB_CLIENT_SECRET=your_client_secret
OAUTH_AZURE_AD_TENANT_ID=your_tenant_id
```
```

--------------------------------

### Configuration Reference

Source: https://deepwiki.com/Chainlit/chainlit/3

Provides an overview of configurable options for features like thread sharing and session management.

```APIDOC
## Configuration Reference

### Thread Sharing Configuration

- **`[features] allow_thread_sharing`** (boolean): Enables or disables the thread sharing UI and backend functionality. Requires the `on_shared_thread_view` callback to be implemented.

### Project Configuration

- **`[project] session_timeout`** (integer): Specifies the duration in seconds for which a session is saved when the connection is lost.
- **`[project] persist_user_env`** (boolean): Determines whether user environment variables should be persisted to thread metadata.
```

--------------------------------

### Calculate Performance Metrics for LLM Generations

Source: https://deepwiki.com/Chainlit/chainlit/4-step-and-message-system

Demonstrates the calculation of performance metrics like duration and token throughput for LLM generations. This is typically done within callback handlers to track efficiency.

```python
# From langchain/callbacks.py lines 591-596
duration = time.time() - chat_start["start"]
if duration and chat_start["token_count"]:
    throughput = chat_start["token_count"] / duration
else:
    throughput = None
```

--------------------------------

### AskFileMessage API

Source: https://deepwiki.com/Chainlit/chainlit/10-actions-and-interactivity

Demonstrates how to use the AskFileMessage to request file uploads with specific constraints.

```APIDOC
## AskFileMessage API

### Description
The `AskFileMessage` API allows you to prompt users for file uploads with configurable constraints such as accepted MIME types, maximum number of files, maximum file size, and timeout duration.

### Usage Example
```python
files = await cl.AskFileMessage(
    content="Upload your document",
    accept=["application/pdf", "text/plain"],
    max_size_mb=10,
    max_files=3,
    timeout=120
).send()
```

### AskFileSpec Fields
- **accept** (`List[str]` or `Dict[str, List[str]]`): Specifies allowed MIME types or a mapping from MIME types to file extensions.
- **max_files** (`int`): The maximum number of files the user can upload.
- **max_size_mb** (`int`): The maximum size for each file in megabytes.
- **timeout** (`int`): The time in seconds to wait for the user's response before canceling.
```

--------------------------------

### HTML Template Generation

Source: https://deepwiki.com/Chainlit/chainlit/3-backend-system

Generates the index HTML file dynamically. It includes SEO meta tags, custom theme injection, links to custom CSS/JS files, font imports, and path rewriting for sub-path deployments.

```APIDOC
## HTML Template Generation

### Description
Generates the index HTML file dynamically. It includes SEO meta tags, custom theme injection, links to custom CSS/JS files, font imports, and path rewriting for sub-path deployments.

### Method
(Internal function, not directly an HTTP endpoint)

### Endpoint
(Generates the root HTML for the application)

### Parameters
#### Function Parameter
- **root_path** (string) - Required - The root path of the application for path rewriting.

### Response
#### Success Response
- **HTML String** - A complete HTML document string.

### Request Example
(This is typically called internally by the server)

### Response Example
(Returns a full HTML document, not a JSON object)
```

--------------------------------

### Nested Steps with LlamaIndex and Chainlit

Source: https://deepwiki.com/Chainlit/chainlit/7-llm-integration

Illustrates integrating LlamaIndex with Chainlit using a callback handler. This approach automatically generates steps for both the retrieval process (including source nodes) and the subsequent LLM generation, providing a detailed view of the query execution flow within Chainlit.

```python
import chainlit as cl
from llama_index.core import VectorStoreIndex, SimpleDirectoryReader
from chainlit.llama_index import LlamaIndexCallbackHandler

@cl.on_chat_start
async def start():
    documents = SimpleDirectoryReader("data").load_data()
    index = VectorStoreIndex.from_documents(documents)
    cl.user_session.set("index", index)

@cl.on_message
async def main(message: cl.Message):
    index = cl.user_session.get("index")
    handler = LlamaIndexCallbackHandler()
    
    query_engine = index.as_query_engine(callbacks=[handler])
    response = query_engine.query(message.content)
    
    await cl.Message(content=str(response)).send()
```

--------------------------------

### Configure SQLAlchemyDataLayer with PostgreSQL and GCS Storage

Source: https://deepwiki.com/Chainlit/chainlit/6

Demonstrates initializing the SQLAlchemyDataLayer for production use with a PostgreSQL asyncpg connection, enabling SSL, and specifying a Google Cloud Storage client for blob handling.

```python
from chainlit.data import SQLAlchemyDataLayer
from chainlit.data.storage_clients import GCSStorageClient

# PostgreSQL for production
data_layer = SQLAlchemyDataLayer(
    conninfo="postgresql+asyncpg://user:pass@localhost/chainlit",
    ssl_require=True,
    storage_provider=GCSStorageClient(bucket_name="my-bucket"),
    user_thread_limit=1000
)

```

--------------------------------

### Keycloak OAuth Provider

Source: https://deepwiki.com/Chainlit/chainlit/8

Implementation for Keycloak OAuth provider with required environment variables and endpoints.

```APIDOC
## Keycloak OAuth Provider

### Description
Implementation for Keycloak OAuth provider with required environment variables and endpoints.

### Environment Variables
- **OAUTH_KEYCLOAK_CLIENT_ID** (string) - Required - Client ID for Keycloak
- **OAUTH_KEYCLOAK_CLIENT_SECRET** (string) - Required - Client secret for Keycloak
- **OAUTH_KEYCLOAK_REALM** (string) - Required - Realm for Keycloak
- **OAUTH_KEYCLOAK_BASE_URL** (string) - Required - Base URL for Keycloak
- **OAUTH_KEYCLOAK_NAME** (string) - Optional - Defaults to "keycloak"
- **OAUTH_KEYCLOAK_PROMPT** (string) - Optional - Controls authentication experience

### Endpoints
`{base_url}/realms/{realm}/protocol/openid-connect/{auth|token|userinfo}`

### Scopes
`profile email openid`

### Special Features
Stores refresh token for session management

### User Identifier
Email address
```

--------------------------------

### Python: MCP Connection Callback with @cl.on_mcp_connect

Source: https://deepwiki.com/Chainlit/chainlit/9-platform-integrations

This Python code defines an asynchronous function `handle_mcp_connect` decorated with `@cl.on_mcp_connect`. This function is executed when an MCP connection is established, allowing for session configuration and registration of tools and resources using the provided `McpConnection` and `ClientSession` objects.

```python
from mcp import ClientSession
from chainlit.mcp import McpConnection

@cl.on_mcp_connect
async def handle_mcp_connect(
    connection: McpConnection,
    session: ClientSession
) -> None:
    """
    Args:
        connection: McpConnection object with name and transport info
        session: MCP ClientSession for interacting with the server
    """
    # List available tools
    tools = await session.list_tools()
    
    # Configure resources
    resources = await session.list_resources()
```

--------------------------------

### Chainlit Step Streaming Tokens

Source: https://deepwiki.com/Chainlit/chainlit/4-step-and-message-system

Enables real-time, token-by-token display of responses, commonly used for LLM outputs. This method provides a dynamic user experience.

```python
async def stream_token(self, token: str, is_sequence=False, is_input=False):
    # ... implementation details ...
    pass
```

--------------------------------

### Instantiate Step Directly in Python

Source: https://deepwiki.com/Chainlit/chainlit/4

Direct instantiation creates a Step object with specified parameters for custom control. It requires importing the Step class. Inputs include name, type, and optional metadata; outputs are the configured Step instance. Limitations include manual management of all attributes.

```python
step = Step(
    name="my_operation",
    type="tool",
    parent_id=optional_parent_id,
    metadata={"key": "value"}
)
```

--------------------------------

### Error Handling

Source: https://deepwiki.com/Chainlit/chainlit/8

Documentation for consistent error handling patterns across all provider implementations.

```APIDOC
## Error Handling

### Description
Consistent error handling patterns across all provider implementations.

### Missing Access Token
If the token exchange response does not contain an `access_token`, an `HTTPException` is raised with status code 400 and detail "Access token missing in the response".

### HTTP Request Failures
All HTTP requests use `response.raise_for_status()` to automatically raise exceptions for 4xx/5xx responses.

### Provider Not Configured
When a provider's required environment variables are not set, `is_configured()` returns `False`, and the provider is excluded from the available providers list returned by `get_configured_oauth_providers()`.
```

--------------------------------

### React Client Package Definition (JSON)

Source: https://deepwiki.com/Chainlit/chainlit/5-frontend-system

This JSON snippet represents the package definition for the `@chainlit/react-client` library. It specifies the package name, version, entry points (CommonJS and ES Module), and TypeScript definitions.

```json
{
  "name": "@chainlit/react-client",
  "version": "0.3.0",
  "main": "dist/index.js",
  "module": "dist/index.mjs",
  "types": "dist/index.d.ts"
}
```

--------------------------------

### Enable MCP Features in config.toml

Source: https://deepwiki.com/Chainlit/chainlit/9-platform-integrations

This configuration snippet shows how to explicitly enable MCP and its various transport methods (SSE, streamable-http, stdio) within the `config.toml` file. Ensure MCP features are opt-in by setting `enabled = true` for the desired sections. The `stdio` transport also allows specifying allowed executables.

```toml
[features.mcp]
    enabled = false  # Must enable this first

[features.mcp.sse]
    enabled = true

[features.mcp.streamable-http]
    enabled = true

[features.mcp.stdio]
    enabled = true
    allowed_executables = ["npx", "uvx"]
```

--------------------------------

### Chainlit Message Class Constructor

Source: https://deepwiki.com/Chainlit/chainlit/4-step-and-message-system

Defines the `Message` class for standard assistant messages, supporting optional actions, elements, and automatic JSON serialization for dictionary content.

```python
Message(
    content: Union[str, Dict],
    author: Optional[str] = None,
    language: Optional[str] = None,
    actions: Optional[List[Action]] = None,
    elements: Optional[List[ElementBased]] = None,
    type: MessageStepType = "assistant_message",
    metadata: Optional[Dict] = None,
    tags: Optional[List[str]] = None,
    id: Optional[str] = None,
    parent_id: Optional[str] = None,
    command: Optional[str] = None,
    created_at: Union[str, None] = None,
)
```

--------------------------------

### Request File Uploads with AskFileMessage

Source: https://deepwiki.com/Chainlit/chainlit/4-step-and-message-system

Demonstrates how to use the AskFileMessage class to request file uploads from the user. It specifies accepted file types, maximum size and number of files, and a timeout. The code then processes the uploaded files if any are provided.

```python
files = await AskFileMessage(
    content="Upload your documents",
    accept=["application/pdf", "text/plain"],
    max_size_mb=10,
    max_files=3,
    timeout=90,
).send()

if files:
    for file in files:
        # file.id, file.name, file.path, file.size, file.type
        process_file(file.path)
```

--------------------------------

### Chainlit Step Direct Instantiation Pattern

Source: https://deepwiki.com/Chainlit/chainlit/4-step-and-message-system

Allows for manual control over Step creation and lifecycle. This method is useful for complex scenarios where automatic management is insufficient.

```python
step = Step(name="My Step", type="llm")
await step.send()  # Send to UI and persist

# Stream tokens
await step.stream_token("Hello ")
await step.stream_token("world")

# Update with final output
step.output = "Final result"
await step.update()
```

--------------------------------

### Running E2E Tests with Cypress CLI

Source: https://deepwiki.com/Chainlit/chainlit/11-developer-guide

Commands to execute End-to-End tests using Cypress. Supports running all tests, specific tests, multiple tests, pattern matching, and interactive debugging mode. These commands utilize the pnpm package manager.

```shell
# Run all tests
pnpm test

# Run specific test
pnpm test -- --spec cypress/e2e/copilot

# Run multiple tests
pnpm test -- --spec "cypress/e2e/copilot,cypress/e2e/data_layer"

# Run with pattern
pnpm test -- --spec "cypress/e2e/**/async-*"

# Interactive mode (debugging)
pnpm test:interactive
```

--------------------------------

### Configure pnpm Workspace with .npmrc

Source: https://deepwiki.com/Chainlit/chainlit/11-developer-guide

Configure pnpm workspace settings to control lockfile sharing, hoist patterns for development tools, and disable side-effects cache for fresh builds. Ensures consistent dependency resolution across the monorepo.

```ini
shared-workspace-lockfile=false
public-hoist-pattern[]=*eslint*
public-hoist-pattern[]=*prettier*
public-hoist-pattern[]=@types*
side-effects-cache=false
```

--------------------------------

### Cypress Test Matrix Configuration

Source: https://deepwiki.com/Chainlit/chainlit/11-developer-guide

Configuration snippet from `e2e-tests.yaml` defining the matrix strategy for running Cypress E2E tests across different operating systems.

```yaml
strategy:
  matrix:
    os: [ubuntu-latest, windows-latest]
```

--------------------------------

### POST /project/action

Source: https://deepwiki.com/Chainlit/chainlit/10-actions-and-interactivity

Handles user interactions by processing action button clicks. It validates the session, finds the appropriate handler for the action, and invokes it.

```APIDOC
## POST /project/action

### Description
Handles user interactions by processing action button clicks. It validates the session, finds the appropriate handler for the action, and invokes it.

### Method
POST

### Endpoint
/project/action

### Parameters
#### Request Body
- **action** (object) - Required - Action dictionary containing name, label, payload, etc.
- **sessionId** (string) - Required - The current session identifier.

### Request Example
```json
{
  "action": {
    "name": "my_action",
    "label": "Click Me",
    "payload": {"key": "value"}
  },
  "sessionId": "user_session_123"
}
```

### Response
#### Success Response (200)
- **status** (string) - Indicates the success of the operation.

#### Response Example
```json
{
  "status": "success"
}
```
```

--------------------------------

### Configure OAuth Providers with Environment Variables

Source: https://deepwiki.com/Chainlit/chainlit/12-configuration-reference

Configure OAuth providers by setting environment variables in the format OAUTH_<PROVIDER>_<SETTING>. This includes client IDs, secrets, domains, scopes, and prompt parameters for various authentication services.

```shell
OAUTH_GITHUB_CLIENT_ID=your_client_id
OAUTH_GITHUB_CLIENT_SECRET=your_client_secret
OAUTH_GOOGLE_CLIENT_ID=your_client_id
OAUTH_GOOGLE_CLIENT_SECRET=your_client_secret
OAUTH_AZURE_AD_CLIENT_ID=your_client_id
OAUTH_AZURE_AD_CLIENT_SECRET=your_secret_access_key
OAUTH_AZURE_AD_TENANT_ID=your_tenant_id
```

--------------------------------

### Chainlit Context Initialization Functions

Source: https://deepwiki.com/Chainlit/chainlit/8-authentication

These functions are responsible for initializing different types of user sessions within Chainlit. `init_http_context` is used for REST API requests and accepts optional user, auth token, and environment details. `init_ws_context` is designed for real-time WebSocket connections.

```python
def init_http_context(user=None, token=None, env=None):
    """Creates HTTPSession for REST API requests."""
    pass

def init_ws_context():
    """Creates WebsocketSession for real-time WebSocket connections."""
    pass
```

--------------------------------

### POST /project/file

Source: https://deepwiki.com/Chainlit/chainlit/3-backend-system

Handles file uploads with validation for spontaneous uploads or ask-file scenarios. It checks enable conditions, validates MIME type and file size, persists the file, and returns a FileDict.

```APIDOC
## POST /project/file

### Description
Handles file uploads with validation for spontaneous uploads or ask-file scenarios. It checks enable conditions, validates MIME type and file size, persists the file, and returns a FileDict.

### Method
POST

### Endpoint
/project/file

### Parameters
#### Request Body
- **file** (file) - Required - The file to upload.
- **metadata** (object) - Optional - Additional metadata for the file.

### Request Example
```json
{
  "file": "<binary file data>",
  "metadata": {
    "description": "User provided image"
  }
}
```

### Response
#### Success Response (200)
- **id** (string) - The unique identifier of the uploaded file.
- **name** (string) - The name of the file.
- **type** (string) - The MIME type of the file.
- **size** (integer) - The size of the file in bytes.

#### Response Example
```json
{
  "id": "file-12345",
  "name": "example.jpg",
  "type": "image/jpeg",
  "size": 102400
}
```
```

--------------------------------

### Configure Storage Providers with Environment Variables

Source: https://deepwiki.com/Chainlit/chainlit/12-configuration-reference

Set environment variables to configure various storage providers like S3, GCS, and Azure. These variables define endpoints, regions, credentials, and bucket names necessary for file storage integration.

```shell
S3_ENDPOINT=your_s3_endpoint
S3_REGION=your_s3_region
S3_ACCESS_KEY_ID=your_access_key_id
S3_SECRET_ACCESS_KEY=your_secret_access_key
S3_BUCKET=your_s3_bucket
GCS_BUCKET=your_gcs_bucket
AZURE_ACCOUNT_URL=your_azure_account_url
AZURE_CONTAINER=your_azure_container
```

--------------------------------

### Listing Threads Endpoint Response Structure (JSON)

Source: https://deepwiki.com/Chainlit/chainlit/3

Shows the expected JSON response structure for the `/project/threads` endpoint, which returns a paginated list of threads. It includes `pageInfo` (hasNextPage, startCursor, endCursor) and a list of `ThreadDict` objects.

```JSON
{
  "pageInfo": {
    "hasNextPage": true,
    "startCursor": "cursor_string",
    "endCursor": "cursor_string"
  },
  "data": [/* ThreadDict objects */]
}
```

--------------------------------

### OpenAI Instrumentation for Steps

Source: https://deepwiki.com/Chainlit/chainlit/4

Enables automatic step creation for OpenAI API calls. After calling `instrument_openai()`, each completion request made via the OpenAI client will result in a corresponding step being logged in Chainlit, capturing the interaction.

```python
from chainlit.openai import instrument_openai

instrument_openai()
# Steps created automatically for each completion
response = client.chat.completions.create(...)
```

--------------------------------

### POST /project/file

Source: https://deepwiki.com/Chainlit/chainlit/10-actions-and-interactivity

Handles file uploads from users. This endpoint is used for both prompted uploads via AskFileMessage and spontaneous file uploads.

```APIDOC
## POST /project/file

### Description
Handles file uploads from users. This endpoint validates uploaded files against configured constraints (MIME type, size, count) and stores them.

### Method
POST

### Endpoint
/project/file

### Parameters
#### Request Body
- **files** (File) - Required - The file(s) to be uploaded.
- **sessionId** (string) - Required - The identifier for the current user session.
- **parent_id** (string) - Optional - Identifier if the file is related to a specific message.

### Response
#### Success Response (200)
- **status** (string) - Indicates the success of the file upload.

#### Response Example
```json
{
  "status": "success"
}
```
```

--------------------------------

### POST /project/file

Source: https://deepwiki.com/Chainlit/chainlit/10

Handles file uploads via multipart form data. Validates file type, size, and user session before storing the file and registering it in the session.

```APIDOC
## POST /project/file

### Description
Accepts a file upload via multipart form data along with a session ID. Performs validation checks and stores the file if all conditions are met.

### Method
POST

### Endpoint
/project/file

### Parameters
#### Request Body
- **file** (file) - Required - The file to upload
- **session_id** (string) - Required - The session identifier

### Request Example
```
POST /project/file
Content-Type: multipart/form-data

file: <file_data>
session_id: "session123"
```

### Response
#### Success Response (200)
- **id** (string) - Unique file identifier
- **name** (string) - Original file name
- **type** (string) - MIME type of the file
- **size** (integer) - Size of the file in bytes

#### Response Example
```
{
  "id": "file123",
  "name": "example.txt",
  "type": "text/plain",
  "size": 1024
}
```

### Error Responses
- **400 Bad Request** - Feature not enabled, invalid MIME type, invalid extension, file size exceeded, file count exceeded
- **401 Unauthorized** - Invalid or missing session
- **422 Unprocessable Entity** - User not authorized

```

--------------------------------

### Chainlit AskFileMessage API for File Uploads

Source: https://deepwiki.com/Chainlit/chainlit/10-actions-and-interactivity

Demonstrates the usage of the AskFileMessage class to prompt users for file uploads. It showcases how to configure constraints such as allowed MIME types, maximum number of files, maximum file size, and timeout duration. The response, when successful, is a list of uploaded files.

```python
files = await cl.AskFileMessage(
    content="Upload your document",
    accept=["application/pdf", "text/plain"],
    max_size_mb=10,
    max_files=3,
    timeout=120
).send()
```

--------------------------------

### Fetch GitHub User Profile and Email in Python

Source: https://deepwiki.com/Chainlit/chainlit/8

Demonstrates fetching a GitHub user's profile information and then making a subsequent request to retrieve their email addresses. This is a special case for GitHub's API, requiring two separate calls.

```python
# First request: Get user profile
user_response = await client.get(
    self.user_info_url,
    headers={"Authorization": f"token {token}"},
)
github_user = user_response.json()
```

--------------------------------

### HTTP Routes and Endpoints

Source: https://deepwiki.com/Chainlit/chainlit/2-architecture-overview

The FastAPI application exposes various HTTP routes for authentication, project management, and asset serving. Each route is associated with a specific method and handler location.

```APIDOC
## HTTP Routes and Endpoints

### Description
The FastAPI application exposes several key HTTP routes for various functionalities, including authentication, project management, and asset serving.

### Method
GET, POST

### Endpoint
Various routes, including `/auth/oauth/{provider_id}`, `/auth/oauth/{provider_id}/callback`, `/login`, `/logout`, `/project/settings`, `/project/translations`, `/project/threads`, `/project/file`, `/project/file/{file_id}`, `/public/{filename:path}`, `/avatars/{name}`

### Parameters
#### Path Parameters
- `provider_id` (string) - Required - OAuth provider identifier.
- `file_id` (string) - Required - File identifier.
- `filename` (string) - Required - Filename for public assets.
- `name` (string) - Required - Avatar name.

#### Query Parameters
- N/A

#### Request Body
- N/A

### Request Example
N/A

### Response
#### Success Response (200)
- N/A

#### Response Example
N/A

| Route Pattern | Method | Purpose | Handler Location |
|---|---|---|---|
| `/auth/oauth/{provider_id}` | GET | Initiate OAuth flow | `backend/chainlit/server.py604-636` |
| `/auth/oauth/{provider_id}/callback` | GET | OAuth callback | `backend/chainlit/server.py639-694` |
| `/login` | POST | Password login | `backend/chainlit/server.py530-547` |
| `/logout` | POST | User logout | `backend/chainlit/server.py551-558` |
| `/project/settings` | GET | Project configuration | `backend/chainlit/server.py797-859` |
| `/project/translations` | GET | UI translations | `backend/chainlit/server.py779-794` |
| `/project/threads` | POST | List user threads | `backend/chainlit/server.py915-975` |
| `/project/file` | POST | Upload file | `backend/chainlit/server.py1044-1092` |
| `/project/file/{file_id}` | GET | Download file | `backend/chainlit/server.py1095-1152` |
| `/public/{filename:path}` | GET | Serve public assets | `backend/chainlit/server.py260-276` |
| `/avatars/{name}` | GET | Serve avatar images | `backend/chainlit/server.py1220-1250` |
```

--------------------------------

### Use Context Manager for Step Lifecycle in Python

Source: https://deepwiki.com/Chainlit/chainlit/4

Context manager pattern for Steps allows resource management with async with statements. It automatically handles initialization and cleanup. Inputs are Step parameters; outputs are set within the block. Limitations include requirement for async context if using await inside.

```python
async with Step(name="fetch_data", type="tool") as step:
    step.input = {"query": "search term"}
    data = await fetch_from_api()
    step.output = data
```

--------------------------------

### File Download API

Source: https://deepwiki.com/Chainlit/chainlit/10-actions-and-interactivity

Allows downloading files that have been previously uploaded. Requires a session ID to identify the user's session.

```APIDOC
## GET /project/file/{file_id}

### Description
Downloads a file previously uploaded to the Chainlit backend.

### Method
GET

### Endpoint
/project/file/{file_id}

### Parameters
#### Path Parameters
- **file_id** (string) - Required - The ID of the file to download.

#### Query Parameters
- **session_id** (string) - Required - The ID of the session associated with the file.

#### Request Body
None

### Request Example
None

### Response
#### Success Response (200)
- **File Content** (binary) - The content of the requested file.

#### Response Example
None (returns file content directly)
```

--------------------------------

### AskActionMessage Structure

Source: https://deepwiki.com/Chainlit/chainlit/10-actions-and-interactivity

Details the structure of the AskActionMessage and the response format when a user selects an action.

```APIDOC
## AskActionMessage Structure

### Description
The `AskActionMessage` prompts the user to select from a list of actions, which are displayed as buttons or a list on the frontend. The response includes the selected action's details.

### Response from Frontend
When a user selects an action, the frontend sends a response containing:
- **name** (string): The identifier of the selected action.
- **payload** (object): Data associated with the action.
- **label** (string): Display text for the action.
- **tooltip** (string): Tooltip text for the action.
- **forId** (string): Identifier for the element associated with the action.
- **id** (string): Unique identifier for the action.
```

--------------------------------

### Dynamic Configuration Overrides for Chat Profiles (Python)

Source: https://deepwiki.com/Chainlit/chainlit/12-configuration-reference

Define a ChatProfile with dynamic configuration overrides using Chainlit's Python SDK. This allows customizing UI settings and feature flags for specific chat profiles.

```python
from chainlit.types import ChatProfile
from chainlit.config import ChainlitConfigOverrides, UISettings, FeaturesSettings, McpFeature

profile = ChatProfile(
    name="Advanced",
    markdown_description="Advanced profile with MCP enabled",
    config_overrides=ChainlitConfigOverrides(
        ui=UISettings(name="Advanced Assistant", cot="tool_call"),
        features=FeaturesSettings(
            mcp=McpFeature(enabled=True)
        )
    )
)
```

--------------------------------

### MCP Configuration in TOML

Source: https://deepwiki.com/Chainlit/chainlit/9

Shows the configuration structure for MCP features in config.toml, including enabling/disabling transports and specifying allowed executables for security.

```toml
[features.mcp]
enabled = false
stdio.enabled = true
stdio.allowed_executables = ["npx", "uvx"]
sse.enabled = true
streamable-http.enabled = true
```

--------------------------------

### Attach Generation Metadata to Chat Step (Python)

Source: https://deepwiki.com/Chainlit/chainlit/4

Demonstrates how to attach generation metadata, specifically for chat models, to a Chainlit step. This includes setting provider, model, messages, and completion details. The generation object is serialized when the step is converted to a dictionary.

```python
from literalai import ChatGeneration

step.generation = ChatGeneration(
    provider="openai",
    model="gpt-4",
    messages=[...],
    message_completion={...},
    token_count=150
)
```

--------------------------------

### Chainlit Configuration Settings

Source: https://deepwiki.com/Chainlit/chainlit/3

This TOML snippet shows global configuration options for Chainlit features, including thread sharing enablement, session timeout duration during connection loss, and whether to persist user environment variables to thread metadata.

```toml
[features]
# Enable thread sharing UI + backend (requires on_shared_thread_view callback)
allow_thread_sharing = false

[project]
# Duration (seconds) session is saved when connection is lost
session_timeout = 3600

# Whether to persist user environment variables to thread metadata
persist_user_env = false
```

--------------------------------

### Spontaneous File Uploads Configuration

Source: https://deepwiki.com/Chainlit/chainlit/10-actions-and-interactivity

Details how to enable and configure spontaneous file uploads, allowing users to attach files to any message.

```APIDOC
## Spontaneous File Uploads Configuration

### Description
Enables users to attach files to any message, not just in response to `AskFileMessage` prompts. Configuration is done via `config.toml`.

### Configuration Example (`config.toml`)
```toml
[features.spontaneous_file_upload]
    enabled = true
    accept = ["image/*", "application/pdf"]
    max_files = 20
    max_size_mb = 500
```

### Configuration Fields
- **enabled** (`boolean`): Set to `true` to enable the feature.
- **accept** (`List[str]`): A list of allowed MIME types or file extensions for uploaded files.
- **max_files** (`int`): The maximum number of files allowed per upload.
- **max_size_mb** (`int`): The maximum size for each file in megabytes.

The `SpontaneousFileUploadFeature` configuration is checked when a file upload request does not have a `parent_id`, indicating a spontaneous upload.
```

--------------------------------

### Manage Step Context with local_steps

Source: https://deepwiki.com/Chainlit/chainlit/4-step-and-message-system

Explains how the `local_steps` context variable manages a stack of active steps to establish parent-child relationships. It details the push operation on entering a step and the pop operation on exiting.

```python
# From backend/chainlit/step.py438-491 backend/chainlit/context.py23

# How it works:
#   1. When a step enters (__aenter__ or __enter__), it:
#      * Gets current stack: `previous_steps = local_steps.get() or []`
#      * Uses last step as parent: `parent_step = previous_steps[-1]`
#      * Pushes itself: `local_steps.set(previous_steps + [self])`
#   2. When a step exits (__aexit__ or __exit__), it:
#      * Pops itself: `current_steps.remove(self)`
#      * Restores stack: `local_steps.set(current_steps)`
```

--------------------------------

### LlamaIndex Integration for Steps

Source: https://deepwiki.com/Chainlit/chainlit/4

Integrates Chainlit's callback handling with LlamaIndex. By using the `LlamaIndexCallbackHandler`, Chainlit can automatically generate steps for LLM calls, retrievals, and tool invocations performed within a LlamaIndex query engine.

```python
from chainlit.llama_index import LlamaIndexCallbackHandler

handler = LlamaIndexCallbackHandler()
index.as_query_engine(callback_manager=CallbackManager([handler]))
# Steps created for LLM calls, retrievals, and tool calls
```

--------------------------------

### Pre-commit Hooks Configuration (JavaScript/TypeScript/Python)

Source: https://deepwiki.com/Chainlit/chainlit/11-developer-guide

Configuration for `lint-staged.config.js` defining pre-commit checks for different file types. It includes formatting with Prettier, linting with ESLint and Ruff, TypeScript type checking, and ActionLint for workflow files.

```javascript
// lint-staged.config.js
module.exports = {
  '**/*.{js,jsx,ts,tsx}': ['npx prettier --write', 'npx eslint --fix'],
  '**/*.{ts,tsx}': [() => 'tsc --skipLibCheck --noEmit'],
  '**/*.py': [
    'uv run --project backend ruff check --fix',
    'uv run --project backend ruff format',
    () => 'pnpm run lintPython'
  ],
  '.github/workflows/**': ['actionlint']
};
```

--------------------------------

### Input/Output Handling in Type Conversion (Python)

Source: https://deepwiki.com/Chainlit/chainlit/6

This snippet from LiteralToChainlitConverter handles input extraction for steps by prioritizing content fields or serializing to JSON. It depends on JSON module and step objects with input attributes. Outputs a string representation; limitations include assuming dict-like inputs and empty handling.

```python
input = (step.input or {}).get("content") or (
    json.dumps(step.input) if step.input and step.input != {} else ""
)
```

--------------------------------

### Standardize Tools Format

Source: https://deepwiki.com/Chainlit/chainlit/7

Converts both function and tool specifications to a uniform structure. This ensures consistency in how tools are represented and processed within the Chainlit framework.

```python
[{\n    "type": "function",\n    "function": { /* function spec */ }\n  }]
```

--------------------------------

### Configure SSL for Database Engine in SQLAlchemyDataLayer

Source: https://deepwiki.com/Chainlit/chainlit/6

Provides a conditional snippet that creates an SSL context when SSL is required, disabling hostname verification and certificate checks, and attaches it to the connection arguments for secure database connections.

```python
if ssl_require:
    ssl_context = ssl.create_default_context()
    ssl_context.check_hostname = False
    ssl_context.verify_mode = ssl.CERT_NONE
    connect_args["ssl"] = ssl_context

```

--------------------------------

### LangChain Integration for Steps

Source: https://deepwiki.com/Chainlit/chainlit/4

Integrates Chainlit's tracing with LangChain. By providing a `LangchainTracer` instance to the chain's config, Chainlit automatically creates steps for each run within the LangChain execution, capturing intermediate steps and final outputs.

```python
from chainlit.langchain import LangchainTracer

tracer = LangchainTracer()
chain.invoke(input_data, config={"callbacks": [tracer]})
# Steps created automatically for each run
```

--------------------------------

### Manual Step Creation: Explicit Send/Update

Source: https://deepwiki.com/Chainlit/chainlit/4

This pattern shows manual step creation by first instantiating a Step object, then explicitly calling `send()` to send it to the UI. The `output` is set, and `update()` is called to refresh the step's state.

```python
step = Step(name="process", type="tool")
await step.send()
# ... processing ...
step.output = result
await step.update()
```

--------------------------------

### Chainlit User Object Creation from OAuth

Source: https://deepwiki.com/Chainlit/chainlit/8-authentication

Illustrates the pattern for creating a `User` object from data provided by OAuth providers. The `identifier` field is crucial, mapping to different fields like email or username based on the provider. `metadata` stores additional user information, including the avatar URL and the provider ID.

```python
# User creation pattern from OAuth providers
user = User(
    identifier=provider_user_id,  # email, username, or provider-specific ID
    metadata={
        "image": avatar_url,      # User profile image
        "provider": provider_id,  # "github", "google", etc.
        # Provider-specific additional data
    }
)
```

--------------------------------

### POST /project/file

Source: https://deepwiki.com/Chainlit/chainlit/3

Handles spontaneous file uploads to a project. It supports various MIME types and file extensions, with configurable limits on the number of files and their total size.

```APIDOC
## POST /project/file

### Description
Allows users to upload files spontaneously to a project. The upload is subject to validation rules defined in the project's configuration, such as accepted MIME types, file extensions, maximum number of files, and maximum file size.

### Method
POST

### Endpoint
`/project/file?session_id={session_id}`

### Parameters
#### Query Parameters
- **session_id** (string) - Required - The unique identifier for the user's session.

#### Request Body
- **file** (file) - Required - The file to be uploaded.

### Request Example
(No specific request body example provided, typically a multipart/form-data request with the file).

### Response
#### Success Response (200)
- **file_id** (string) - The unique identifier assigned to the uploaded file.
- **name** (string) - The original name of the uploaded file.
- **path** (string) - The path where the file is temporarily stored or a signed URL if cloud storage is configured.
- **size** (integer) - The size of the file in bytes.
- **type** (string) - The MIME type of the file.

#### Response Example
```json
{
  "file_id": "a1b2c3d4-e5f6-7890-1234-567890abcdef",
  "name": "example.pdf",
  "path": "/tmp/files/example.pdf",
  "size": 102400,
  "type": "application/pdf"
}
```
```

--------------------------------

### Chainlit Step Context Manager Pattern

Source: https://deepwiki.com/Chainlit/chainlit/4-step-and-message-system

The recommended method for using Chainlit Steps, automatically handling timing and error capture. This pattern ensures robust step management within your application.

```python
async with Step(name="My Step", type="llm"):
    # Your code here
    await llm_call()
    # Step is automatically ended here
```

--------------------------------

### Chainlit Token Streaming API for Incremental Delivery

Source: https://deepwiki.com/Chainlit/chainlit/4

This Python code defines the `stream_token` method for incremental content delivery in Chainlit. It handles the initial `stream_start` event and subsequent `send_token` events. Tokens are accumulated in `self.output` (or `self.input`), with an option to replace content using `is_sequence`.

```python
async def stream_token(
    self, 
    token: str, 
    is_sequence: bool = False, 
    is_input: bool = False
)
```

--------------------------------

### Retrieve OAuth Prompt Parameter in Python

Source: https://deepwiki.com/Chainlit/chainlit/8

Defines a method to obtain the `prompt` parameter for OAuth authentication, checking provider-specific, global, and default values. Used across all OAuth providers to control login behavior.

```python
def get_prompt(self) -> Optional[str]:
    """Return OAuth prompt param."""
    if prompt := os.environ.get(f"OAUTH_{self.get_env_prefix()}_PROMPT"):
        return prompt

    if prompt := os.environ.get("OAUTH_PROMPT"):
        return prompt

    return self.default_prompt
```

--------------------------------

### Chainlit ErrorMessage Class Constructor

Source: https://deepwiki.com/Chainlit/chainlit/4-step-and-message-system

A simple wrapper for displaying error messages within Chainlit. It is designed for clear error reporting to the user.

```python
ErrorMessage(
    content: str,
    author: str = config.ui.name,
    fail_on_persist_error: bool = False,
)
```

--------------------------------

### File Upload Validation

Source: https://deepwiki.com/Chainlit/chainlit/10-actions-and-interactivity

Details the backend validation process for uploaded files, ensuring they meet MIME type, size, and count constraints.

```APIDOC
## File Upload Validation

### Description
When files are uploaded via the `/project/file` endpoint, the backend performs validation checks to ensure compliance with the specified constraints.

### Validation Checks
1.  **MIME Type Matching**: Verifies if the uploaded file's MIME type matches the allowed types. This includes exact matches (e.g., `"image/png"`), wildcard matches (e.g., `"image/*"`), and extension-based matches (e.g., `{"*/*": [".pdf", ".txt"]}`).
2.  **Size Constraints**: Ensures that the total size of all uploaded files does not exceed the limit defined by `max_size_mb` (converted to bytes).
3.  **Count Limits**: Checks if the number of uploaded files is within the `max_files` limit.

The validation logic is applied based on whether the upload was prompted by an `AskFileMessage` or is a spontaneous upload, referencing either `AskFileSpec` or `SpontaneousFileUploadFeature` configurations.
```

--------------------------------

### File Upload Endpoint

Source: https://deepwiki.com/Chainlit/chainlit/10

Handles the upload of files to the Chainlit server. It processes incoming file data and stores it according to the system's configuration.

```APIDOC
## POST /project/file

### Description
Handles file upload requests. This endpoint receives file data and saves it to the designated storage location.

### Method
POST

### Endpoint
/project/file

### Parameters
#### Request Body
- **file** (file) - Required - The file to be uploaded.

### Request Example
```
# This is a conceptual example, actual file upload is handled by multipart/form-data
POST /project/file HTTP/1.1
Host: localhost:8000
Content-Type: multipart/form-data; boundary=----WebKitFormBoundary7MA4YWxkTrZu0gW

------WebKitFormBoundary7MA4YWxkTrZu0gW
Content-Disposition: form-data; name="file"; filename="example.txt"
Content-Type: text/plain

This is the content of the example file.
------WebKitFormBoundary7MA4YWxkTrZu0gW--
```

### Response
#### Success Response (200)
- **message** (string) - A confirmation message indicating successful upload.
- **file_id** (string) - The unique identifier for the uploaded file.

#### Response Example
```json
{
  "message": "File uploaded successfully",
  "file_id": "a1b2c3d4-e5f6-7890-1234-567890abcdef"
}
```
```

--------------------------------

### Client-to-Server Message Events

Source: https://deepwiki.com/Chainlit/chainlit/2

Handles all client-initiated events including messages, edits, audio streaming, and system controls. These events are emitted by the frontend and processed by server handlers.

```APIDOC
## Client-to-Server Message Events

### Description
Handles all client-initiated events including user messages, message editing, audio streaming, and system controls. Events are processed by specific server handlers.

### Method
WebSocket (Socket.IO events)

### Endpoint
/ws (Socket.IO namespace)

### Parameters
#### Path Parameters
- None (event-based routing)

#### Query Parameters
- None

#### Request Body

**For client_message event:**
- **content** (string) - Required - Message content
- **id** (string) - Optional - Message identifier
- **parentId** (string) - Optional - Parent message ID for threading
- **attachments** (array) - Optional - File attachments

**For edit_message event:**
- **id** (string) - Required - Message ID to edit
- **content** (string) - Required - New message content

**For audio_chunk event:**
- **audio** (string) - Required - Base64 encoded audio data
- **timestamp** (number) - Required - Audio chunk timestamp

### Request Example
{
  "event": "client_message",
  "payload": {
    "content": "Hello, this is a test message",
    "id": "msg_123",
    "parentId": null,
    "attachments": []
  }
}

### Response
#### Success Response (200)
- **status** (string) - Event processing status
- **messageId** (string) - Generated or updated message ID

#### Response Example
{
  "status": "processed",
  "messageId": "msg_123"
}
```

--------------------------------

### Configure Spontaneous File Upload Settings

Source: https://deepwiki.com/Chainlit/chainlit/3

This configuration defines settings for the spontaneous file upload feature, including which MIME types or file extensions are accepted, and the maximum number and size of files allowed. It uses a TOML format for configuration.

```toml
[features.spontaneous_file_upload]
    enabled = true
    # MIME type patterns
    accept = ["image/*", "application/pdf", "text/plain"]
    # OR file extensions
    # accept = { "application/octet-stream" = [".xyz", ".pdb"] }
    max_files = 20
    max_size_mb = 500
```

--------------------------------

### Pytest Test Matrix Configuration

Source: https://deepwiki.com/Chainlit/chainlit/11-developer-guide

Configuration snippet from `pytest.yaml` defining the matrix strategy for running pytest tests across different Python versions.

```yaml
strategy:
  matrix:
    python-version: ['3.10', '3.11', '3.12', '3.13']
```

--------------------------------

### AWS Cognito OAuth Provider

Source: https://deepwiki.com/Chainlit/chainlit/8

Implementation for AWS Cognito OAuth provider with required environment variables and endpoints.

```APIDOC
## AWS Cognito OAuth Provider

### Description
Implementation for AWS Cognito OAuth provider with required environment variables and endpoints.

### Environment Variables
- **OAUTH_COGNITO_CLIENT_ID** (string) - Required - Client ID for AWS Cognito
- **OAUTH_COGNITO_CLIENT_SECRET** (string) - Required - Client secret for AWS Cognito
- **OAUTH_COGNITO_DOMAIN** (string) - Required - Domain for AWS Cognito (e.g., `myapp.auth.us-east-1.amazoncognito.com`)
- **OAUTH_COGNITO_SCOPE** (string) - Optional - Defaults to "openid profile email"
- **OAUTH_COGNITO_PROMPT** (string) - Optional - Controls authentication experience

### Endpoints
- Authorization: `https://{domain}/login`
- Token: `https://{domain}/oauth2/token`
- Userinfo: `https://{domain}/oauth2/userInfo`

### User Identifier
Email address
```

--------------------------------

### Generic OAuth Provider

Source: https://deepwiki.com/Chainlit/chainlit/8

Implementation for Generic OAuth provider that works with any OAuth 2.0-compliant identity provider.

```APIDOC
## Generic OAuth Provider

### Description
Implementation for Generic OAuth provider that works with any OAuth 2.0-compliant identity provider.

### Environment Variables
- **OAUTH_GENERIC_CLIENT_ID** (string) - Required - Client ID for the provider
- **OAUTH_GENERIC_CLIENT_SECRET** (string) - Required - Client secret for the provider
- **OAUTH_GENERIC_AUTH_URL** (string) - Required - Authorization URL
- **OAUTH_GENERIC_TOKEN_URL** (string) - Required - Token URL
- **OAUTH_GENERIC_USER_INFO_URL** (string) - Required - User info URL
- **OAUTH_GENERIC_SCOPES** (string) - Required - Scopes for the provider
- **OAUTH_GENERIC_NAME** (string) - Optional - Defaults to "generic"
- **OAUTH_GENERIC_USER_IDENTIFIER** (string) - Optional - Defaults to "email"
- **OAUTH_GENERIC_PROMPT** (string) - Optional - Controls authentication experience

### User Identifier
Configurable via `OAUTH_GENERIC_USER_IDENTIFIER`. This field is extracted from the userinfo response.
```

--------------------------------

### Enable Debug Mode for Chainlit Backend and Cypress

Source: https://deepwiki.com/Chainlit/chainlit/11

Activates verbose logging for troubleshooting. The backend uses the `CHAINLIT_DEBUG=1` environment variable, while Cypress tests utilize `DEBUG=cypress:*` for detailed output during interactive testing.

```shell
# Backend with debug logging
cd backend
CHAINLIT_DEBUG=1 uv run chainlit run chainlit/hello.py

# Cypress with debug output
DEBUG=cypress:* pnpm test:interactive
```

--------------------------------

### Define Command Interface - Python

Source: https://deepwiki.com/Chainlit/chainlit/10-actions-and-interactivity

Defines the structure for commands used in the Chainlit message composer, specifying fields like id, description, icon, and button/persistent flags. This interface is crucial for both frontend and backend command handling.

```python
class ICommand(BaseModel):
    id: str
    description: str
    icon: str
    button: Optional[bool] = False
    persistent: Optional[bool] = False
```

--------------------------------

### Convert Step Generation to Dictionary

Source: https://deepwiki.com/Chainlit/chainlit/7

Serializes the generation object to a dictionary format for persistence. If the generation object is null, it is set to None. This dictionary is then used for storage in the data layer or transmission to the frontend.

```python
function example() {
  return true;
}
```

--------------------------------

### Error Handling in Step Context Manager

Source: https://deepwiki.com/Chainlit/chainlit/4

Demonstrates how exceptions occurring within an asynchronous Step context manager are caught and handled. The `__aexit__` method captures the exception, sets the step's output to the exception message, marks the step as an error, and then allows the exception to propagate.

```python
# Inside __aexit__ method of Step class
if exc_val:
    self.output = str(exc_val)
    self.is_error = True
# Exception propagates after step update completes
```

--------------------------------

### File Download Endpoint

Source: https://deepwiki.com/Chainlit/chainlit/10

Allows retrieval of previously uploaded files using their unique identifiers. This endpoint facilitates accessing stored file content.

```APIDOC
## GET /project/file/{file_id}

### Description
Handles file download requests. Retrieves a file by its unique identifier.

### Method
GET

### Endpoint
/project/file/{file_id}

### Parameters
#### Path Parameters
- **file_id** (string) - Required - The unique identifier of the file to download.

### Response
#### Success Response (200)
- The response body will contain the raw content of the requested file.

#### Response Example
```
# Example response for a text file:
This is the content of the example file.
```
```

--------------------------------

### Chainlit Message Class Token Streaming

Source: https://deepwiki.com/Chainlit/chainlit/4

This Python code demonstrates token streaming within Chainlit's `Message` class, which inherits streaming capabilities. It shows how to stream tokens to `message.content` and then finalize the stream with `message.send()`, ensuring persistence.

```python
await message.stream_token("Hello ")
await message.stream_token("world!")
await message.send()  # Finalize stream and persist
```

--------------------------------

### Check OAuth Provider Configuration in Python

Source: https://deepwiki.com/Chainlit/chainlit/8

Determines if an OAuth provider is configured by checking for the presence of all its required environment variables. It iterates through the provider's `env` list and verifies if each variable exists in the environment.

```python
def is_configured(self):
    return all([os.environ.get(env) for env in self.env])
```

--------------------------------

### Chainlit Spontaneous File Upload Configuration

Source: https://deepwiki.com/Chainlit/chainlit/10-actions-and-interactivity

Illustrates how to enable and configure spontaneous file uploads in Chainlit via the `config.toml` file. This feature allows users to attach files to any message, not just in response to a direct file upload prompt. The configuration mirrors the constraints defined in AskFileSpec.

```toml
[features.spontaneous_file_upload]
    enabled = true
    accept = ["image/*", "application/pdf"]
    max_files = 20
    max_size_mb = 500
```

--------------------------------

### Use Decorator for Step Creation in Python

Source: https://deepwiki.com/Chainlit/chainlit/4

The @step decorator wraps functions to automatically create Steps, capturing inputs and outputs. It depends on the step decorator from Chainlit. Inputs are function arguments; outputs are returned values or exceptions. Supports both sync and async, but requires the decorated function to be callable.

```python
@step(name="process_data", type="tool")
async def process_data(input_text: str):
    # Function body becomes step execution
    result = perform_processing(input_text)
    return result
```

--------------------------------

### Configure MCP Features in config.toml

Source: https://deepwiki.com/Chainlit/chainlit/9-platform-integrations

This TOML snippet demonstrates how to enable or disable various Model Context Protocol (MCP) transports such as SSE, streamable HTTP, and stdio. Adjust the boolean flags to control feature availability and specify allowed executables for the stdio transport. It is used by the Chainlit server to determine which MCP capabilities to activate at runtime.

```TOML
[features.mcp]
    enabled = false

[features.mcp.sse]
    enabled = true

[features.mcp.streamable-http]
    enabled = true

[features.mcp.stdio]
    enabled = true
    allowed_executables = ["npx", "uvx"]
```

--------------------------------

### Asynchronous Step Persistence in Chainlit

Source: https://deepwiki.com/Chainlit/chainlit/4

This Python code demonstrates the asynchronous creation and updating of steps in Chainlit. It utilizes `asyncio.create_task` to persist step data without blocking the main execution flow. The `data_layer` object is responsible for the actual persistence operations, and a `persisted` flag prevents duplicate persistence.

```python
if data_layer and not self.persisted:
    asyncio.create_task(data_layer.create_step(step_dict.copy()))
    self.persisted = True
```

```python
if data_layer:
    asyncio.create_task(data_layer.update_step(step_dict.copy()))
```

--------------------------------

### File Upload API

Source: https://deepwiki.com/Chainlit/chainlit/10-actions-and-interactivity

Handles the upload of files to the Chainlit backend. Upon successful upload, it returns a FileDict containing the server ID of the uploaded file.

```APIDOC
## POST /project/file

### Description
Uploads a file to the Chainlit backend.

### Method
POST

### Endpoint
/project/file

### Parameters
#### Path Parameters
None

#### Query Parameters
None

#### Request Body
- **file** (multipart/form-data) - Required - The file to upload.

### Request Example
None

### Response
#### Success Response (200)
- **id** (string) - The server ID of the uploaded file.
- **name** (string) - The name of the uploaded file.
- **size** (integer) - The size of the uploaded file in bytes.
- **type** (string) - The MIME type of the uploaded file.

#### Response Example
```json
{
  "id": "some-file-id",
  "name": "example.txt",
  "size": 1024,
  "type": "text/plain"
}
```
```

--------------------------------

### Debugging E2E Tests in Headed Mode

Source: https://deepwiki.com/Chainlit/chainlit/11-developer-guide

A command to run Cypress E2E tests in headed mode, keeping the browser open after completion for debugging. It sets environment variables `SINGLE_TEST` and `CYPRESS_OPTIONS`.

```shell
SINGLE_TEST=password_auth CYPRESS_OPTIONS='--headed --no-exit' pnpm test
```

--------------------------------

### Execute Parameterized SQL using SQLAlchemy Async Session

Source: https://deepwiki.com/Chainlit/chainlit/6

Defines an async execute_sql method that prepares a parameterized query with SQLAlchemy's text construct, runs it within a transaction, commits on success, and rolls back on exception, returning rows or rowcount.

```python
async def execute_sql(self, query: str, parameters: dict):
    parameterized_query = text(query)
    async with self.async_session() as session:
        try:
            await session.begin()
            result = await session.execute(parameterized_query, parameters)
            await session.commit()
            # Returns rows or rowcount
        except SQLAlchemyError:
            await session.rollback()

```

--------------------------------

### Thread Creation Logic in Chainlit (Python)

Source: https://deepwiki.com/Chainlit/chainlit/3

Demonstrates how threads are created implicitly during WebSocket connections in Chainlit. If no threadId is provided, a new thread is created. Otherwise, an existing thread is resumed.

```Python
Threads are created implicitly during WebSocket connection. When a user connects without a `threadId`, a new thread is created automatically. If a `threadId` is provided, the existing thread is resumed instead.
Sources: backend/chainlit/server.py1-2089
```

--------------------------------

### Attach Elements (Images, PDFs) to Chainlit Steps and Messages

Source: https://deepwiki.com/Chainlit/chainlit/4-step-and-message-system

Chainlit steps and messages can include attached elements like images, PDFs, or plots. These elements are created and then sent to the UI with a reference to the parent step or message ID. The lifecycle involves creation, sending, persistence, and UI display.

```python
from chainlit.element import Image, Text

step = Step(name="Analysis", type="tool")
step.elements = [
    Image(name="chart.png", path="./chart.png", display="inline"),
    Text(name="report.txt", content="Analysis results...", display="side")
]
await step.send()
```

--------------------------------

### Chainlit OAuth Provider Configuration Check

Source: https://deepwiki.com/Chainlit/chainlit/8-authentication

This Python snippet demonstrates how to check which OAuth providers are configured in the Chainlit environment. It utilizes the `get_configured_oauth_providers` function, which returns a list of provider IDs for which configurations are present.

```python
# Each provider checks configuration with is_configured()
providers = get_configured_oauth_providers()  # Returns list of provider IDs
```

--------------------------------

### POST Authentication

Source: https://deepwiki.com/Chainlit/chainlit/2

Authenticates users by extracting and validating tokens from HTTP cookies. Required when require_login() returns True, and must be completed before session access.

```APIDOC
## POST Authentication

### Description
Authenticates users by extracting and validating tokens from HTTP cookies. This is a prerequisite for session access when authentication is required.

### Method
POST (via WebSocket handshake)

### Endpoint
/ws (Socket.IO connection with cookie authentication)

### Parameters
#### Path Parameters
- None (handled in Socket.IO handshake)

#### Query Parameters
- None (authentication via cookies)

#### Request Body
- **token** (string) - Required - JWT or session token from HTTP cookie

### Request Example
{
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}

### Response
#### Success Response (200)
- **authenticated** (boolean) - Authentication status
- **user** (object) - Current user information

#### Response Example
{
  "authenticated": true,
  "user": {
    "id": "user123",
    "name": "John Doe"
  }
}
```

--------------------------------

### Audio Streaming API

Source: https://deepwiki.com/Chainlit/chainlit/2

Handles bidirectional audio streaming including input audio chunks from client and output audio chunks from server, with support for audio interrupts and connection state management.

```APIDOC
## Audio Streaming API

### Description
Manages bidirectional audio streaming between client and server. Handles input audio from client (speech-to-text) and output audio to client (text-to-speech) with connection state management.

### Method
WebSocket (Socket.IO events)

### Endpoint
/ws (Socket.IO namespace)

### Parameters
#### Path Parameters
- None (audio streaming via events)

#### Query Parameters
- None

#### Request Body

**Client audio_chunk:**
- **audio** (string) - Required - Base64 encoded audio data
- **mimeType** (string) - Required - Audio format (e.g., "webm")
- **timestamp** (number) - Required - Audio chunk timestamp

**Server audio_chunk:**
- **audio** (string) - Required - Base64 encoded audio data
- **mimeType** (string) - Required - Audio format
- **timestamp** (number) - Required - Audio chunk timestamp

### Request Example
{
  "event": "audio_chunk",
  "payload": {
    "audio": "UklGRnoGAABXQVZFZm10IBAAAAABAAEAQB8AAEAfAAABAAgAZGF0YQoGAAC...",
    "mimeType": "webm",
    "timestamp": 1234567890
  }
}

### Response
#### Success Response (200)
- **status** (string) - Audio processing status
- **processed** (boolean) - Whether audio was successfully processed

#### Response Example
{
  "status": "processed",
  "processed": true
}
```

--------------------------------

### Control Chain of Thought (CoT) Display with config.ui.cot

Source: https://deepwiki.com/Chainlit/chainlit/4-step-and-message-system

The `config.ui.cot` setting in Chainlit governs the visibility of steps in the UI, offering 'full', 'tool_call', or 'hidden' modes. The `check_add_step_in_cot` function implements this logic, determining whether a step should be displayed or sent as a simplified stub.

```python
# From step.py lines 22-31
def check_add_step_in_cot(step: "Step"):
    is_message = step.type in [
        "user_message",
        "assistant_message",
    ]
    is_cl_run = step.name in CL_RUN_NAMES and step.type == "run"
    if config.ui.cot == "hidden" and not is_message and not is_cl_run:
        return False
    return True
```

```python
# From step.py lines 33-43
def stub_step(step: "Step") -> "StepDict":
    return {
        "type": step.type,
        "name": step.name,
        "id": step.id,
        "parentId": step.parent_id,
        "threadId": step.thread_id,
        "input": "",
        "output": "",
    }
```

--------------------------------

### Execute Query Method for AsyncPG Data Layer

Source: https://deepwiki.com/Chainlit/chainlit/6

Defines the async execute_query method used by ChainlitDataLayer to run parameterized SQL statements via asyncpg. It acquires a connection from the pool, executes the query safely, and returns results as a list of dictionaries while handling connection errors.

```python
async def execute_query(self, query: str, params: Union[Dict, None] = None)

```

--------------------------------

### Decorator-Based API

Source: https://deepwiki.com/Chainlit/chainlit/2-architecture-overview

Chainlit provides a decorator-based API for registering lifecycle callbacks and event handlers. These decorators specify the location to register these callbacks within the application's configuration.

```APIDOC
## Decorator API

### Description
Chainlit uses decorators to register lifecycle callbacks and event handlers. The registration location is specified in the decorator table.

### Method
N/A

### Endpoint
N/A

### Parameters
#### Path Parameters
- N/A

#### Query Parameters
- N/A

#### Request Body
- N/A

### Request Example
N/A

### Response
#### Success Response (200)
- N/A

#### Response Example
N/A

| Decorator | Purpose | Registration Location |
|---|---|---|
| `@cl.on_app_startup` | App initialization | `config.code.on_app_startup` |
| `@cl.on_app_shutdown` | App cleanup | `config.code.on_app_shutdown` |
| `@cl.on_chat_start` | New conversation start | `config.code.on_chat_start` |
| `@cl.on_chat_resume` | Resume existing thread | `config.code.on_chat_resume` |
| `@cl.on_message` | User message received | `config.code.on_message` |
| `@cl.on_chat_end` | Conversation end | `config.code.on_chat_end` |
| `@cl.on_audio_chunk` | Audio streaming | `config.code.on_audio_chunk` |
| `@cl.on_mcp_connect` | MCP connection | `config.code.on_mcp_connect` |
| `@cl.action_callback(name)` | Action button click | `config.code.action_callbacks[name]` |
| `@cl.password_auth_callback` | Password authentication | `config.code.password_auth_callback` |
| `@cl.oauth_callback` | OAuth authentication | `config.code.oauth_callback` |
```

--------------------------------

### Configure DynamoDB Data Layer with S3 Storage

Source: https://deepwiki.com/Chainlit/chainlit/6

Instantiates the DynamoDBDataLayer, specifying the DynamoDB table name, a custom boto3 client, and an S3StorageClient for storing conversation elements. It also sets a user thread limit.

```python
from chainlit.data import DynamoDBDataLayer
from chainlit.data.storage_clients import S3StorageClient
import boto3

# Custom boto3 client
dynamodb_client = boto3.client(
    'dynamodb',
    region_name='us-east-1',
    aws_access_key_id='...', 
    aws_secret_access_key='...'
)

data_layer = DynamoDBDataLayer(
    table_name="chainlit-conversations",
    client=dynamodb_client,
    storage_provider=S3StorageClient(bucket="my-bucket"),
    user_thread_limit=10
)
```

--------------------------------

### OAuth Authentication API

Source: https://deepwiki.com/Chainlit/chainlit/8

Chainlit's OAuth 2.0 authentication system allows users to log in via external identity providers. It supports a pluggable architecture for various OAuth providers.

```APIDOC
## OAuth Authentication

### Description
This section details Chainlit's OAuth 2.0 authentication system, which allows users to log in through third-party identity providers like GitHub, Google, and Azure AD. The system handles the complete OAuth flow, from generating authorization URLs to exchanging codes for tokens and retrieving user information.

### Method
N/A (This section describes a system rather than a single API endpoint)

### Endpoint
N/A

### Parameters
N/A

### Request Example
N/A

### Response
N/A

## OAuth Provider Base Class

### Description
The `OAuthProvider` is an abstract base class that defines the interface for all OAuth provider implementations within Chainlit. Each provider must adhere to this interface to ensure consistent handling of the authentication flow.

### Method
N/A

### Endpoint
N/A

### Parameters
#### Core Methods
- **is_configured()** (`bool`) - Checks if all required environment variables for the provider are set.
- **get_raw_token_response(code, url)** (`dict`) - Exchanges the authorization code for tokens with the provider. Returns a dictionary containing access and refresh tokens.
- **get_token(code, url)** (`str`) - Extracts the access token from the raw token response.
- **get_user_info(token)** (`Tuple[Dict, User]`) - Fetches user profile information from the provider using the access token. Returns a tuple containing the raw user data and a standardized `User` object.
- **get_env_prefix()** (`str`) - Returns the environment variable prefix specific to the provider (e.g., "AZURE_AD").
- **get_prompt()** (`Optional[str]`) - Retrieves the OAuth prompt parameter from environment variables, if set.

### Request Example
N/A

### Response
N/A

**Note**: The `id` attribute uniquely identifies each provider and is used in URL routing, e.g., `/auth/oauth/github`.
```

--------------------------------

### Thread and User Scoping

Source: https://deepwiki.com/Chainlit/chainlit/3

Details the access control mechanisms for threads and user data, ensuring that users can only access their own data and perform actions on threads they own.

```APIDOC
## Permissions and Access Control

### Thread Author Verification

#### Description
Ensures that only the author of a thread can modify or access its details. This is enforced through the `is_thread_author` function.

#### Methods Affected
- `GET /project/thread/{thread_id}`
- `GET /project/thread/{thread_id}/element/{element_id}`
- `PUT /project/thread`
- `PUT /project/thread/share`
- `DELETE /project/thread`

### User-Scoped Data Access

#### Description
All queries related to threads are automatically scoped to the current user. This prevents users from accessing threads belonging to other users.

### File Access Control

#### Description
File access is strictly session-scoped. Files are stored within a user's session and can only be accessed by that user. This is maintained through session-specific storage and identifier matching during download requests. Temporary files are automatically cleaned up upon session termination.
```

--------------------------------

### Clean Python and Node Build Artifacts

Source: https://deepwiki.com/Chainlit/chainlit/11

Removes temporary build directories and artifacts for both Python (backend) and Node.js (frontend) projects to ensure a clean slate for development or rebuilding. This is crucial for avoiding issues caused by stale build caches.

```shell
# Clean Python build artifacts
cd backend
rm -rf .venv build dist *.egg-info chainlit/frontend/dist chainlit/copilot/dist
uv sync --extra tests --extra mypy --extra dev --extra custom-data

# Clean Node artifacts
cd ..
rm -rf node_modules */node_modules */dist
pnpm install
pnpm run buildUi
```

--------------------------------

### Handle LlamaIndex Events with LlamaIndexCallbackHandler

Source: https://deepwiki.com/Chainlit/chainlit/4-step-and-message-system

The LlamaIndexCallbackHandler processes LlamaIndex events and maps them to Chainlit step types. It handles events such as FUNCTION_CALL, RETRIEVE, QUERY, and LLM, translating them into 'tool' or 'llm' step types for UI display.

--------------------------------

### Interactive Message Types

Source: https://deepwiki.com/Chainlit/chainlit/10-actions-and-interactivity

Chainlit provides specialized message classes for different types of user prompts, including text input, file uploads, and multiple-choice selections.

```APIDOC
## Interactive Message Types

### Description
Chainlit provides specialized message classes for different types of user prompts, including text input, file uploads, and multiple-choice selections. These message types allow for asynchronous waiting for user responses or timeouts.

### Message Types
- **AskUserMessage**: Prompts for text input. Returns `str` or `None`. Supports timeouts (default 60s).
- **AskFileMessage**: Requests file uploads. Returns `List[AskFileResponse]` or `None`. Supports timeouts (default 90s).
- **AskActionMessage**: Presents multiple choices for user selection. Returns `AskActionResponse` or `None`. Supports timeouts (default 90s).
- **AskElementMessage**: For custom element submission. Returns `AskElementResponse` or `None`. Supports timeouts (default 90s).

All `Ask*Message` classes have an async `send()` method that emits the prompt, waits for a response or timeout, and returns the result.
```

--------------------------------

### Safe Batch Step Sending with Error Handling (Python)

Source: https://deepwiki.com/Chainlit/chainlit/6

The safely_send_steps method in LiteralDataLayer sends steps asynchronously via API client while catching HTTP and request errors to log issues without data loss. It relies on aiohttp or similar for HTTP operations and logging. Inputs are lists of steps; outputs successful sends or logged errors; supports resilience in network failures.

```python
try:
    await self.client.api.send_steps(steps)
except HTTPStatusError as e:
    logger.error(f"HTTP Request: error sending steps: {e.response.status_code}")
except RequestError as e:
    logger.error(f"HTTP Request: error for {e.request.url!r}.")
```

--------------------------------

### Chainlit Step Decorator Pattern

Source: https://deepwiki.com/Chainlit/chainlit/4-step-and-message-system

Utilizes the `@step` decorator to wrap functions, automatically creating steps. This simplifies step creation by handling input/output processing and error capture.

```python
# From step.py lines 76-161
@step(name="Custom Step", type="tool")
async def my_function(arg1, arg2):
    # Function body becomes step output
    return result
```

--------------------------------

### Register MCP Connect and Disconnect Callbacks in Python

Source: https://deepwiki.com/Chainlit/chainlit/9

Demonstrates how to register custom callback functions for MCP connection and disconnection events. These hooks allow developers to implement custom logic when connections are established or terminated.

```python
@cl.on_mcp_connect
async def handle_mcp_connect(connection: McpConnection, client_session: ClientSession):
    # Custom logic on connect

@cl.on_mcp_disconnect
async def handle_mcp_disconnect(name: str, client_session: ClientSession):
    # Custom logic on disconnect
```

--------------------------------

### LangChain and LlamaIndex Parent ID Mapping for Chainlit

Source: https://deepwiki.com/Chainlit/chainlit/4

This Python code outlines how Chainlit integrates with LangChain and LlamaIndex to map parent IDs for steps. The `LangchainTracer` uses `parent_id_map` and `ignored_runs` to re-attach children to non-ignored ancestors. The `LlamaIndexCallbackHandler` uses `_get_parent_id()` which checks a registry or the current context variable.

```python
self.parent_id_map: Dict[str, str]  # Maps run_id to parent_run_id
self.ignored_runs: set  # Set of ignored run_ids
```

```python
# Check if event_parent_id exists in self.steps registry
# Otherwise use context_var.get().current_step.id
# Otherwise use None
```

--------------------------------

### Define Command Interface - TypeScript

Source: https://deepwiki.com/Chainlit/chainlit/10-actions-and-interactivity

Defines the structure for commands used in the Chainlit message composer, specifying fields like id, description, icon, and button/persistent flags. This interface is crucial for both frontend and backend command handling.

```typescript
interface ICommand {
  id: string;
  description: string;
  icon: string;
  button?: boolean;
  persistent?: boolean;
}
```

--------------------------------

### Thread Management Operations

Source: https://deepwiki.com/Chainlit/chainlit/3

This section details the API endpoints for managing conversation threads, including listing threads with various filtering and pagination options.

```APIDOC
## POST /project/threads

### Description
Returns a paginated list of threads for the authenticated user. This endpoint supports cursor-based pagination and allows filtering by feedback, user ID, and search queries.

### Method
POST

### Endpoint
/project/threads

### Parameters
#### Query Parameters
- **pagination.first** (int) - Required - Number of threads to fetch.
- **pagination.cursor** (Optional[str]) - Optional - Cursor for the next page.
- **filter.feedback** (Literal[0, 1]) - Optional - Filter by feedback value (0 or 1).
- **filter.userId** (str) - Optional - Filter by user ID. This is automatically set to the current user's ID.
- **filter.search** (str) - Optional - Search query to filter threads.

### Response
#### Success Response (200)
- **pageInfo** (object) - Pagination information.
  - **hasNextPage** (boolean) - Indicates if there are more pages.
  - **startCursor** (string) - The cursor for the beginning of the current page.
  - **endCursor** (string) - The cursor for the end of the current page.
- **data** (array) - An array of ThreadDict objects representing the threads.

#### Response Example
```json
{
  "pageInfo": {
    "hasNextPage": true,
    "startCursor": "cursor_string_start",
    "endCursor": "cursor_string_end"
  },
  "data": [
    {
      "id": "thread_id_1",
      "createdAt": "timestamp",
      "metadata": {
        "chat_profile": "default",
        "chat_settings": {},
        "env": {},
        "is_shared": false,
        "shared_at": null
      }
    },
    {
      "id": "thread_id_2",
      "createdAt": "timestamp",
      "metadata": {
        "chat_profile": "custom",
        "chat_settings": {},
        "env": {},
        "is_shared": true,
        "shared_at": "timestamp"
      }
    }
  ]
}
```
```

--------------------------------

### Configuring UI Header Links in Chainlit TOML

Source: https://deepwiki.com/Chainlit/chainlit/12-configuration-reference

This snippet demonstrates how to add custom links to the header in Chainlit's UI section using TOML configuration. It requires specifying name, icon_url, and url as mandatory fields, with optional display_name and target. The configuration is part of the [[UI.header_links]] array and allows integration with external resources like GitHub.

```toml
[[UI.header_links]]
name = "Issues"
display_name = "Report Issue"
icon_url = "https://avatars.githubusercontent.com/u/128686189?s=200&v=4"
url = "https://github.com/Chainlit/chainlit/issues"
target = "_blank"
```

--------------------------------

### StepDict Serialization Format for Chainlit Steps

Source: https://deepwiki.com/Chainlit/chainlit/4-step-and-message-system

Steps in Chainlit are serialized into a `StepDict` TypedDict format for transmission and storage. This structure includes fields like name, type, IDs, metadata, input/output, timestamps, and optional generation details.

```python
# From step.py lines 289-310
{
    "name": str,
    "type": StepType,
    "id": str,
    "threadId": str,
    "parentId": Optional[str],
    "streaming": bool,
    "metadata": Dict,
    "tags": Optional[List[str]],
    "input": str,
    "isError": Optional[bool],
    "output": str,
    "createdAt": Optional[str],
    "start": Optional[str],
    "end": Optional[str],
    "language": Optional[str],
    "defaultOpen": Optional[bool],
    "showInput": Optional[Union[bool, str]],
    "generation": Optional[Dict],  # serialized from BaseGeneration
}
```

--------------------------------

### WebSocket Session Management

Source: https://deepwiki.com/Chainlit/chainlit/2

Handles session creation, restoration, and management. Sessions are stored in memory and can be restored using session ID, with automatic cleanup on disconnect.

```APIDOC
## WebSocket Session Management

### Description
Manages WebSocket session lifecycle including creation, restoration, and cleanup. Sessions are stored in memory dictionaries for lookup by both socket ID and session ID.

### Method
WebSocket (Socket.IO)

### Endpoint
/ws/session

### Parameters
#### Path Parameters
- **sessionId** (string) - Optional - Session identifier for restoration
- **socketId** (string) - Required - WebSocket connection identifier

#### Query Parameters
- None

#### Request Body
- **socketId** (string) - Required - Current WebSocket connection ID
- **sessionId** (string) - Optional - Existing session to restore

### Request Example
{
  "sessionId": "sess_123456",
  "socketId": "abc_def_ghi"
}

### Response
#### Success Response (200)
- **sessionCreated** (boolean) - Whether new session was created
- **sessionId** (string) - Active session identifier
- **socketId** (string) - Associated socket connection

#### Response Example
{
  "sessionCreated": false,
  "sessionId": "sess_123456",
  "socketId": "abc_def_ghi"
}
```

--------------------------------

### Chainlit AskUserMessage Usage

Source: https://deepwiki.com/Chainlit/chainlit/4-step-and-message-system

Blocks execution until user input is received, typically used for prompts or queries. It returns the user's input in a structured format.

```python
response = await AskUserMessage(
    content="What is your name?",
    timeout=60,
    raise_on_timeout=False,
).send()

if response:
    user_input = response["output"]
```

--------------------------------

### LangChain Message to GenerationMessage Conversion

Source: https://deepwiki.com/Chainlit/chainlit/7

Maps LangChain message types to standardized roles for consistent handling of messages within Chainlit. It defines how specific types like 'human*', 'system*', 'function*', and 'tool*' are mapped to 'user', 'system', 'function', and 'tool' respectively.

```python
class GenerationMessage(TypedDict):
    role: str  # \"user\", \"assistant\", \"system\", \"function\", \"tool\"
    content: Union[str, List[Dict]]
    name: Optional[str]
    function_call: Optional[Dict]
    tool_calls: Optional[List[Dict]]
    uuid: Optional[str]
    templated: Optional[bool]
```

--------------------------------

### PUT /project/thread

Source: https://deepwiki.com/Chainlit/chainlit/3

Updates the thread name after verifying thread authorship. Delegates to data_layer.update_thread.

```APIDOC
## PUT /project/thread

### Description
Updates the thread name after verifying thread authorship. The operation delegates to `data_layer.update_thread`.

### Method
PUT

### Endpoint
/project/thread

### Parameters
#### Path Parameters
None

#### Query Parameters
None

#### Request Body
- **threadId** (string) - Required - The ID of the thread to update.
- **name** (string) - Required - The new name for the thread.

### Request Example
{
  "threadId": "thread_123",
  "name": "Updated Chat Name"
}

### Response
#### Success Response (200)
- **message** (string) - Confirmation message indicating the thread was renamed.

#### Response Example
{
  "message": "Thread renamed successfully."
}
```

--------------------------------

### Stub Step Data for UI

Source: https://deepwiki.com/Chainlit/chainlit/4

The stub_step function creates a minimal representation of a step, containing only essential metadata. This stub is sent to the UI to hide detailed execution information while the full step data is preserved for the data layer or database.

```python
def stub_step(step: "Step") -> "StepDict":
    return {
        "type": step.type,
        "name": step.name,
        "id": step.id,
        "parentId": step.parent_id,
        "threadId": step.thread_id,
        "input": "",
        "output": "",
    }
```

--------------------------------

### Configure Spontaneous File Upload Feature in TOML

Source: https://deepwiki.com/Chainlit/chainlit/10-actions-and-interactivity

Defines the configuration for enabling spontaneous file uploads, specifying accepted MIME types, maximum file count, and size limits. The TOML snippet can be placed in the project's config.toml to control upload behavior. Referenced in backend/chainlit/config.py.

```TOML
[features.spontaneous_file_upload]\n    enabled = true\n    # MIME type patterns\n    accept = ["image/*", "application/pdf", "text/plain"]\n    # Or MIME-to-extension mapping\n    # accept = { "application/octet-stream" = [".xyz", ".pdb"] }\n    max_files = 20\n    max_size_mb = 500
```

--------------------------------

### Handle Missing Access Token Error in Python

Source: https://deepwiki.com/Chainlit/chainlit/8

Checks the token exchange response for an `access_token` and raises an HTTPException with a 400 status code if absent, enforcing required token presence.

```python
if not token:
    raise HTTPException(status_code=400, detail=ACCESS_TOKEN_MISSING)
```

--------------------------------

### DELETE /project/thread

Source: https://deepwiki.com/Chainlit/chainlit/3

Permanently deletes a thread after verifying authorship.

```APIDOC
## DELETE /project/thread

### Description
Permanently deletes a thread after verifying authorship.

### Method
DELETE

### Endpoint
/project/thread

### Parameters
#### Path Parameters
None

#### Query Parameters
None

#### Request Body
- **threadId** (string) - Required - The ID of the thread to delete.

### Request Example
{
  "threadId": "thread_123"
}

### Response
#### Success Response (200)
- **message** (string) - Confirmation message indicating the thread was deleted.

#### Response Example
{
  "message": "Thread deleted successfully."
}
```

--------------------------------

### Action Invocation API

Source: https://deepwiki.com/Chainlit/chainlit/10-actions-and-interactivity

Enables the invocation of specific action callbacks defined within the Chainlit application. This is used for triggering backend logic associated with user interactions.

```APIDOC
## POST /project/action

### Description
Invokes an action callback on the backend.

### Method
POST

### Endpoint
/project/action

### Parameters
#### Path Parameters
None

#### Query Parameters
None

#### Request Body
- **name** (string) - Required - The name of the action to invoke.
- **args** (object) - Optional - Arguments to pass to the action callback.

### Request Example
```json
{
  "name": "my_action",
  "args": {
    "param1": "value1"
  }
}
```

### Response
#### Success Response (200)
- **success** (boolean) - Indicates whether the action invocation was successful.

#### Response Example
```json
{
  "success": true
}
```
```

--------------------------------

### Fetch and Encode Azure AD User Profile Photo

Source: https://deepwiki.com/Chainlit/chainlit/8

Retrieves user profile photo from Microsoft Graph API and encodes it as base64 data URL. Handles 48x48 pixel images with proper content type detection. Includes error handling to gracefully skip photo retrieval failures.

```python
try:
    photo_response = await client.get(
        "https://graph.microsoft.com/v1.0/me/photos/48x48/$value",
        headers={"Authorization": f"Bearer {token}"},
    )
    photo_data = await photo_response.aread()
    base64_image = base64.b64encode(photo_data)
    azure_user["image"] = (
        f"data:{photo_response.headers['Content-Type']};base64,{base64_image.decode('utf-8')}"
    )
except Exception:
    # Ignore errors getting the photo
    pass
```

--------------------------------

### HTTP Request Failure Handling with httpx in Python

Source: https://deepwiki.com/Chainlit/chainlit/8

Performs an asynchronous POST request to exchange tokens, using `response.raise_for_status()` to automatically raise exceptions for non‑2xx responses, and returns the JSON payload on success.

```python
async with httpx.AsyncClient() as client:
    response = await client.post(token_url, data=payload)
    response.raise_for_status()  # Raises HTTPStatusError if not 2xx
    return response.json()
```

--------------------------------

### Chainlit Automatic Parent-Child Hierarchy Management

Source: https://deepwiki.com/Chainlit/chainlit/4

This Python code illustrates Chainlit's mechanism for automatically managing the parent-child relationships between steps. It uses a `local_steps` ContextVar to maintain a stack of currently executing steps. When a step enters its context, it identifies its parent from the stack and pushes itself onto the stack. When exiting, it removes itself from the stack.

```python
previous_steps = local_steps.get() or []
parent_step = previous_steps[-1] if previous_steps else None
if self.parent_id not set:
    self.parent_id = parent_step.id
local_steps.set(previous_steps + [self])
```

```python
current_steps = local_steps.get()
current_steps.remove(self)
local_steps.set(current_steps)
```

--------------------------------

### Generation Metadata Overview

Source: https://deepwiki.com/Chainlit/chainlit/7

Generation Metadata refers to the structured data captured during Large Language Model (LLM) interactions in Chainlit. This metadata includes model information, token counts, timing metrics, provider details, and invocation parameters. The system records this information for both chat-based and completion-based generations, enabling observability, debugging, and analytics of LLM calls.

```APIDOC
## Purpose and Scope
Generation Metadata refers to the structured data captured during Large Language Model (LLM) interactions in Chainlit. This metadata includes model information, token counts, timing metrics, provider details, and invocation parameters. The system records this information for both chat-based and completion-based generations, enabling observability, debugging, and analytics of LLM calls.

For information about the Step abstraction that contains generation metadata, see Step and Message System. For LLM integration mechanisms, see LLM Integration.
```

--------------------------------

### Chainlit File Storage Structure

Source: https://deepwiki.com/Chainlit/chainlit/3

Illustrates the data structure used to store file metadata within a Chainlit session. This includes file ID, name, temporary path, size, and MIME type. It also mentions the process of persisting files to a local directory or cloud storage.

```python
session.files[file_id] = {
    "id": file_id,
    "name": filename,
    "path": Path,  # Temporary file path
    "size": int,
    "type": mime_type
}
```

--------------------------------

### Decorated Function for Steps

Source: https://deepwiki.com/Chainlit/chainlit/4

The `@step` decorator automatically wraps an asynchronous function, creating a step with the specified type and name. It captures the function's input and output, automatically handling the step's lifecycle.

```python
@step(type="tool", name="analyze_sentiment")
async def analyze_sentiment(text: str) -> dict:
    # Input captured automatically
    result = perform_analysis(text)
    return result  # Output captured automatically
```

--------------------------------

### Server-to-Client Event Streaming

Source: https://deepwiki.com/Chainlit/chainlit/2

Streams real-time events from server to client including task status, message updates, streaming tokens, and UI state changes. Supports bidirectional communication for conversational AI interfaces.

```APIDOC
## Server-to-Client Event Streaming

### Description
Streams real-time events from server to client including task status updates, message streaming, audio data, and UI state changes. Provides bi-directional communication for conversational AI interfaces.

### Method
WebSocket (Socket.IO events)

### Endpoint
/ws (Socket.IO namespace)

### Parameters
#### Path Parameters
- None (event-based streaming)

#### Query Parameters
- None

#### Request Body
N/A - Server-initiated events

### Request Example
N/A - Server push events

### Response
#### Success Response (200)

**stream_token event:**
- **id** (string) - Message ID being streamed
- **token** (string) - Streaming token/word
- **isSequence** (boolean) - Whether token continues sequence
- **isInput** (boolean) - Whether token is user input

**new_message event:**
- **id** (string) - Unique message identifier
- **type** (string) - Message type (user/assistant/system)
- **content** (object) - Message content structure
- **parentId** (string) - Parent message ID
- **children** (array) - Child message IDs

**ask event:**
- **msg** (string) - Prompt message for user
- **spec** (object) - Input specification and constraints

#### Response Example
{
  "event": "stream_token",
  "payload": {
    "id": "msg_123",
    "token": "Hello",
    "isSequence": true,
    "isInput": false
  }
}
```

--------------------------------

### Generation Metadata in Step Objects

Source: https://deepwiki.com/Chainlit/chainlit/7

The `Step` class in Chainlit includes an optional `generation` field that stores generation metadata. This field is populated by LLM integration handlers and is persisted as part of the step dictionary.

```APIDOC
## Generation Metadata in Step Objects

### Step.generation Field
The `Step` class includes an optional `generation` field that stores generation metadata:

```python
generation: Optional[BaseGeneration]
```

This field is populated by LLM integration handlers and persisted as part of the step dictionary:

```python
```

The `to_dict()` method serializes generation metadata for transmission:
backend/chainlit/step.py289-310
**Sources:** backend/chainlit/step.py183 backend/chainlit/step.py308

## Generation Capture by Integration
```

--------------------------------

### Generation Data Types

Source: https://deepwiki.com/Chainlit/chainlit/7

Chainlit utilizes two primary data structures from the `literalai` library to represent LLM generation metadata: `ChatGeneration` for chat-based interactions and `CompletionGeneration` for completion-based interactions.

```APIDOC
## Generation Data Types
Chainlit uses two primary data structures from the `literalai` library to represent LLM generation metadata:

### ChatGeneration
`ChatGeneration` represents chat-based LLM interactions where the input consists of a sequence of messages and the output is a single message completion. This structure captures:

| Field                 | Type              | Description                                       |
|-----------------------|-------------------|---------------------------------------------------|
| `provider`            | `str`             | LLM provider name (e.g., "openai", "anthropic") |
| `model`               | `str`             | Model identifier (e.g., "gpt-4", "claude-3")    |
| `messages`            | `List[GenerationMessage]` | Input message sequence                            |
| `message_completion`  | `GenerationMessage` | Generated response message                        |
| `tools`               | `List[Dict]`      | Available tools/functions                         |
| `settings`            | `Dict`            | Model invocation parameters                       |
| `variables`           | `Dict[str, str]`  | Template variables used                           |
| `duration`            | `float`           | Total generation time in seconds                  |
| `token_count`         | `int`             | Total tokens processed                            |
| `token_throughput_in_s` | `float`           | Tokens per second                                 |
| `tt_first_token`      | `float`           | Time to first token in milliseconds               |
| `prompt_id`           | `str`             | Prompt template identifier (optional)             |

### CompletionGeneration
`CompletionGeneration` represents completion-based LLM interactions where the input is a single prompt string:

| Field                 | Type              | Description                                       |
|-----------------------|-------------------|---------------------------------------------------|
| `provider`            | `str`             | LLM provider name                                 |
| `model`               | `str`             | Model identifier                                  |
| `prompt`              | `str`             | Input prompt text                                 |
| `completion`          | `str`             | Generated completion text                         |
| `settings`            | `Dict`            | Model invocation parameters                       |
| `variables`           | `Dict[str, str]`  | Template variables used                           |
| `duration`            | `float`           | Total generation time in seconds                  |
| `token_count`         | `int`             | Total tokens processed                            |
| `token_throughput_in_s` | `float`           | Tokens per second                                 |
| `tt_first_token`      | `float`           | Time to first token in milliseconds               |

**Sources:** backend/chainlit/langchain/callbacks.py94-106 backend/chainlit/llama_index/callbacks.py3-4
```

--------------------------------

### Persist User Session Metadata via Data Layer (Python)

Source: https://deepwiki.com/Chainlit/chainlit/5

On disconnect, the backend persists session metadata—including chat settings, profile, and environment—to the database using the data layer's update_thread method. This enables restoration of user state when a session is resumed.

```Python
await data_layer.update_thread(\n    thread_id=session.thread_id,\n    metadata=session.to_persistable()  # Includes chat_settings, chat_profile, env\n)
```

--------------------------------

### Python: MCP Disconnection Callback with @cl.on_mcp_disconnect

Source: https://deepwiki.com/Chainlit/chainlit/9-platform-integrations

This Python code defines an asynchronous function `handle_mcp_disconnect` decorated with `@cl.on_mcp_disconnect`. This function is triggered when an MCP connection is terminated, providing the connection name and the `ClientSession` object for performing necessary cleanup operations.

```python
@cl.on_mcp_disconnect
async def handle_mcp_disconnect(
    name: str,
    session: ClientSession
) -> None:
    """
    Args:
        name: The MCP connection name
        session: The ClientSession being disconnected
    """
    # Cleanup resources
    await cleanup_mcp_resources(name)
```

--------------------------------

### Handle JSON Metadata Strings for SQLite

Source: https://deepwiki.com/Chainlit/chainlit/6

Ensures that metadata retrieved from SQLite, which may be stored as JSON strings, is correctly parsed into Python dictionaries for further processing.

```python
metadata = user_data.get("metadata", {})
if isinstance(metadata, str):
    metadata = json.loads(metadata)

```

--------------------------------

### Register Action Callback in Python

Source: https://deepwiki.com/Chainlit/chainlit/10-actions-and-interactivity

Registers a callback function for an interactive action using the @cl.action_callback decorator. The action includes properties like name, label, payload, and tooltip. The callback receives a cl.Action object and can access its payload or remove the action button.

```python
@cl.action_callback("action_name")
async def handle_action(action: cl.Action):
    # Access action.payload for any data
    # Call action.remove() to hide the button
    pass
```

--------------------------------

### Thread Author Verification Logic

Source: https://deepwiki.com/Chainlit/chainlit/3

A Python function to verify if a given user identifier matches the owner of a specific thread. This is crucial for access control, ensuring only the thread author can modify or view sensitive thread details. It raises an HTTPException if the user is not authorized.

```python
async def is_thread_author(user_identifier: str, thread_id: str) -> None:
    """
    Verify that user_identifier matches the thread's userIdentifier.
    Raises HTTPException(401) if not authorized.
    """
```

--------------------------------

### DynamoDB Query for Thread Items

Source: https://deepwiki.com/Chainlit/chainlit/6

Fetches all items associated with a specific thread ID from DynamoDB using a query operation. It then categorizes these items (metadata, steps, elements) based on their Sort Key (SK) prefix.

```python
response = self.client.query(
    KeyConditionExpression="#pk = :pk",
    ExpressionAttributeNames={"#pk": "PK"},
    ExpressionAttributeValues={":pk": {"S": f"THREAD#{thread_id}"}}
)
```

--------------------------------

### Filter Steps for CoT Visibility

Source: https://deepwiki.com/Chainlit/chainlit/4

The check_add_step_in_cot function determines if a step should be visible in the UI based on the CoT (Chain of Thought) setting. It makes messages and specific run types always visible, while other step types are hidden if CoT is set to 'hidden'.

```python
def check_add_step_in_cot(step: "Step"):
    is_message = step.type in ["user_message", "assistant_message"]
    is_cl_run = step.name in CL_RUN_NAMES and step.type == "run"
    if config.ui.cot == "hidden" and not is_message and not is_cl_run:
        return False
    return True
```

--------------------------------

### Recoil LocalStorage Effect for Persistent Atom State (TypeScript)

Source: https://deepwiki.com/Chainlit/chainlit/5

Provides a Recoil atom effect that automatically restores an atom's value from localStorage on initialization and saves it on every change. Useful for maintaining session continuity across page reloads.

```TypeScript
const localStorageEffect = <T>(key: string): AtomEffect<T> => \n  ({ setSelf, onSet }) => {\n    // Restore from localStorage on atom initialization\n    const savedValue = localStorage.getItem(key);\n    if (savedValue != null) {\n      try {\n        setSelf(JSON.parse(savedValue));\n      } catch (error) {\n        console.error(`Error parsing localStorage value for key "${key}":`, error);\n      }\n    }\n    \n    // Save to localStorage whenever atom value changes\n    onSet((newValue, _, isReset) => {\n      if (isReset) {\n        localStorage.removeItem(key);\n      } else {\n        localStorage.setItem(key, JSON.stringify(newValue));\n      }\n    });\n  };
```

--------------------------------

### Python: Union Type for MCP Connection Requests

Source: https://deepwiki.com/Chainlit/chainlit/9-platform-integrations

Defines a `ConnectMCPRequest` union type in Python, combining different request schemas for connecting to MCP via stdio, SSE, or streamable-http transports. This type is used to handle various connection initiation methods.

```python
from typing import Union
from chainlit.types import (
    ConnectStdioMCPRequest,
    ConnectSseMCPRequest,
    ConnectStreamableHttpMCPRequest
)

ConnectMCPRequest = Union[
    ConnectStdioMCPRequest,
    ConnectSseMCPRequest,
    ConnectStreamableHttpMCPRequest
]
```

--------------------------------

### Share/Unshare Thread Request Body

Source: https://deepwiki.com/Chainlit/chainlit/3

JSON payload for toggling a thread's shared status. Requires author verification and updates the thread metadata accordingly.

```JSON
{
  "threadId": "string",
  "isShared": true
}
```

--------------------------------

### DynamoDB List Threads Query using GSI

Source: https://deepwiki.com/Chainlit/chainlit/6

Retrieves a list of threads for a user efficiently using the 'UserThread' Global Secondary Index (GSI) in DynamoDB. It queries in descending order of timestamp to show the most recent threads first.

```python
query_args = {
    "IndexName": "UserThread",
    "ScanIndexForward": False,  # DESC order
    "KeyConditionExpression": "#UserThreadPK = :pk",
    "ExpressionAttributeValues": {":pk": {"S": f"USER#{user_id}"}},
}
```

--------------------------------

### PUT /project/thread/share

Source: https://deepwiki.com/Chainlit/chainlit/3

Manages thread sharing by setting or removing the 'is_shared' flag in the thread's metadata.

```APIDOC
## PUT /project/thread/share

### Description
Manages thread sharing by setting or removing the 'is_shared' flag in the thread's metadata. Verifies thread authorship before updating.

### Method
PUT

### Endpoint
/project/thread/share

### Parameters
#### Path Parameters
None

#### Query Parameters
None

#### Request Body
- **threadId** (string) - Required - The ID of the thread to share or unshare.
- **isShared** (boolean) - Required - Set to `true` to share, `false` to unshare.

### Request Example
{
  "threadId": "thread_123",
  "isShared": true
}

### Response
#### Success Response (200)
- **message** (string) - Confirmation message indicating the sharing status was updated.

#### Response Example
{
  "message": "Thread sharing status updated successfully."
}
```

--------------------------------

### Custom Element Update API

Source: https://deepwiki.com/Chainlit/chainlit/10-actions-and-interactivity

Allows updating existing custom elements displayed within the Chainlit UI. This is useful for dynamically modifying element content or properties.

```APIDOC
## PUT /project/element

### Description
Updates a custom element.

### Method
PUT

### Endpoint
/project/element

### Parameters
#### Path Parameters
None

#### Query Parameters
None

#### Request Body
- **id** (string) - Required - The ID of the element to update.
- **name** (string) - Optional - The new name for the element.
- **content** (string) - Optional - The new content for the element.
- **display** (string) - Optional - The display type of the element (e.g., "inline", "page").
- **type** (string) - Optional - The type of the element (e.g., "text", "image").

### Request Example
```json
{
  "id": "my-element-id",
  "content": "Updated content for the element."
}
```

### Response
#### Success Response (200)
- **success** (boolean) - Indicates whether the element update was successful.

#### Response Example
```json
{
  "success": true
}
```
```

--------------------------------

### Thread Filtering Logic (Python)

Source: https://deepwiki.com/Chainlit/chainlit/3

Illustrates how the implementation automatically restricts threads to the current user by setting the `filter.userId`. It retrieves the user ID based on whether the current user is a `PersistedUser` or needs to be looked up by identifier.

```Python
If current user is PersistedUser:
    Use user.id directly
Else:
    Look up user by identifier
    Use persisted user's id

Sources: backend/chainlit/server.py915-941 backend/chainlit/types.py51-117
```

--------------------------------

### Rename Thread Endpoint Request Body

Source: https://deepwiki.com/Chainlit/chainlit/3

JSON payload used to rename a thread. Requires thread author verification before updating the thread name via the data layer. Provide the thread identifier and the new name.

```JSON
{
  "threadId": "string",
  "name": "string"
}
```

--------------------------------

### Custom Element Removal API

Source: https://deepwiki.com/Chainlit/chainlit/10-actions-and-interactivity

Provides functionality to remove custom elements from the Chainlit UI. This is useful for cleaning up UI elements that are no longer needed.

```APIDOC
## DELETE /project/element

### Description
Removes a custom element.

### Method
DELETE

### Endpoint
/project/element

### Parameters
#### Path Parameters
None

#### Query Parameters
None

#### Request Body
- **id** (string) - Required - The ID of the element to remove.

### Request Example
```json
{
  "id": "my-element-id"
}
```

### Response
#### Success Response (200)
- **success** (boolean) - Indicates whether the element removal was successful.

#### Response Example
```json
{
  "success": true
}
```
```

--------------------------------

### Assign Parent ID to Messages

Source: https://deepwiki.com/Chainlit/chainlit/4-step-and-message-system

Shows how messages automatically assign their `parent_id` by checking the `local_steps` context in their `__post_init__` method. If active steps are present, the ID of the last step in the stack is used.

```python
# From message.py lines 49-59
def __post_init__(self) -> None:
    self.thread_id = context.session.thread_id
    
    previous_steps = local_steps.get() or []
    parent_step = previous_steps[-1] if previous_steps else None
    if parent_step:
        self.parent_id = parent_step.id
```

--------------------------------

### DynamoDB Type Serialization and Deserialization

Source: https://deepwiki.com/Chainlit/chainlit/6

Handles the conversion of Python float types to Decimal for DynamoDB to prevent precision loss and back to float for JSON compatibility during deserialization.

```python
def _serialize_item(self, item: dict[str, Any]):
    def convert_floats(obj):
        if isinstance(obj, float):
            return Decimal(str(obj))
        # ... recursive conversion
    return {k: self._type_serializer.serialize(convert_floats(v)) 
            for k, v in item.items()}
```

--------------------------------

### DynamoDB Feedback Storage Update

Source: https://deepwiki.com/Chainlit/chainlit/6

Stores feedback as an attribute within a step item in DynamoDB using an UpdateExpression. This is a different approach compared to SQL implementations.

```python
self.client.update_item(
    Key={"PK": {"S": f"THREAD#{thread_id}"}, "SK": {"S": f"STEP#{step_id}"}},
    UpdateExpression="SET #feedback = :feedback",
    ExpressionAttributeNames={"#feedback": "feedback"},
    ExpressionAttributeValues={":feedback": serialized_feedback}
)
```

--------------------------------

### Delete Thread Endpoint Request Body

Source: https://deepwiki.com/Chainlit/chainlit/3

JSON payload used to permanently delete a thread after verifying the requester is the thread author. Only the thread identifier is required.

```JSON
{
  "threadId": "string"
}
```

--------------------------------

### DynamoDB Batch Delete for Thread Items

Source: https://deepwiki.com/Chainlit/chainlit/6

Deletes all items belonging to a thread from DynamoDB by first fetching them and then using `batch_write_item` to delete them in chunks of 25. It includes logic for handling unprocessed items with exponential backoff.

```python
BATCH_ITEM_SIZE = 25
for i in range(0, len(delete_requests), BATCH_ITEM_SIZE):
    chunk = delete_requests[i : i + BATCH_ITEM_SIZE]
    response = self.client.batch_write_item(
        RequestItems={self.table_name: chunk}
    )
# Exponential backoff for unprocessed items
# ... (code omitted for brevity)
```

--------------------------------

### Synchronize Thread ID with WebSocket Auth in React (TypeScript)

Source: https://deepwiki.com/Chainlit/chainlit/5

Updates the Socket.IO authentication payload whenever the frontend thread ID changes. This ensures the backend session stays aligned with the current conversation thread. Implemented as a React useEffect hook.

```TypeScript
useEffect(() => {\n  if (session?.socket) {\n    session.socket.auth['threadId'] = currentThreadId || '';\n  }\n}, [currentThreadId]);
```

--------------------------------

### Thread History Grouping Effect in React Client State

Source: https://deepwiki.com/Chainlit/chainlit/5

This effect within the React client state automatically groups threads by date whenever the thread list changes. It utilizes a custom `onSet` callback on the `threadHistoryState` atom to trigger the grouping logic. The `groupByDate` utility function is responsible for organizing threads into categories like 'Today', 'Yesterday', and 'Last 7 days' for UI display. This ensures a dynamic and user-friendly presentation of conversation history.

```typescript
effects: [
  ({ setSelf, onSet }: { setSelf: any; onSet: any }) => {
    onSet((newValue, oldValue) => {
      let timeGroupedThreads = newValue?.timeGroupedThreads;
      if (newValue?.threads && !isEqual(newValue.threads, oldValue?.timeGroupedThreads)) {
        timeGroupedThreads = groupByDate(newValue.threads);
      }
      setSelf({ ...newValue, timeGroupedThreads });
    });
  }
]
```

=== COMPLETE CONTENT === This response contains all available snippets from this library. No additional content exists. Do not make further requests.