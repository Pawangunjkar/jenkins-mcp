"""
Jenkins MCP Server — Main Entry Point.

Author: Pawan Gunjkar (pawangunjkar@gamil.com)

A comprehensive MCP server providing 53 tools across 10 categories
for managing Jenkins CI/CD servers via AI assistants.

Usage:
    uv run server.py                # Run via stdio (for Cursor/Claude Desktop)
    uv run mcp dev server.py        # Run with MCP Inspector (for testing)
"""

import sys
import json
from mcp.server.fastmcp import FastMCP

from jenkins_client import JenkinsClient
from credential_store import CredentialStore

# ============================================================
# Initialize MCP Server
# ============================================================

mcp = FastMCP(
    "jenkins",
    instructions=(
        "Jenkins MCP Server — Manage Jenkins CI/CD servers via REST API. "
        "Use jenkins_connect to establish a session first (or set JENKINS_URL/JENKINS_USERNAME/JENKINS_API_TOKEN env vars). "
        "Provides 53 tools across 10 categories: jobs, builds, pipelines, nodes, queue, views, "
        "credentials, plugins, folders, and system administration."
    ),
)

# Global Jenkins client instance
_credential_store = CredentialStore()
_jenkins = JenkinsClient(credential_store=_credential_store)

# Auto-connect if env vars are set
_env_creds = _credential_store.get_from_env()
if _env_creds:
    print(f"Auto-connecting to {_env_creds.url} from environment variables...", file=sys.stderr)
    _jenkins.connect(
        session_name="default",
        url=_env_creds.url,
        username=_env_creds.username,
        api_token=_env_creds.api_token,
        ssl_verify=_env_creds.ssl_verify,
        timeout=_env_creds.timeout,
    )


# ============================================================
# CATEGORY 1: Connection & Authentication (4 tools)
# ============================================================

@mcp.tool()
def jenkins_connect(
    url: str,
    username: str = "admin",
    api_token: str = "",
    ssl_verify: bool = True,
    timeout: int = 30,
    session_name: str = "default",
) -> str:
    """
    Connect to a Jenkins server and create a named session.

    If a session with the same name exists, it will be disconnected first.
    Credentials are automatically cached for future reconnection.

    Args:
        url: Jenkins server URL (e.g., 'http://localhost:8080')
        username: Jenkins username (default: admin)
        api_token: Jenkins API token (generate at User → Configure → API Token)
        ssl_verify: Verify SSL certificates (default: True, set False for self-signed certs)
        timeout: Request timeout in seconds (default: 30)
        session_name: Name for this session, e.g. 'prod', 'staging' (default: 'default')
    """
    return _jenkins.connect(
        session_name=session_name,
        url=url,
        username=username,
        api_token=api_token or None,
        ssl_verify=ssl_verify,
        timeout=timeout,
    )


@mcp.tool()
def jenkins_disconnect(session_name: str = "default") -> str:
    """
    Disconnect a specific Jenkins session.

    Args:
        session_name: Name of the session to disconnect (default: 'default')
    """
    return _jenkins.disconnect(session_name)


@mcp.tool()
def jenkins_status(session_name: str = "default") -> str:
    """
    Show connection status and Jenkins system overview.

    Displays active sessions, Jenkins version, executor info, and job counts.

    Args:
        session_name: Session to check (default: 'default')
    """
    sessions = _jenkins.list_sessions()
    if not sessions:
        return (
            "📡 No active Jenkins sessions.\n\n"
            "Use jenkins_connect to create a session:\n"
            "  jenkins_connect(url='http://localhost:8080', username='admin', api_token='your-token')"
        )

    lines = ["📡 Active Jenkins Sessions:\n"]
    for s in sessions:
        csrf = "🛡️" if s["csrf_enabled"] else "⚠️"
        lines.append(
            f"  🟢 {s['session_name']}: {s['username']}@{s['url']} "
            f"(uptime: {s['uptime']}, requests: {s['requests']}, csrf: {csrf})"
        )

    # Fetch system info from the requested session
    data, error = _jenkins.get(
        "/api/json?tree=mode,nodeDescription,numExecutors,quietingDown,useSecurity",
        session_name=session_name,
    )
    if data and not error:
        lines.append(f"\n🏗️ Jenkins Info:")
        lines.append(f"  • Mode: {data.get('mode', 'unknown')}")
        lines.append(f"  • Description: {data.get('nodeDescription', 'N/A')}")
        lines.append(f"  • Executors: {data.get('numExecutors', 'N/A')}")
        lines.append(f"  • Quieting Down: {'Yes' if data.get('quietingDown') else 'No'}")
        lines.append(f"  • Security: {'Enabled' if data.get('useSecurity') else 'Disabled'}")

    return "\n".join(lines)


@mcp.tool()
def jenkins_save_credentials(
    session_name: str,
    url: str,
    username: str = "admin",
    api_token: str = "",
) -> str:
    """
    Save Jenkins credentials for a session name (persisted to disk for future use).

    Saved credentials are used for auto-connect and future sessions.

    Args:
        session_name: Name to save these credentials under
        url: Jenkins server URL
        username: Jenkins username
        api_token: Jenkins API token
    """
    _credential_store.save_credentials(
        session_name=session_name,
        url=url,
        username=username,
        api_token=api_token or None,
    )
    return f"✅ Credentials saved for session '{session_name}' ({username}@{url})"


# ============================================================
# CATEGORY 2: Job Management (10 tools)
# ============================================================

@mcp.tool()
def jenkins_list_jobs(
    folder: str = "",
    session_name: str = "default",
) -> str:
    """
    List all Jenkins jobs, optionally within a specific folder.

    Shows job name, type, color/status, and URL for each job.

    Args:
        folder: Folder path to list jobs from (empty = root level)
        session_name: Jenkins session to use (default: 'default')
    """
    path = _jenkins.job_path(folder) if folder else ""
    data, error = _jenkins.get(
        f"{path}/api/json?tree=jobs[name,color,url,_class]",
        session_name=session_name,
    )
    if error:
        return error

    jobs = data.get("jobs", [])
    if not jobs:
        location = f"folder '{folder}'" if folder else "Jenkins"
        return f"📋 No jobs found in {location}."

    lines = [f"📋 Jobs ({len(jobs)}):\n"]
    for job in jobs:
        # Map color to emoji status
        color = job.get("color", "")
        status_map = {
            "blue": "🟢", "blue_anime": "🔵⏳", "green": "🟢", "green_anime": "🔵⏳",
            "yellow": "🟡", "yellow_anime": "🟡⏳",
            "red": "🔴", "red_anime": "🔴⏳",
            "grey": "⚪", "disabled": "⛔", "aborted": "⚫",
            "notbuilt": "⬜",
        }
        icon = status_map.get(color, "❓")

        # Detect job type
        cls = job.get("_class", "")
        if "Folder" in cls or "OrganizationFolder" in cls:
            icon = "📁"
            job_type = "Folder"
        elif "WorkflowJob" in cls:
            job_type = "Pipeline"
        elif "WorkflowMultiBranchProject" in cls:
            icon = "🌿"
            job_type = "Multibranch"
        elif "FreeStyleProject" in cls:
            job_type = "Freestyle"
        elif "MatrixProject" in cls:
            job_type = "Matrix"
        else:
            job_type = cls.split(".")[-1] if cls else "Unknown"

        lines.append(f"  {icon} {job['name']}  [{job_type}]")

    return "\n".join(lines)


