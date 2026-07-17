# 🏗️ Jenkins MCP Server

> **MCP server for Jenkins CI/CD operations — 53 tools for job management, builds, pipelines, nodes, credentials, plugins, and more.**

A comprehensive [Model Context Protocol (MCP)](https://modelcontextprotocol.io/) server that exposes the full Jenkins REST API as AI-ready tools. Connect your AI assistant (Cursor, Claude Desktop, or any MCP client) to manage Jenkins servers through natural language.

Author: **Pawan Gunjkar** (pawangunjkar@gamil.com)

---

## ✨ Features

- 🔌 **53 tools** across **10 categories** — full Jenkins API coverage
- 🔐 **Secure authentication** — API token-based auth with CSRF crumb handling
- 💾 **Credential caching** — auto-connect from env vars or cached credentials
- 📁 **Folder support** — navigate and manage jobs in nested folder structures
- 🔀 **Pipeline support** — view stages, replay builds, and inspect pipeline runs
- 🧩 **Plugin management** — list, install, and inspect plugins
- 🖥️ **Node management** — monitor agents, executors, and system health
- 🎯 **Zero configuration** — just set env vars and run

---

## 🚀 Quick Start

### Prerequisites

- **Python 3.10+**
- **[uv](https://docs.astral.sh/uv/)** package manager
- **Jenkins server** with API access enabled

### 1. Clone & Install

```bash
cd jenkins-mcp
uv sync
```

### 2. Configure Jenkins Credentials

**Option A: Environment Variables (Recommended)**

```bash
# Copy and edit the example file
cp .env.example .env

# Set your Jenkins details
JENKINS_URL=http://localhost:8080
JENKINS_USERNAME=admin
JENKINS_API_TOKEN=your-api-token-here
```

**Option B: Connect via chat**

Just start the server and use the `jenkins_connect` tool:
```
jenkins_connect(url="http://localhost:8080", username="admin", api_token="your-token")
```

### 3. Generate a Jenkins API Token

1. Log in to Jenkins
2. Click your username → **Configure**
3. Under **API Token** → **Add new Token**
4. Give it a name → Click **Generate**
5. Copy the token value

### 4. Run the Server

```bash
# For Cursor / Claude Desktop (stdio transport)
uv run server.py

# For testing with MCP Inspector
uv run mcp dev server.py
```

---

## 🛠️ Tool Reference (53 Tools)

### Category 1: Connection & Authentication (4 tools)

| Tool | Description |
|------|-------------|
| `jenkins_connect` | Connect to a Jenkins server (URL + username + API token) |
| `jenkins_disconnect` | Disconnect the current session |
| `jenkins_status` | Show connection status and Jenkins system overview |
| `jenkins_save_credentials` | Save Jenkins credentials to disk cache for future use |

### Category 2: Job Management (10 tools)

| Tool | Description |
|------|-------------|
| `jenkins_list_jobs` | List all jobs (with optional folder path) |
| `jenkins_get_job` | Get detailed job info (config, health, parameters, builds) |
| `jenkins_create_job` | Create a new job from XML config |
| `jenkins_delete_job` | Delete a job permanently |
| `jenkins_copy_job` | Copy/clone an existing job to a new name |
| `jenkins_rename_job` | Rename a job |
| `jenkins_enable_job` | Enable a disabled job |
| `jenkins_disable_job` | Disable a job (prevents new builds) |
| `jenkins_get_job_config` | Get job's config.xml |
| `jenkins_update_job_config` | Update job's config.xml |

### Category 3: Build Operations (8 tools)

| Tool | Description |
|------|-------------|
| `jenkins_build` | Trigger a build (with optional JSON parameters) |
| `jenkins_get_build_info` | Get build details (result, duration, artifacts) |
| `jenkins_get_build_log` | Get build console output/log |
| `jenkins_stop_build` | Abort/stop a running build |
| `jenkins_delete_build` | Delete a specific build from history |
| `jenkins_get_last_build` | Get last build info for a job |
| `jenkins_get_last_successful_build` | Get last successful build info |
| `jenkins_get_last_failed_build` | Get last failed build info |

### Category 4: Build Queue (3 tools)

| Tool | Description |
|------|-------------|
| `jenkins_get_queue` | List all items in the build queue |
| `jenkins_get_queue_item` | Get details of a specific queue item |
| `jenkins_cancel_queue_item` | Cancel/remove an item from the queue |

### Category 5: Node/Agent Management (6 tools)

| Tool | Description |
|------|-------------|
| `jenkins_list_nodes` | List all nodes/agents with status |
| `jenkins_get_node_info` | Get detailed node information |
| `jenkins_enable_node` | Bring a node back online |
| `jenkins_disable_node` | Take a node offline (with reason) |
| `jenkins_get_node_log` | Get node's log output |
| `jenkins_get_executor_status` | Show executor status across all nodes |

### Category 6: View Management (5 tools)

| Tool | Description |
|------|-------------|
| `jenkins_list_views` | List all views |
| `jenkins_get_view` | Get view details and its jobs |
| `jenkins_create_view` | Create a new view |
| `jenkins_delete_view` | Delete a view |
| `jenkins_add_job_to_view` | Add a job to a view |

### Category 7: Credentials Management (4 tools)

| Tool | Description |
|------|-------------|
| `jenkins_list_credentials` | List stored Jenkins credentials |
| `jenkins_get_credential` | Get credential details (secrets masked) |
| `jenkins_create_credential` | Create a credential (username/password, secret text, SSH key) |
| `jenkins_delete_credential` | Delete a credential |

### Category 8: Plugin Management (4 tools)

| Tool | Description |
|------|-------------|
| `jenkins_list_plugins` | List all installed plugins with version |
| `jenkins_get_plugin_info` | Get details and dependencies of a plugin |
| `jenkins_install_plugin` | Install a plugin (with optional version) |
| `jenkins_list_available_plugins` | Search available plugins from Update Center |

### Category 9: Pipeline & Folder Operations (4 tools)

| Tool | Description |
|------|-------------|
| `jenkins_list_folder_jobs` | List jobs inside a folder |
| `jenkins_create_folder` | Create a new folder |
| `jenkins_get_pipeline_stages` | Get pipeline stage details and status |
| `jenkins_replay_pipeline` | Replay a pipeline build with modified script |

### Category 10: System & Administration (5 tools)

| Tool | Description |
|------|-------------|
| `jenkins_system_info` | Get Jenkins version, system stats, and overview |
| `jenkins_restart` | Restart Jenkins (safe or immediate) |
| `jenkins_quiet_down` | Put Jenkins in quiet-down mode (no new builds) |
| `jenkins_cancel_quiet_down` | Cancel quiet-down mode |
| `jenkins_run_groovy_script` | Execute a Groovy script on Jenkins Script Console |

---

## ⚙️ Configuration

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `JENKINS_URL` | Yes | — | Jenkins server URL (e.g., `http://localhost:8080`) |
| `JENKINS_USERNAME` | Yes | `admin` | Jenkins username |
| `JENKINS_API_TOKEN` | Yes | — | Jenkins API token |
| `JENKINS_SSL_VERIFY` | No | `true` | Set to `false` for self-signed certificates |
| `JENKINS_TIMEOUT` | No | `30` | Request timeout in seconds |
| `JENKINS_MCP_CACHE_DIR` | No | `~/.jenkins-mcp-cache` | Credential cache directory |

### Cursor Integration

Add to your Cursor MCP settings (`.cursor/mcp.json`):

```json
{
  "mcpServers": {
    "jenkins": {
      "command": "uv",
      "args": ["run", "--directory", "/path/to/jenkins-mcp", "server.py"],
      "env": {
        "JENKINS_URL": "http://localhost:8080",
        "JENKINS_USERNAME": "admin",
        "JENKINS_API_TOKEN": "your-api-token"
      }
    }
  }
}
```

### Claude Desktop Integration

Add to your Claude Desktop config (`claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "jenkins": {
      "command": "uv",
      "args": ["run", "--directory", "/path/to/jenkins-mcp", "server.py"],
      "env": {
        "JENKINS_URL": "http://localhost:8080",
        "JENKINS_USERNAME": "admin",
        "JENKINS_API_TOKEN": "your-api-token"
      }
    }
  }
}
```

---

## 💡 Example Usage

### Managing Jobs

```
"List all Jenkins jobs"
→ jenkins_list_jobs()

"Show me details about the 'deploy-prod' job"
→ jenkins_get_job(job_name="deploy-prod")

"Create a copy of 'deploy-prod' called 'deploy-staging'"
→ jenkins_copy_job(source_job="deploy-prod", new_name="deploy-staging")

"Disable the test job while we fix the flaky tests"
→ jenkins_disable_job(job_name="test-suite")
```

### Building & Monitoring

```
"Build the deploy pipeline with BRANCH=main"
→ jenkins_build(job_name="deploy-prod", parameters='{"BRANCH": "main"}')

"Show me the console output of the last build"
→ jenkins_get_build_log(job_name="deploy-prod")

"Stop build #42 — it's hanging"
→ jenkins_stop_build(job_name="deploy-prod", build_number=42)

"Show me the pipeline stages for the last build"
→ jenkins_get_pipeline_stages(job_name="deploy-prod")
```

### System Administration

```
"What's the status of all Jenkins nodes?"
→ jenkins_list_nodes()

"Take node 'agent-1' offline for maintenance"
→ jenkins_disable_node(node_name="agent-1", reason="Scheduled maintenance")

"List all installed plugins"
→ jenkins_list_plugins()

"Restart Jenkins safely after builds complete"
→ jenkins_restart(safe=True)

"Run a Groovy script to list all users"
→ jenkins_run_groovy_script(script="Jenkins.instance.securityRealm.getAllUsers().each { println it.id }")
```

---

## 📁 Project Structure

```
jenkins-mcp/
├── server.py              # Main MCP server — 53 tool definitions
├── jenkins_client.py      # Jenkins REST API client (HTTP, auth, CSRF)
├── credential_store.py    # Credential caching (env vars, memory, file)
├── pyproject.toml         # Project metadata & dependencies
├── .env.example           # Example environment variables
├── .gitignore             # Python gitignore
├── LICENSE                # MIT license
└── README.md              # This file
```

---

## 🔒 Security Notes

- **API tokens** are stored in `~/.jenkins-mcp-cache/credentials.json` with restrictive file permissions (600)
- **Never commit** `.env` files or credentials to version control
- Use **API tokens** (not passwords) for authentication — tokens can be revoked individually
- The server supports **SSL verification** — only disable for self-signed certs in development

---

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.
