"""
Jenkins REST API Client for Jenkins MCP Server.

Author: Pawan Gunjkar (pawangunjkar@gamil.com)

Handles all HTTP communication with Jenkins servers:
- Basic authentication with API tokens
- CSRF crumb auto-fetching and caching
- GET/POST request helpers with error handling
- Connection management and validation
- Output formatting for MCP tool responses
"""

import sys
import time
from typing import Optional, Any
from urllib.parse import quote as url_quote

import httpx

from credential_store import CredentialStore, JenkinsCredentials


# Constants
DEFAULT_TIMEOUT = 30
MAX_OUTPUT_SIZE = 50 * 1024  # 50KB


class JenkinsClient:
    """
    Jenkins REST API client.

    Manages HTTP sessions with Jenkins servers, handles authentication,
    CSRF crumb management, and provides typed API methods.
    """

    def __init__(self, credential_store: Optional[CredentialStore] = None):
        self._credentials = credential_store or CredentialStore()
        self._sessions: dict[str, _JenkinsSession] = {}

    @property
    def credential_store(self) -> CredentialStore:
        return self._credentials

    def connect(
        self,
        session_name: str = "default",
        url: Optional[str] = None,
        username: Optional[str] = None,
        api_token: Optional[str] = None,
        ssl_verify: bool = True,
        timeout: int = DEFAULT_TIMEOUT,
        save_credentials: bool = True,
    ) -> str:
        """
        Connect to a Jenkins server and create a named session.

        Returns a status message.
        """
        # If already connected with this session name, disconnect first
        if session_name in self._sessions:
            self.disconnect(session_name)

        # If no URL provided, try to get from credential store
        if not url:
            creds = self._credentials.get_credentials(session_name)
            if creds:
                url = creds.url
                username = username or creds.username
                api_token = api_token or creds.api_token
                ssl_verify = creds.ssl_verify
                timeout = creds.timeout
            else:
                return (
                    f"❌ No credentials found for session '{session_name}'.\n\n"
                    f"Please provide connection details:\n"
                    f"  • url: Jenkins server URL (e.g., 'http://localhost:8080')\n"
                    f"  • username: Jenkins username (default: admin)\n"
                    f"  • api_token: Jenkins API token\n\n"
                    f"Example: jenkins_connect(url='http://localhost:8080', username='admin', api_token='your-token')\n\n"
                    f"💡 To generate an API token:\n"
                    f"   1. Log in to Jenkins → Your name → Configure\n"
                    f"   2. Under 'API Token' → Add new Token → Generate\n"
                    f"   3. Copy the token value"
                )

        if not url:
            return "❌ Jenkins URL is required."
        if not api_token:
            return "❌ Jenkins API token is required."

        url = url.rstrip("/")
        username = username or "admin"

        try:
            # Create HTTP client
            client = httpx.Client(
                base_url=url,
                auth=(username, api_token),
                verify=ssl_verify,
                timeout=timeout,
                follow_redirects=True,
                headers={"Accept": "application/json"},
            )

            # Validate connection by fetching Jenkins info
            response = client.get("/api/json?tree=mode,nodeDescription,useSecurity")
            response.raise_for_status()
            info = response.json()

            # Fetch crumb for CSRF protection
            crumb_header = None
            crumb_value = None
            try:
                crumb_response = client.get("/crumbIssuer/api/json")
                if crumb_response.status_code == 200:
                    crumb_data = crumb_response.json()
                    crumb_header = crumb_data.get("crumbRequestField")
                    crumb_value = crumb_data.get("crumb")
            except Exception:
                pass  # CSRF may be disabled

            # Create session
            session = _JenkinsSession(
                name=session_name,
                url=url,
                username=username,
                client=client,
                crumb_header=crumb_header,
                crumb_value=crumb_value,
            )
            self._sessions[session_name] = session

            # Cache credentials
            if save_credentials:
                self._credentials.save_credentials(
                    session_name=session_name,
                    url=url,
                    username=username,
                    api_token=api_token,
                    ssl_verify=ssl_verify,
                    timeout=timeout,
                )

            print(f"Connected to Jenkins at {url} as {username} (session: {session_name})", file=sys.stderr)

            csrf_status = "✅ enabled" if crumb_header else "⚠️ disabled"
            return (
                f"✅ Connected to Jenkins successfully!\n"
                f"  • Session: {session_name}\n"
                f"  • URL: {url}\n"
                f"  • User: {username}\n"
                f"  • Mode: {info.get('mode', 'unknown')}\n"
                f"  • CSRF Protection: {csrf_status}\n"
                f"  • Credentials cached for future use"
            )

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                return f"❌ Authentication failed for {username}@{url}. Check your username and API token."
            elif e.response.status_code == 403:
                return f"❌ Access forbidden at {url}. Check permissions for user '{username}'."
            return f"❌ HTTP error connecting to {url}: {e.response.status_code} {e.response.reason_phrase}"
        except httpx.ConnectError:
            return f"❌ Connection failed to {url}. Check if Jenkins is running and the URL is correct."
        except httpx.TimeoutException:
            return f"❌ Connection timed out to {url}. Check if Jenkins is reachable."
        except Exception as e:
            return f"❌ Failed to connect to {url}: {str(e)}"

    def disconnect(self, session_name: str = "default") -> str:
        """Disconnect a specific session."""
        if session_name not in self._sessions:
            return f"⚠️ No active session named '{session_name}'."

        session = self._sessions.pop(session_name)
        try:
            session.client.close()
        except Exception:
            pass

        return f"✅ Disconnected session '{session_name}' from {session.url}"

    def disconnect_all(self) -> str:
        """Disconnect all sessions."""
        if not self._sessions:
            return "⚠️ No active sessions to disconnect."

        names = list(self._sessions.keys())
        for name in names:
            self.disconnect(name)

        return f"✅ Disconnected {len(names)} session(s): {', '.join(names)}"

    def _get_session(self, session_name: str = "default") -> tuple[Optional["_JenkinsSession"], Optional[str]]:
        """
        Get a session by name, auto-connecting if credentials are cached.

        Returns (session, error_message).
        """
        if session_name not in self._sessions:
            # Try auto-connect from credentials
            creds = self._credentials.get_credentials(session_name)
            if creds:
                result = self.connect(
                    session_name=session_name,
                    url=creds.url,
                    username=creds.username,
                    api_token=creds.api_token,
                    ssl_verify=creds.ssl_verify,
                    timeout=creds.timeout,
                    save_credentials=False,
                )
                if session_name in self._sessions:
                    return self._sessions[session_name], None
                else:
                    return None, result

            return None, (
                f"❌ No active session '{session_name}'.\n\n"
                f"Please connect first using jenkins_connect:\n"
                f"  jenkins_connect(url='http://your-jenkins:8080', username='admin', api_token='your-token')\n\n"
                f"Active sessions: {', '.join(self._sessions.keys()) if self._sessions else 'none'}"
            )

        return self._sessions[session_name], None

    def _refresh_crumb(self, session: "_JenkinsSession") -> None:
        """Refresh the CSRF crumb for a session."""
        try:
            response = session.client.get("/crumbIssuer/api/json")
            if response.status_code == 200:
                data = response.json()
                session.crumb_header = data.get("crumbRequestField")
                session.crumb_value = data.get("crumb")
        except Exception:
            pass

    # ================================================================
    # Core HTTP Methods
    # ================================================================

    def get(
        self,
        path: str,
        session_name: str = "default",
        params: Optional[dict] = None,
        raw: bool = False,
    ) -> tuple[Optional[Any], Optional[str]]:
        """
        Perform a GET request.

        Returns (data, error). If raw=True, returns response text instead of JSON.
        """
        session, error = self._get_session(session_name)
        if error:
            return None, error

        try:
            response = session.client.get(path, params=params)
            response.raise_for_status()
            session.last_used = time.time()
            session.request_count += 1

            if raw:
                text = response.text
                if len(text) > MAX_OUTPUT_SIZE:
                    text = text[:MAX_OUTPUT_SIZE] + f"\n\n... [OUTPUT TRUNCATED — {len(response.text)} bytes total]"
                return text, None

            return response.json(), None

        except httpx.HTTPStatusError as e:
            return None, f"❌ HTTP {e.response.status_code}: {e.response.reason_phrase} — {path}"
        except Exception as e:
            return None, f"❌ Request failed: {str(e)}"

    def post(
        self,
        path: str,
        session_name: str = "default",
        data: Optional[str] = None,
        params: Optional[dict] = None,
        content_type: Optional[str] = None,
        expect_json: bool = False,
    ) -> tuple[Optional[Any], Optional[str]]:
        """
        Perform a POST request with CSRF crumb.

        Returns (data, error).
        """
        session, error = self._get_session(session_name)
        if error:
            return None, error

        headers = {}

        # Add CSRF crumb
        if session.crumb_header and session.crumb_value:
            headers[session.crumb_header] = session.crumb_value

        if content_type:
            headers["Content-Type"] = content_type

        try:
            response = session.client.post(
                path,
                content=data,
                params=params,
                headers=headers,
            )

            # If we get a 403, try refreshing the crumb and retry once
            if response.status_code == 403 and session.crumb_header:
                self._refresh_crumb(session)
                if session.crumb_header and session.crumb_value:
                    headers[session.crumb_header] = session.crumb_value
                    response = session.client.post(
                        path,
                        content=data,
                        params=params,
                        headers=headers,
                    )

            response.raise_for_status()
            session.last_used = time.time()
            session.request_count += 1

            if expect_json and response.text.strip():
                return response.json(), None

            return response.text, None

        except httpx.HTTPStatusError as e:
            body = ""
            try:
                body = e.response.text[:500]
            except Exception:
                pass
            return None, f"❌ HTTP {e.response.status_code}: {e.response.reason_phrase} — {path}\n{body}".strip()
        except Exception as e:
            return None, f"❌ Request failed: {str(e)}"

    # ================================================================
    # Jenkins Path Helpers
    # ================================================================

    @staticmethod
    def job_path(job_name: str) -> str:
        """
        Convert a job name (possibly with folder path) to Jenkins URL path.

        Examples:
            'my-job' → '/job/my-job'
            'folder/my-job' → '/job/folder/job/my-job'
            'folder/subfolder/my-job' → '/job/folder/job/subfolder/job/my-job'
        """
        parts = job_name.strip("/").split("/")
        return "/job/" + "/job/".join(url_quote(p, safe="") for p in parts)

    # ================================================================
    # Session Info
    # ================================================================

    def list_sessions(self) -> list[dict]:
        """List all active sessions."""
        sessions = []
        for session in self._sessions.values():
            sessions.append(session.info())
        return sessions

    def is_connected(self, session_name: str = "default") -> bool:
        """Check if a session exists."""
        return session_name in self._sessions


class _JenkinsSession:
    """Represents a single Jenkins HTTP session."""

    def __init__(
        self,
        name: str,
        url: str,
        username: str,
        client: httpx.Client,
        crumb_header: Optional[str] = None,
        crumb_value: Optional[str] = None,
    ):
        self.name = name
        self.url = url
        self.username = username
        self.client = client
        self.crumb_header = crumb_header
        self.crumb_value = crumb_value
        self.connected_at = time.time()
        self.last_used = time.time()
        self.request_count = 0

    @property
    def uptime_str(self) -> str:
        secs = int(time.time() - self.connected_at)
        if secs < 60:
            return f"{secs}s"
        elif secs < 3600:
            return f"{secs // 60}m {secs % 60}s"
        else:
            h = secs // 3600
            m = (secs % 3600) // 60
            return f"{h}h {m}m"

    def info(self) -> dict:
        """Return session info as a dictionary."""
        return {
            "session_name": self.name,
            "url": self.url,
            "username": self.username,
            "csrf_enabled": bool(self.crumb_header),
            "uptime": self.uptime_str,
            "requests": self.request_count,
        }