@mcp.tool()
def jenkins_get_job(job_name: str, session_name: str = "default") -> str:
    """
    Get detailed information about a specific Jenkins job.

    Shows configuration, health, last builds, parameters, and more.

    Args:
        job_name: Full job name (use 'folder/job-name' for jobs in folders)
        session_name: Jenkins session to use
    """
    path = _jenkins.job_path(job_name)
    data, error = _jenkins.get(
        f"{path}/api/json?tree=name,url,color,buildable,description,displayName,"
        f"healthReport[description,score],lastBuild[number,url,result,timestamp,duration],"
        f"lastSuccessfulBuild[number],lastFailedBuild[number],lastStableBuild[number],"
        f"nextBuildNumber,inQueue,property[parameterDefinitions[name,type,defaultParameterValue[value],description]]",
        session_name=session_name,
    )
    if error:
        return error

    lines = [f"🔧 Job: {data.get('displayName', data.get('name', job_name))}\n"]
    lines.append(f"  • URL: {data.get('url', 'N/A')}")
    lines.append(f"  • Buildable: {'Yes' if data.get('buildable') else 'No'}")

    desc = data.get("description")
    if desc:
        lines.append(f"  • Description: {desc[:200]}")

    # Health reports
    health = data.get("healthReport", [])
    if health:
        lines.append(f"\n💊 Health:")
        for h in health:
            lines.append(f"  • [{h.get('score', '?')}%] {h.get('description', '')}")

    # Last build
    last_build = data.get("lastBuild")
    if last_build:
        result = last_build.get("result", "IN PROGRESS")
        duration_ms = last_build.get("duration", 0)
        duration_str = _format_duration(duration_ms)
        lines.append(f"\n🏗️ Last Build: #{last_build.get('number')}")
        lines.append(f"  • Result: {result}")
        lines.append(f"  • Duration: {duration_str}")

    # Build numbers
    lines.append(f"\n📊 Build Summary:")
    lines.append(f"  • Next Build: #{data.get('nextBuildNumber', '?')}")
    lsb = data.get("lastSuccessfulBuild")
    if lsb:
        lines.append(f"  • Last Success: #{lsb.get('number')}")
    lfb = data.get("lastFailedBuild")
    if lfb:
        lines.append(f"  • Last Failure: #{lfb.get('number')}")
    lines.append(f"  • In Queue: {'Yes' if data.get('inQueue') else 'No'}")

    # Parameters
    props = data.get("property", [])
    for prop in props:
        params = prop.get("parameterDefinitions", [])
        if params:
            lines.append(f"\n⚙️ Parameters:")
            for p in params:
                default = p.get("defaultParameterValue", {}).get("value", "")
                lines.append(f"  • {p.get('name')} ({p.get('type', '?')}): default='{default}'")
                if p.get("description"):
                    lines.append(f"    {p['description'][:100]}")

    return "\n".join(lines)


@mcp.tool()
def jenkins_create_job(
    job_name: str,
    config_xml: str,
    folder: str = "",
    session_name: str = "default",
) -> str:
    """
    Create a new Jenkins job from an XML configuration.

    Args:
        job_name: Name for the new job
        config_xml: Job configuration in XML format (config.xml content)
        folder: Folder to create the job in (empty = root level)
        session_name: Jenkins session to use
    """
    base_path = _jenkins.job_path(folder) if folder else ""
    _, error = _jenkins.post(
        f"{base_path}/createItem",
        params={"name": job_name},
        data=config_xml,
        content_type="application/xml",
        session_name=session_name,
    )
    if error:
        return error

    location = f"in folder '{folder}'" if folder else "at root level"
    return f"✅ Job '{job_name}' created successfully {location}."


@mcp.tool()
def jenkins_delete_job(job_name: str, session_name: str = "default") -> str:
    """
    Delete a Jenkins job permanently.

    ⚠️ This action cannot be undone. All build history will be lost.

    Args:
        job_name: Full job name (use 'folder/job-name' for jobs in folders)
        session_name: Jenkins session to use
    """
    path = _jenkins.job_path(job_name)
    _, error = _jenkins.post(f"{path}/doDelete", session_name=session_name)
    if error:
        return error

    return f"✅ Job '{job_name}' deleted successfully."


@mcp.tool()
def jenkins_copy_job(
    source_job: str,
    new_name: str,
    session_name: str = "default",
) -> str:
    """
    Copy/clone an existing Jenkins job to a new name.

    The new job will have identical configuration to the source.

    Args:
        source_job: Name of the job to copy
        new_name: Name for the new job
        session_name: Jenkins session to use
    """
    _, error = _jenkins.post(
        "/createItem",
        params={"name": new_name, "from": source_job, "mode": "copy"},
        session_name=session_name,
    )
    if error:
        return error

    return f"✅ Job '{source_job}' copied to '{new_name}' successfully."


@mcp.tool()
def jenkins_rename_job(
    job_name: str,
    new_name: str,
    session_name: str = "default",
) -> str:
    """
    Rename a Jenkins job.

    Args:
        job_name: Current job name
        new_name: New name for the job
        session_name: Jenkins session to use
    """
    path = _jenkins.job_path(job_name)
    _, error = _jenkins.post(
        f"{path}/doRename",
        params={"newName": new_name},
        session_name=session_name,
    )
    if error:
        return error

    return f"✅ Job '{job_name}' renamed to '{new_name}'."


@mcp.tool()
def jenkins_enable_job(job_name: str, session_name: str = "default") -> str:
    """
    Enable a disabled Jenkins job so it can be built again.

    Args:
        job_name: Full job name
        session_name: Jenkins session to use
    """
    path = _jenkins.job_path(job_name)
    _, error = _jenkins.post(f"{path}/enable", session_name=session_name)
    if error:
        return error

    return f"✅ Job '{job_name}' enabled."


@mcp.tool()
def jenkins_disable_job(job_name: str, session_name: str = "default") -> str:
    """
    Disable a Jenkins job (prevents new builds from being triggered).

    Args:
        job_name: Full job name
        session_name: Jenkins session to use
    """
    path = _jenkins.job_path(job_name)
    _, error = _jenkins.post(f"{path}/disable", session_name=session_name)
    if error:
        return error

    return f"✅ Job '{job_name}' disabled."


@mcp.tool()
def jenkins_get_job_config(job_name: str, session_name: str = "default") -> str:
    """
    Get a job's XML configuration (config.xml).

    Useful for understanding job setup, modifying, or duplicating configurations.

    Args:
        job_name: Full job name
        session_name: Jenkins session to use
    """
    path = _jenkins.job_path(job_name)
    data, error = _jenkins.get(f"{path}/config.xml", session_name=session_name, raw=True)
    if error:
        return error

    return f"📄 config.xml for '{job_name}':\n\n{data}"


@mcp.tool()
def jenkins_update_job_config(
    job_name: str,
    config_xml: str,
    session_name: str = "default",
) -> str:
    """
    Update a job's XML configuration (config.xml).

    ⚠️ This replaces the entire job configuration.

    Args:
        job_name: Full job name
        config_xml: New XML configuration content
        session_name: Jenkins session to use
    """
    path = _jenkins.job_path(job_name)
    _, error = _jenkins.post(
        f"{path}/config.xml",
        data=config_xml,
        content_type="application/xml",
        session_name=session_name,
    )
    if error:
        return error

    return f"✅ Configuration updated for job '{job_name}'."


# ============================================================
# CATEGORY 3: Build Operations (8 tools)
# ============================================================

@mcp.tool()
def jenkins_build(
    job_name: str,
    parameters: str = "",
    session_name: str = "default",
) -> str:
    """
    Trigger a build for a Jenkins job.

    For parameterized builds, pass parameters as JSON string.

    Args:
        job_name: Full job name
        parameters: Build parameters as JSON string, e.g. '{"BRANCH": "main", "DEPLOY": "true"}' (empty for non-parameterized jobs)
        session_name: Jenkins session to use
    """
    path = _jenkins.job_path(job_name)

    if parameters:
        try:
            params = json.loads(parameters)
        except json.JSONDecodeError:
            return f"❌ Invalid JSON parameters: {parameters}\nExpected format: {{\"PARAM1\": \"value1\", \"PARAM2\": \"value2\"}}"

        _, error = _jenkins.post(
            f"{path}/buildWithParameters",
            params=params,
            session_name=session_name,
        )
    else:
        _, error = _jenkins.post(f"{path}/build", session_name=session_name)

    if error:
        return error

    return f"✅ Build triggered for '{job_name}'." + (f"\n  Parameters: {parameters}" if parameters else "")


@mcp.tool()
def jenkins_get_build_info(
    job_name: str,
    build_number: int,
    session_name: str = "default",
) -> str:
    """
    Get detailed information about a specific build.

    Shows result, duration, timestamp, changes, and artifacts.

    Args:
        job_name: Full job name
        build_number: Build number to inspect
        session_name: Jenkins session to use
    """
    path = _jenkins.job_path(job_name)
    data, error = _jenkins.get(
        f"{path}/{build_number}/api/json?tree=number,url,result,timestamp,duration,estimatedDuration,"
        f"building,displayName,description,executor[number],artifacts[fileName,relativePath],"
        f"actions[causes[shortDescription,userId]]",
        session_name=session_name,
    )
    if error:
        return error

    result = data.get("result", "IN PROGRESS") if not data.get("building") else "🔄 BUILDING"
    result_icon = {"SUCCESS": "🟢", "FAILURE": "🔴", "UNSTABLE": "🟡", "ABORTED": "⚫", "NOT_BUILT": "⬜"}
    icon = result_icon.get(data.get("result", ""), "🔵") if not data.get("building") else "🔵"

    lines = [f"{icon} Build #{data.get('number')} — {data.get('displayName', job_name)}\n"]
    lines.append(f"  • Result: {result}")
    lines.append(f"  • Duration: {_format_duration(data.get('duration', 0))}")
    lines.append(f"  • Estimated: {_format_duration(data.get('estimatedDuration', 0))}")

    ts = data.get("timestamp")
    if ts:
        import datetime
        dt = datetime.datetime.fromtimestamp(ts / 1000)
        lines.append(f"  • Started: {dt.strftime('%Y-%m-%d %H:%M:%S')}")

    lines.append(f"  • URL: {data.get('url', 'N/A')}")

    desc = data.get("description")
    if desc:
        lines.append(f"  • Description: {desc[:200]}")

    # Causes
    for action in data.get("actions", []):
        causes = action.get("causes", [])
        for cause in causes:
            lines.append(f"  • Trigger: {cause.get('shortDescription', 'unknown')}")

    # Artifacts
    artifacts = data.get("artifacts", [])
    if artifacts:
        lines.append(f"\n📦 Artifacts ({len(artifacts)}):")
        for a in artifacts[:20]:
            lines.append(f"  • {a.get('fileName', a.get('relativePath', 'unknown'))}")

    return "\n".join(lines)


@mcp.tool()
def jenkins_get_build_log(
    job_name: str,
    build_number: int = 0,
    start_line: int = 0,
    session_name: str = "default",
) -> str:
    """
    Get console output (build log) for a specific build.

    Returns the full console text output of the build.

    Args:
        job_name: Full job name
        build_number: Build number (0 = last build)
        start_line: Start offset in bytes for progressive output (default: 0 = from beginning)
        session_name: Jenkins session to use
    """
    path = _jenkins.job_path(job_name)
    build = build_number if build_number > 0 else "lastBuild"

    data, error = _jenkins.get(
        f"{path}/{build}/consoleText",
        session_name=session_name,
        raw=True,
    )
    if error:
        return error

    build_label = f"#{build_number}" if build_number > 0 else "last build"
    return f"📜 Console Output — {job_name} ({build_label}):\n\n{data}"


@mcp.tool()
def jenkins_stop_build(
    job_name: str,
    build_number: int = 0,
    session_name: str = "default",
) -> str:
    """
    Abort/stop a running build.

    Args:
        job_name: Full job name
        build_number: Build number to stop (0 = last build)
        session_name: Jenkins session to use
    """
    path = _jenkins.job_path(job_name)
    build = build_number if build_number > 0 else "lastBuild"

    _, error = _jenkins.post(f"{path}/{build}/stop", session_name=session_name)
    if error:
        return error

    build_label = f"#{build_number}" if build_number > 0 else "last build"
    return f"✅ Build {build_label} of '{job_name}' has been stopped."


@mcp.tool()
def jenkins_delete_build(
    job_name: str,
    build_number: int,
    session_name: str = "default",
) -> str:
    """
    Delete a specific build from the build history.

    ⚠️ This cannot be undone.

    Args:
        job_name: Full job name
        build_number: Build number to delete
        session_name: Jenkins session to use
    """
    path = _jenkins.job_path(job_name)
    _, error = _jenkins.post(f"{path}/{build_number}/doDelete", session_name=session_name)
    if error:
        return error

    return f"✅ Build #{build_number} of '{job_name}' deleted."


@mcp.tool()
def jenkins_get_last_build(job_name: str, session_name: str = "default") -> str:
    """
    Get information about the last build of a job.

    Args:
        job_name: Full job name
        session_name: Jenkins session to use
    """
    path = _jenkins.job_path(job_name)
    data, error = _jenkins.get(
        f"{path}/lastBuild/api/json?tree=number,result,timestamp,duration,building,displayName,"
        f"actions[causes[shortDescription]]",
        session_name=session_name,
    )
    if error:
        return error

    return _format_build_summary("Last Build", job_name, data)


@mcp.tool()
def jenkins_get_last_successful_build(job_name: str, session_name: str = "default") -> str:
    """
    Get information about the last successful build of a job.

    Args:
        job_name: Full job name
        session_name: Jenkins session to use
    """
    path = _jenkins.job_path(job_name)
    data, error = _jenkins.get(
        f"{path}/lastSuccessfulBuild/api/json?tree=number,result,timestamp,duration,building,displayName,"
        f"actions[causes[shortDescription]]",
        session_name=session_name,
    )
    if error:
        return error

    return _format_build_summary("Last Successful Build", job_name, data)


@mcp.tool()
def jenkins_get_last_failed_build(job_name: str, session_name: str = "default") -> str:
    """
    Get information about the last failed build of a job.

    Args:
        job_name: Full job name
        session_name: Jenkins session to use
    """
    path = _jenkins.job_path(job_name)
    data, error = _jenkins.get(
        f"{path}/lastFailedBuild/api/json?tree=number,result,timestamp,duration,building,displayName,"
        f"actions[causes[shortDescription]]",
        session_name=session_name,
    )
    if error:
        return error

    return _format_build_summary("Last Failed Build", job_name, data)


# ============================================================
# CATEGORY 4: Build Queue (3 tools)
# ============================================================

@mcp.tool()
def jenkins_get_queue(session_name: str = "default") -> str:
    """
    List all items currently in the Jenkins build queue.

    Shows queued jobs waiting to be built, their position, and why they're waiting.

    Args:
        session_name: Jenkins session to use
    """
    data, error = _jenkins.get(
        "/queue/api/json?tree=items[id,task[name,url],why,inQueueSince,blocked,buildable,stuck]",
        session_name=session_name,
    )
    if error:
        return error

    items = data.get("items", [])
    if not items:
        return "📭 Build queue is empty."

    lines = [f"📬 Build Queue ({len(items)} item(s)):\n"]
    for item in items:
        task = item.get("task", {})
        status = "⏳"
        if item.get("stuck"):
            status = "🔒"
        elif item.get("blocked"):
            status = "🚫"
        elif item.get("buildable"):
            status = "✅"

        lines.append(f"  {status} [{item.get('id')}] {task.get('name', 'unknown')}")
        why = item.get("why")
        if why:
            lines.append(f"     Reason: {why[:150]}")

    return "\n".join(lines)


@mcp.tool()
def jenkins_get_queue_item(queue_id: int, session_name: str = "default") -> str:
    """
    Get details of a specific item in the build queue.

    Args:
        queue_id: Queue item ID (from jenkins_get_queue)
        session_name: Jenkins session to use
    """
    data, error = _jenkins.get(
        f"/queue/item/{queue_id}/api/json",
        session_name=session_name,
    )
    if error:
        return error

    task = data.get("task", {})
    lines = [f"📋 Queue Item #{queue_id}\n"]
    lines.append(f"  • Job: {task.get('name', 'unknown')}")
    lines.append(f"  • URL: {task.get('url', 'N/A')}")
    lines.append(f"  • Blocked: {data.get('blocked', False)}")
    lines.append(f"  • Buildable: {data.get('buildable', False)}")
    lines.append(f"  • Stuck: {data.get('stuck', False)}")
    why = data.get("why")
    if why:
        lines.append(f"  • Reason: {why}")

    return "\n".join(lines)


@mcp.tool()
def jenkins_cancel_queue_item(queue_id: int, session_name: str = "default") -> str:
    """
    Cancel/remove an item from the build queue.

    Args:
        queue_id: Queue item ID to cancel
        session_name: Jenkins session to use
    """
    _, error = _jenkins.post(
        "/queue/cancelItem",
        params={"id": str(queue_id)},
        session_name=session_name,
    )
    if error:
        return error

    return f"✅ Queue item #{queue_id} cancelled."


# ============================================================
# CATEGORY 5: Node/Agent Management (6 tools)
# ============================================================

@mcp.tool()
def jenkins_list_nodes(session_name: str = "default") -> str:
    """
    List all Jenkins nodes/agents with their status.

    Shows node name, status (online/offline), executors, and labels.

    Args:
        session_name: Jenkins session to use
    """
    data, error = _jenkins.get(
        "/computer/api/json?tree=computer[displayName,offline,temporarilyOffline,"
        "numExecutors,idle,monitorData,offlineCauseReason]",
        session_name=session_name,
    )
    if error:
        return error

    computers = data.get("computer", [])
    if not computers:
        return "🖥️ No nodes found."

    lines = [f"🖥️ Nodes ({len(computers)}):\n"]
    for node in computers:
        name = node.get("displayName", "unknown")
        offline = node.get("offline", False)
        temp_offline = node.get("temporarilyOffline", False)

        if offline:
            icon = "🔴"
            status = "Offline"
        elif temp_offline:
            icon = "🟡"
            status = "Temporarily Offline"
        else:
            icon = "🟢"
            status = "Online"

        executors = node.get("numExecutors", 0)
        idle = "Idle" if node.get("idle") else "Busy"

        lines.append(f"  {icon} {name}: {status} ({executors} executors, {idle})")

        reason = node.get("offlineCauseReason")
        if reason:
            lines.append(f"     Reason: {reason[:100]}")

        # System info from monitor data
        monitor = node.get("monitorData", {})
        if monitor:
            disk = monitor.get("hudson.node_monitors.DiskSpaceMonitor")
            if disk and isinstance(disk, dict):
                size_gb = disk.get("size", 0) / (1024 ** 3)
                lines.append(f"     Disk: {size_gb:.1f} GB free")

    return "\n".join(lines)


@mcp.tool()
def jenkins_get_node_info(node_name: str, session_name: str = "default") -> str:
    """
    Get detailed information about a specific Jenkins node/agent.

    Args:
        node_name: Node name (use '(built-in)' or '(master)' for the master node)
        session_name: Jenkins session to use
    """
    # Handle built-in node naming
    if node_name.lower() in ("(built-in)", "(master)", "master", "built-in"):
        api_name = "(built-in)"
    else:
        api_name = node_name

    data, error = _jenkins.get(
        f"/computer/{api_name}/api/json",
        session_name=session_name,
    )
    if error:
        return error

    lines = [f"🖥️ Node: {data.get('displayName', node_name)}\n"]
    lines.append(f"  • Offline: {data.get('offline', False)}")
    lines.append(f"  • Temporarily Offline: {data.get('temporarilyOffline', False)}")
    lines.append(f"  • Executors: {data.get('numExecutors', 0)}")
    lines.append(f"  • Idle: {data.get('idle', False)}")

    reason = data.get("offlineCauseReason")
    if reason:
        lines.append(f"  • Offline Reason: {reason}")

    labels = data.get("assignedLabels", [])
    if labels:
        label_names = [l.get("name", "") for l in labels if l.get("name")]
        lines.append(f"  • Labels: {', '.join(label_names)}")

    return "\n".join(lines)


@mcp.tool()
def jenkins_enable_node(node_name: str, session_name: str = "default") -> str:
    """
    Bring a Jenkins node/agent back online.

    Args:
        node_name: Node name to enable
        session_name: Jenkins session to use
    """
    if node_name.lower() in ("(built-in)", "(master)", "master", "built-in"):
        api_name = "(built-in)"
    else:
        api_name = node_name

    _, error = _jenkins.post(
        f"/computer/{api_name}/toggleOffline",
        params={"offlineMessage": ""},
        session_name=session_name,
    )
    if error:
        return error

    return f"✅ Node '{node_name}' brought online."


@mcp.tool()
def jenkins_disable_node(
    node_name: str,
    reason: str = "Taken offline via Jenkins MCP",
    session_name: str = "default",
) -> str:
    """
    Take a Jenkins node/agent offline with a reason message.

    Args:
        node_name: Node name to disable
        reason: Reason for taking offline (displayed in Jenkins UI)
        session_name: Jenkins session to use
    """
    if node_name.lower() in ("(built-in)", "(master)", "master", "built-in"):
        api_name = "(built-in)"
    else:
        api_name = node_name

    _, error = _jenkins.post(
        f"/computer/{api_name}/toggleOffline",
        params={"offlineMessage": reason},
        session_name=session_name,
    )
    if error:
        return error

    return f"✅ Node '{node_name}' taken offline. Reason: {reason}"


@mcp.tool()
def jenkins_get_node_log(node_name: str, session_name: str = "default") -> str:
    """
    Get the log output from a Jenkins node/agent.

    Args:
        node_name: Node name
        session_name: Jenkins session to use
    """
    if node_name.lower() in ("(built-in)", "(master)", "master", "built-in"):
        api_name = "(built-in)"
    else:
        api_name = node_name

    data, error = _jenkins.get(
        f"/computer/{api_name}/logText/progressiveText",
        session_name=session_name,
        raw=True,
    )
    if error:
        return error

    return f"📜 Node Log — {node_name}:\n\n{data}" if data else f"📜 No log output for node '{node_name}'."


@mcp.tool()
def jenkins_get_executor_status(session_name: str = "default") -> str:
    """
    Show executor status across all nodes.

    Displays which executors are busy and what they're running.

    Args:
        session_name: Jenkins session to use
    """
    data, error = _jenkins.get(
        "/computer/api/json?tree=computer[displayName,executors[currentExecutable[url,number],idle,number],"
        "numExecutors,offline]&depth=1",
        session_name=session_name,
    )
    if error:
        return error

    computers = data.get("computer", [])
    lines = ["⚙️ Executor Status:\n"]
    total_executors = 0
    busy_executors = 0

    for node in computers:
        if node.get("offline"):
            continue

        name = node.get("displayName", "unknown")
        executors = node.get("executors", [])
        total_executors += len(executors)

        for exe in executors:
            exe_num = exe.get("number", "?")
            if exe.get("idle"):
                lines.append(f"  💤 {name} #{exe_num}: Idle")
            else:
                busy_executors += 1
                executable = exe.get("currentExecutable", {})
                build_url = executable.get("url", "")
                build_num = executable.get("number", "?")
                # Extract job name from URL
                job_info = build_url.split("/job/")[-1] if "/job/" in build_url else "unknown"
                lines.append(f"  🔨 {name} #{exe_num}: Building {job_info}")

    lines.insert(1, f"  Total: {total_executors} | Busy: {busy_executors} | Free: {total_executors - busy_executors}\n")

    return "\n".join(lines)


# ============================================================
# CATEGORY 6: View Management (5 tools)
# ============================================================

@mcp.tool()
def jenkins_list_views(session_name: str = "default") -> str:
    """
    List all Jenkins views.

    Args:
        session_name: Jenkins session to use
    """
    data, error = _jenkins.get(
        "/api/json?tree=views[name,url,_class]",
        session_name=session_name,
    )
    if error:
        return error

    views = data.get("views", [])
    if not views:
        return "👁️ No views found."

    lines = [f"👁️ Views ({len(views)}):\n"]
    for view in views:
        cls = view.get("_class", "")
        view_type = "List" if "ListView" in cls else ("All" if "AllView" in cls else cls.split(".")[-1])
        lines.append(f"  • {view['name']}  [{view_type}]")

    return "\n".join(lines)


@mcp.tool()
def jenkins_get_view(view_name: str, session_name: str = "default") -> str:
    """
    Get details about a view and list its jobs.

    Args:
        view_name: View name
        session_name: Jenkins session to use
    """
    data, error = _jenkins.get(
        f"/view/{view_name}/api/json?tree=name,url,description,jobs[name,color,url]",
        session_name=session_name,
    )
    if error:
        return error

    lines = [f"👁️ View: {data.get('name', view_name)}\n"]
    desc = data.get("description")
    if desc:
        lines.append(f"  Description: {desc[:200]}\n")

    jobs = data.get("jobs", [])
    if jobs:
        lines.append(f"  Jobs ({len(jobs)}):")
        for job in jobs:
            color = job.get("color", "")
            status_map = {
                "blue": "🟢", "green": "🟢", "yellow": "🟡",
                "red": "🔴", "grey": "⚪", "disabled": "⛔",
            }
            icon = status_map.get(color.replace("_anime", ""), "❓")
            lines.append(f"    {icon} {job['name']}")
    else:
        lines.append("  No jobs in this view.")

    return "\n".join(lines)


@mcp.tool()
def jenkins_create_view(
    view_name: str,
    view_type: str = "list",
    session_name: str = "default",
) -> str:
    """
    Create a new Jenkins view.

    Args:
        view_name: Name for the new view
        view_type: View type — 'list' (default) or 'my' (My View)
        session_name: Jenkins session to use
    """
    mode_map = {
        "list": "hudson.model.ListView",
        "my": "hudson.model.MyView",
    }
    mode = mode_map.get(view_type.lower(), "hudson.model.ListView")

    view_config = json.dumps({"name": view_name, "mode": mode})
    _, error = _jenkins.post(
        "/createView",
        params={"name": view_name},
        data=view_config,
        content_type="application/json",
        session_name=session_name,
    )
    if error:
        return error

    return f"✅ View '{view_name}' created ({view_type})."


@mcp.tool()
def jenkins_delete_view(view_name: str, session_name: str = "default") -> str:
    """
    Delete a Jenkins view.

    ⚠️ This only removes the view — jobs in the view are NOT deleted.

    Args:
        view_name: View name to delete
        session_name: Jenkins session to use
    """
    _, error = _jenkins.post(f"/view/{view_name}/doDelete", session_name=session_name)
    if error:
        return error

    return f"✅ View '{view_name}' deleted."


@mcp.tool()
def jenkins_add_job_to_view(
    view_name: str,
    job_name: str,
    session_name: str = "default",
) -> str:
    """
    Add a job to an existing view.

    Args:
        view_name: View name
        job_name: Job name to add to the view
        session_name: Jenkins session to use
    """
    _, error = _jenkins.post(
        f"/view/{view_name}/addJobToView",
        params={"name": job_name},
        session_name=session_name,
    )
    if error:
        return error

    return f"✅ Job '{job_name}' added to view '{view_name}'."


# ============================================================
# CATEGORY 7: Credentials Management (4 tools)
# ============================================================

@mcp.tool()
def jenkins_list_credentials(
    domain: str = "_",
    store: str = "system",
    session_name: str = "default",
) -> str:
    """
    List all credentials stored in Jenkins.

    Args:
        domain: Credential domain ('_' = global domain, default)
        store: Credential store ('system' = system store, default)
        session_name: Jenkins session to use
    """
    data, error = _jenkins.get(
        f"/credentials/store/{store}/domain/{domain}/api/json?tree=credentials[id,displayName,typeName,description]",
        session_name=session_name,
    )
    if error:
        return error

    creds = data.get("credentials", [])
    if not creds:
        return "🔑 No credentials found."

    lines = [f"🔑 Credentials ({len(creds)}):\n"]
    for c in creds:
        lines.append(f"  • [{c.get('id', '?')}] {c.get('displayName', 'unnamed')}")
        lines.append(f"    Type: {c.get('typeName', 'unknown')}")
        desc = c.get("description")
        if desc:
            lines.append(f"    Desc: {desc[:100]}")

    return "\n".join(lines)


@mcp.tool()
def jenkins_get_credential(
    credential_id: str,
    domain: str = "_",
    store: str = "system",
    session_name: str = "default",
) -> str:
    """
    Get details of a specific Jenkins credential (secrets are masked).

    Args:
        credential_id: Credential ID
        domain: Credential domain ('_' = global)
        store: Credential store ('system' = system store)
        session_name: Jenkins session to use
    """
    data, error = _jenkins.get(
        f"/credentials/store/{store}/domain/{domain}/credential/{credential_id}/api/json",
        session_name=session_name,
    )
    if error:
        return error

    lines = [f"🔑 Credential: {data.get('displayName', credential_id)}\n"]
    lines.append(f"  • ID: {data.get('id', 'N/A')}")
    lines.append(f"  • Type: {data.get('typeName', 'unknown')}")
    lines.append(f"  • Description: {data.get('description', 'N/A')}")

    # Show username if it's a username/password credential
    username = data.get("username")
    if username:
        lines.append(f"  • Username: {username}")

    return "\n".join(lines)


@mcp.tool()
def jenkins_create_credential(
    credential_id: str,
    credential_type: str,
    username: str = "",
    password: str = "",
    secret: str = "",
    description: str = "",
    domain: str = "_",
    store: str = "system",
    session_name: str = "default",
) -> str:
    """
    Create a new credential in Jenkins.

    Args:
        credential_id: Unique ID for the credential
        credential_type: Type — 'userpass' (username/password), 'secret' (secret text), 'ssh' (SSH key)
        username: Username (for 'userpass' type)
        password: Password (for 'userpass' type) or private key (for 'ssh' type)
        secret: Secret text (for 'secret' type)
        description: Description of the credential
        domain: Credential domain ('_' = global)
        store: Credential store ('system' = system store)
        session_name: Jenkins session to use
    """
    type_map = {
        "userpass": "com.cloudbees.plugins.credentials.impl.UsernamePasswordCredentialsImpl",
        "secret": "org.jenkinsci.plugins.plaincredentials.impl.StringCredentialsImpl",
        "ssh": "com.cloudbees.jenkins.plugins.sshcredentials.impl.BasicSSHUserPrivateKey",
    }

    cls = type_map.get(credential_type.lower())
    if not cls:
        return f"❌ Invalid credential type '{credential_type}'. Valid types: userpass, secret, ssh"

    if credential_type.lower() == "userpass":
        xml = (
            f'<com.cloudbees.plugins.credentials.impl.UsernamePasswordCredentialsImpl>\n'
            f'  <scope>GLOBAL</scope>\n'
            f'  <id>{credential_id}</id>\n'
            f'  <description>{description}</description>\n'
            f'  <username>{username}</username>\n'
            f'  <password>{password}</password>\n'
            f'</com.cloudbees.plugins.credentials.impl.UsernamePasswordCredentialsImpl>'
        )
    elif credential_type.lower() == "secret":
        xml = (
            f'<org.jenkinsci.plugins.plaincredentials.impl.StringCredentialsImpl>\n'
            f'  <scope>GLOBAL</scope>\n'
            f'  <id>{credential_id}</id>\n'
            f'  <description>{description}</description>\n'
            f'  <secret>{secret}</secret>\n'
            f'</org.jenkinsci.plugins.plaincredentials.impl.StringCredentialsImpl>'
        )
    elif credential_type.lower() == "ssh":
        xml = (
            f'<com.cloudbees.jenkins.plugins.sshcredentials.impl.BasicSSHUserPrivateKey>\n'
            f'  <scope>GLOBAL</scope>\n'
            f'  <id>{credential_id}</id>\n'
            f'  <description>{description}</description>\n'
            f'  <username>{username}</username>\n'
            f'  <privateKeySource class="com.cloudbees.jenkins.plugins.sshcredentials.impl.BasicSSHUserPrivateKey$DirectEntryPrivateKeySource">\n'
            f'    <privateKey>{password}</privateKey>\n'
            f'  </privateKeySource>\n'
            f'</com.cloudbees.jenkins.plugins.sshcredentials.impl.BasicSSHUserPrivateKey>'
        )

    _, error = _jenkins.post(
        f"/credentials/store/{store}/domain/{domain}/createCredentials",
        data=f"<com.cloudbees.plugins.credentials.impl.SystemCredentialsProvider_-StoreImpl>{xml}</com.cloudbees.plugins.credentials.impl.SystemCredentialsProvider_-StoreImpl>",
        content_type="application/xml",
        session_name=session_name,
    )
    if error:
        return error

    return f"✅ Credential '{credential_id}' created ({credential_type})."


@mcp.tool()
def jenkins_delete_credential(
    credential_id: str,
    domain: str = "_",
    store: str = "system",
    session_name: str = "default",
) -> str:
    """
    Delete a credential from Jenkins.

    Args:
        credential_id: Credential ID to delete
        domain: Credential domain ('_' = global)
        store: Credential store ('system' = system store)
        session_name: Jenkins session to use
    """
    _, error = _jenkins.post(
        f"/credentials/store/{store}/domain/{domain}/credential/{credential_id}/doDelete",
        session_name=session_name,
    )
    if error:
        return error

    return f"✅ Credential '{credential_id}' deleted."


# ============================================================
# CATEGORY 8: Plugin Management (4 tools)
# ============================================================

@mcp.tool()
def jenkins_list_plugins(session_name: str = "default") -> str:
    """
    List all installed Jenkins plugins with version and status.

    Args:
        session_name: Jenkins session to use
    """
    data, error = _jenkins.get(
        "/pluginManager/api/json?tree=plugins[shortName,longName,version,active,enabled,hasUpdate,url]&depth=1",
        session_name=session_name,
    )
    if error:
        return error

    plugins = data.get("plugins", [])
    if not plugins:
        return "🧩 No plugins found."

    # Sort by name
    plugins.sort(key=lambda p: p.get("shortName", ""))

    active_count = sum(1 for p in plugins if p.get("active"))
    update_count = sum(1 for p in plugins if p.get("hasUpdate"))

    lines = [f"🧩 Installed Plugins ({len(plugins)} total, {active_count} active, {update_count} updates available):\n"]
    for plugin in plugins:
        icon = "✅" if plugin.get("active") else "⛔"
        update = " 🔄" if plugin.get("hasUpdate") else ""
        lines.append(
            f"  {icon} {plugin.get('shortName', '?')} v{plugin.get('version', '?')}{update}"
            f"  — {plugin.get('longName', '')}"
        )

    return "\n".join(lines)


@mcp.tool()
def jenkins_get_plugin_info(plugin_name: str, session_name: str = "default") -> str:
    """
    Get detailed information about a specific installed plugin.

    Args:
        plugin_name: Plugin short name (e.g., 'git', 'pipeline-model-definition')
        session_name: Jenkins session to use
    """
    data, error = _jenkins.get(
        "/pluginManager/api/json?tree=plugins[shortName,longName,version,active,enabled,"
        "hasUpdate,url,dependencies[shortName,version,optional]]&depth=2",
        session_name=session_name,
    )
    if error:
        return error

    plugins = data.get("plugins", [])
    plugin = next((p for p in plugins if p.get("shortName") == plugin_name), None)

    if not plugin:
        return f"❌ Plugin '{plugin_name}' not found. Use jenkins_list_plugins to see installed plugins."

    lines = [f"🧩 Plugin: {plugin.get('longName', plugin_name)}\n"]
    lines.append(f"  • Short Name: {plugin.get('shortName')}")
    lines.append(f"  • Version: {plugin.get('version', '?')}")
    lines.append(f"  • Active: {plugin.get('active', False)}")
    lines.append(f"  • Enabled: {plugin.get('enabled', False)}")
    lines.append(f"  • Update Available: {plugin.get('hasUpdate', False)}")

    url = plugin.get("url")
    if url:
        lines.append(f"  • URL: {url}")

    deps = plugin.get("dependencies", [])
    if deps:
        required = [d for d in deps if not d.get("optional")]
        optional = [d for d in deps if d.get("optional")]
        if required:
            lines.append(f"\n  Required Dependencies ({len(required)}):")
            for d in required[:15]:
                lines.append(f"    • {d.get('shortName', '?')} v{d.get('version', '?')}")
        if optional:
            lines.append(f"\n  Optional Dependencies ({len(optional)}):")
            for d in optional[:10]:
                lines.append(f"    • {d.get('shortName', '?')} v{d.get('version', '?')}")

    return "\n".join(lines)


@mcp.tool()
def jenkins_install_plugin(
    plugin_name: str,
    version: str = "",
    session_name: str = "default",
) -> str:
    """
    Install a Jenkins plugin.

    The plugin will be downloaded and installed. Jenkins may need a restart to activate it.

    Args:
        plugin_name: Plugin short name (e.g., 'git', 'blueocean')
        version: Specific version to install (empty = latest)
        session_name: Jenkins session to use
    """
    plugin_id = f"{plugin_name}@{version}" if version else f"{plugin_name}@latest"

    xml_data = f'<jenkins><install plugin="{plugin_id}" /></jenkins>'
    _, error = _jenkins.post(
        "/pluginManager/installNecessaryPlugins",
        data=xml_data,
        content_type="application/xml",
        session_name=session_name,
    )
    if error:
        return error

    return (
        f"✅ Plugin '{plugin_name}' installation initiated"
        + (f" (version: {version})" if version else " (latest version)")
        + ".\n\n💡 A Jenkins restart may be required. Use jenkins_restart(safe=True) to restart safely."
    )


@mcp.tool()
def jenkins_list_available_plugins(
    query: str = "",
    session_name: str = "default",
) -> str:
    """
    Search available plugins for installation from the Jenkins Update Center.

    Args:
        query: Search query to filter plugins (empty = list all available)
        session_name: Jenkins session to use
    """
    data, error = _jenkins.get(
        "/pluginManager/api/json?tree=plugins[shortName]",
        session_name=session_name,
    )
    if error:
        return error

    # Get available plugins from update center
    uc_data, uc_error = _jenkins.get(
        "/updateCenter/coreSource/api/json?tree=availables[name,title,version,wiki]&depth=1",
        session_name=session_name,
    )

    if uc_error:
        # Fallback: try the site API
        uc_data, uc_error = _jenkins.get(
            "/updateCenter/api/json?tree=availables[name,title,version]",
            session_name=session_name,
        )

    if uc_error:
        return f"❌ Could not fetch available plugins: {uc_error}"

    availables = uc_data.get("availables", [])

    if query:
        q = query.lower()
        availables = [
            p for p in availables
            if q in p.get("name", "").lower() or q in p.get("title", "").lower()
        ]

    if not availables:
        return f"🧩 No available plugins found" + (f" matching '{query}'" if query else "") + "."

    lines = [f"🧩 Available Plugins ({len(availables)}):\n"]
    for plugin in availables[:50]:
        lines.append(f"  • {plugin.get('name', '?')} v{plugin.get('version', '?')} — {plugin.get('title', '')}")

    if len(availables) > 50:
        lines.append(f"\n  ... and {len(availables) - 50} more. Use a more specific query to narrow results.")

    return "\n".join(lines)


# ============================================================
# CATEGORY 9: Pipeline & Folder Operations (4 tools)
# ============================================================

@mcp.tool()
def jenkins_list_folder_jobs(
    folder_path: str,
    session_name: str = "default",
) -> str:
    """
    List all jobs inside a Jenkins folder (recursive).

    Args:
        folder_path: Folder path (e.g., 'my-folder' or 'parent/child-folder')
        session_name: Jenkins session to use
    """
    return jenkins_list_jobs(folder=folder_path, session_name=session_name)


@mcp.tool()
def jenkins_create_folder(
    folder_name: str,
    parent_folder: str = "",
    description: str = "",
    session_name: str = "default",
) -> str:
    """
    Create a new folder in Jenkins.

    Args:
        folder_name: Name for the new folder
        parent_folder: Parent folder path (empty = root level)
        description: Folder description
        session_name: Jenkins session to use
    """
    config_xml = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<com.cloudbees.hudson.plugins.folder.Folder plugin="cloudbees-folder">\n'
        f'  <description>{description}</description>\n'
        '  <properties/>\n'
        '  <views>\n'
        '    <hudson.model.AllView>\n'
        '      <name>All</name>\n'
        '      <filterExecutors>false</filterExecutors>\n'
        '      <filterQueue>false</filterQueue>\n'
        '      <properties class="hudson.model.View$PropertyList"/>\n'
        '    </hudson.model.AllView>\n'
        '  </views>\n'
        '  <viewsTabBar class="hudson.views.DefaultViewsTabBar"/>\n'
        '  <healthMetrics/>\n'
        '</com.cloudbees.hudson.plugins.folder.Folder>'
    )

    return jenkins_create_job(
        job_name=folder_name,
        config_xml=config_xml,
        folder=parent_folder,
        session_name=session_name,
    )


@mcp.tool()
def jenkins_get_pipeline_stages(
    job_name: str,
    build_number: int = 0,
    session_name: str = "default",
) -> str:
    """
    Get pipeline stage details and status for a pipeline build.

    Shows each stage's name, status, and duration. Requires the Pipeline: REST API plugin.

    Args:
        job_name: Pipeline job name
        build_number: Build number (0 = last build)
        session_name: Jenkins session to use
    """
    path = _jenkins.job_path(job_name)
    build = build_number if build_number > 0 else "lastBuild"

    data, error = _jenkins.get(
        f"{path}/{build}/wfapi/describe",
        session_name=session_name,
    )
    if error:
        return f"❌ Could not fetch pipeline stages. Make sure this is a Pipeline job and the Pipeline REST API plugin is installed.\n\n{error}"

    lines = [f"🔀 Pipeline: {data.get('name', job_name)} — Build #{data.get('id', build)}\n"]
    lines.append(f"  • Status: {data.get('status', 'unknown')}")
    lines.append(f"  • Duration: {_format_duration(data.get('durationMillis', 0))}")

    stages = data.get("stages", [])
    if stages:
        lines.append(f"\n  Stages ({len(stages)}):")
        for stage in stages:
            status = stage.get("status", "unknown")
            status_map = {
                "SUCCESS": "🟢", "FAILED": "🔴", "IN_PROGRESS": "🔵",
                "ABORTED": "⚫", "NOT_EXECUTED": "⬜", "UNSTABLE": "🟡",
            }
            icon = status_map.get(status, "❓")
            duration = _format_duration(stage.get("durationMillis", 0))
            lines.append(f"    {icon} {stage.get('name', '?')} — {status} ({duration})")
    else:
        lines.append("\n  No stages found.")

    return "\n".join(lines)


@mcp.tool()
def jenkins_replay_pipeline(
    job_name: str,
    build_number: int,
    script: str = "",
    session_name: str = "default",
) -> str:
    """
    Replay a pipeline build, optionally with a modified Groovy script.

    This re-runs a pipeline build, allowing you to edit the pipeline script
    without modifying the Jenkinsfile.

    Args:
        job_name: Pipeline job name
        build_number: Build number to replay
        script: Modified pipeline script (empty = use original script)
        session_name: Jenkins session to use
    """
    path = _jenkins.job_path(job_name)

    if not script:
        # Get the original script first
        orig_data, orig_error = _jenkins.get(
            f"{path}/{build_number}/replay",
            session_name=session_name,
            raw=True,
        )
        if orig_error:
            return f"❌ Could not fetch original script for replay: {orig_error}"

        return (
            f"📜 Original pipeline script for Build #{build_number}:\n\n{orig_data}\n\n"
            f"💡 To replay with modifications, call this tool again with the 'script' parameter."
        )

    _, error = _jenkins.post(
        f"{path}/{build_number}/replay/run",
        data=f"json={json.dumps({'mainScript': script})}",
        content_type="application/x-www-form-urlencoded",
        session_name=session_name,
    )
    if error:
        return error

    return f"✅ Pipeline build #{build_number} of '{job_name}' replayed with modified script."


# ============================================================
# CATEGORY 10: System & Administration (5 tools)
# ============================================================

@mcp.tool()
def jenkins_system_info(session_name: str = "default") -> str:
    """
    Get comprehensive Jenkins system information.

    Shows version, JVM info, system properties, and environment overview.

    Args:
        session_name: Jenkins session to use
    """
    # Get basic info
    data, error = _jenkins.get(
        "/api/json?tree=mode,nodeDescription,numExecutors,quietingDown,useSecurity,"
        "primaryView[name],views[name]",
        session_name=session_name,
    )
    if error:
        return error

    lines = ["🏗️ Jenkins System Information\n"]
    lines.append(f"  • Mode: {data.get('mode', 'unknown')}")
    lines.append(f"  • Description: {data.get('nodeDescription', 'N/A')}")
    lines.append(f"  • Executors: {data.get('numExecutors', 'N/A')}")
    lines.append(f"  • Quieting Down: {'Yes' if data.get('quietingDown') else 'No'}")
    lines.append(f"  • Security: {'Enabled' if data.get('useSecurity') else 'Disabled'}")

    primary_view = data.get("primaryView", {})
    if primary_view:
        lines.append(f"  • Primary View: {primary_view.get('name', 'N/A')}")

    views = data.get("views", [])
    lines.append(f"  • Views: {len(views)}")

    # Get node info for more details
    node_data, _ = _jenkins.get(
        "/computer/api/json?tree=totalExecutors,busyExecutors",
        session_name=session_name,
    )
    if node_data:
        lines.append(f"\n⚙️ Executors:")
        lines.append(f"  • Total: {node_data.get('totalExecutors', 'N/A')}")
        lines.append(f"  • Busy: {node_data.get('busyExecutors', 'N/A')}")

    # Get queue info
    queue_data, _ = _jenkins.get(
        "/queue/api/json?tree=items[id]",
        session_name=session_name,
    )
    if queue_data:
        queue_items = queue_data.get("items", [])
        lines.append(f"\n📬 Queue: {len(queue_items)} item(s)")

    return "\n".join(lines)


@mcp.tool()
def jenkins_restart(safe: bool = True, session_name: str = "default") -> str:
    """
    Restart the Jenkins server.

    Args:
        safe: If True (default), waits for running builds to finish before restarting.
              If False, restarts immediately (may abort running builds).
        session_name: Jenkins session to use
    """
    endpoint = "/safeRestart" if safe else "/restart"
    restart_type = "Safe restart" if safe else "Immediate restart"

    _, error = _jenkins.post(endpoint, session_name=session_name)
    if error:
        return error

    return (
        f"✅ {restart_type} initiated.\n"
        f"{'Jenkins will restart after all running builds complete.' if safe else '⚠️ Jenkins is restarting immediately. Running builds may be aborted.'}\n\n"
        f"💡 Use jenkins_connect to reconnect after restart."
    )


@mcp.tool()
def jenkins_quiet_down(session_name: str = "default") -> str:
    """
    Put Jenkins into quiet-down mode (no new builds will be started).

    Running builds will continue but no new builds will be queued.
    Useful before maintenance or restart.

    Args:
        session_name: Jenkins session to use
    """
    _, error = _jenkins.post("/quietDown", session_name=session_name)
    if error:
        return error

    return "✅ Jenkins is now in quiet-down mode. No new builds will be started."


@mcp.tool()
def jenkins_cancel_quiet_down(session_name: str = "default") -> str:
    """
    Cancel quiet-down mode and resume normal operations.

    Queued builds will begin processing again.

    Args:
        session_name: Jenkins session to use
    """
    _, error = _jenkins.post("/cancelQuietDown", session_name=session_name)
    if error:
        return error

    return "✅ Quiet-down mode cancelled. Jenkins is back to normal operations."


@mcp.tool()
def jenkins_run_groovy_script(
    script: str,
    session_name: str = "default",
) -> str:
    """
    Execute a Groovy script on the Jenkins Script Console.

    ⚠️ This is a powerful admin tool. Scripts run with full Jenkins access.

    Common scripts:
    - List all jobs: 'Jenkins.instance.items.each { println it.name }'
    - Get Jenkins version: 'println Jenkins.instance.version'
    - List users: 'Jenkins.instance.securityRealm.getAllUsers().each { println it.id }'

    Args:
        script: Groovy script to execute
        session_name: Jenkins session to use
    """
    data, error = _jenkins.post(
        "/scriptText",
        data=f"script={script}",
        content_type="application/x-www-form-urlencoded",
        session_name=session_name,
    )
    if error:
        return error

    return f"📜 Script Output:\n\n{data}" if data else "📜 Script executed (no output)."


# ============================================================
# Helper Functions
# ============================================================

def _format_duration(ms: int) -> str:
    """Format milliseconds into human-readable duration."""
    if ms <= 0:
        return "0s"
    seconds = ms // 1000
    if seconds < 60:
        return f"{seconds}s"
    elif seconds < 3600:
        m = seconds // 60
        s = seconds % 60
        return f"{m}m {s}s"
    else:
        h = seconds // 3600
        m = (seconds % 3600) // 60
        return f"{h}h {m}m"


def _format_build_summary(label: str, job_name: str, data: dict) -> str:
    """Format a build info response."""
    result = data.get("result", "IN PROGRESS") if not data.get("building") else "🔄 BUILDING"
    result_icon = {"SUCCESS": "🟢", "FAILURE": "🔴", "UNSTABLE": "🟡", "ABORTED": "⚫"}
    icon = result_icon.get(data.get("result", ""), "🔵")

    lines = [f"{icon} {label} — {job_name}\n"]
    lines.append(f"  • Build: #{data.get('number', '?')}")
    lines.append(f"  • Result: {result}")
    lines.append(f"  • Duration: {_format_duration(data.get('duration', 0))}")

    ts = data.get("timestamp")
    if ts:
        import datetime
        dt = datetime.datetime.fromtimestamp(ts / 1000)
        lines.append(f"  • Started: {dt.strftime('%Y-%m-%d %H:%M:%S')}")

    display = data.get("displayName")
    if display:
        lines.append(f"  • Display: {display}")

    # Causes
    for action in data.get("actions", []):
        causes = action.get("causes", [])
        for cause in causes:
            lines.append(f"  • Trigger: {cause.get('shortDescription', 'unknown')}")

    return "\n".join(lines)


# ============================================================
# Entry Point
# ============================================================

def main() -> None:
    """Console entry point for PyPI / uvx installs."""
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
