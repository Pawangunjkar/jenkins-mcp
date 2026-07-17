"""
Credential Store for Jenkins MCP Server.

Author: Pawan Gunjkar (pawangunjkar@gamil.com)

Manages Jenkins connection credentials with a layered lookup strategy:
1. Environment variables (JENKINS_URL, JENKINS_USERNAME, JENKINS_API_TOKEN)
2. In-memory cache (current server session)
3. Local file cache (~/.jenkins-mcp-cache/credentials.json)
4. If none found → returns None (server will prompt user)
"""

import json
import os
import sys
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional


@dataclass
class JenkinsCredentials:
    """Jenkins connection credentials."""
    url: str
    username: str = "admin"
    api_token: Optional[str] = None
    ssl_verify: bool = True
    timeout: int = 30

    def to_dict(self) -> dict:
        """Convert to dictionary (excludes None values)."""
        return {k: v for k, v in asdict(self).items() if v is not None}

    @classmethod
    def from_dict(cls, data: dict) -> "JenkinsCredentials":
        """Create from dictionary."""
        return cls(
            url=data["url"].rstrip("/"),
            username=data.get("username", "admin"),
            api_token=data.get("api_token"),
            ssl_verify=data.get("ssl_verify", True),
            timeout=int(data.get("timeout", 30)),
        )

    def masked_dict(self) -> dict:
        """Return dict with API token masked (for display)."""
        d = self.to_dict()
        if "api_token" in d and d["api_token"]:
            token = d["api_token"]
            d["api_token"] = "****" + token[-4:] if len(token) > 4 else "****"
        return d


class CredentialStore:
    """
    Multi-layer credential store for Jenkins connections.

    Credentials are cached in memory and optionally persisted to a JSON file.
    """

    def __init__(self, cache_dir: Optional[str] = None):
        """Initialize the credential store."""
        self._memory_cache: dict[str, JenkinsCredentials] = {}

        # Determine cache directory
        if cache_dir:
            self._cache_dir = Path(cache_dir)
        else:
            env_cache_dir = os.environ.get("JENKINS_MCP_CACHE_DIR")
            if env_cache_dir:
                self._cache_dir = Path(env_cache_dir)
            else:
                self._cache_dir = Path.home() / ".jenkins-mcp-cache"

        self._cache_file = self._cache_dir / "credentials.json"
        self._ensure_cache_dir()
        self._load_file_cache()

    def _ensure_cache_dir(self):
        """Create cache directory if it doesn't exist."""
        try:
            self._cache_dir.mkdir(parents=True, exist_ok=True)
            # Set restrictive permissions on Unix-like systems
            if sys.platform != "win32":
                os.chmod(self._cache_dir, 0o700)
        except OSError as e:
            print(f"Warning: Could not create cache directory: {e}", file=sys.stderr)

    def _load_file_cache(self):
        """Load credentials from the JSON cache file."""
        if self._cache_file.exists():
            try:
                with open(self._cache_file, "r") as f:
                    data = json.load(f)
                for name, cred_data in data.items():
                    if name not in self._memory_cache:
                        self._memory_cache[name] = JenkinsCredentials.from_dict(cred_data)
                print(f"Loaded {len(data)} cached credential(s) from {self._cache_file}", file=sys.stderr)
            except (json.JSONDecodeError, KeyError, OSError) as e:
                print(f"Warning: Could not load credential cache: {e}", file=sys.stderr)

    def _save_file_cache(self):
        """Save all credentials to the JSON cache file."""
        try:
            data = {name: cred.to_dict() for name, cred in self._memory_cache.items()}
            with open(self._cache_file, "w") as f:
                json.dump(data, f, indent=2)
            # Set restrictive permissions on the file
            if sys.platform != "win32":
                os.chmod(self._cache_file, 0o600)
        except OSError as e:
            print(f"Warning: Could not save credential cache: {e}", file=sys.stderr)

    def get_from_env(self) -> Optional[JenkinsCredentials]:
        """
        Try to get credentials from environment variables.

        Looks for: JENKINS_URL, JENKINS_USERNAME, JENKINS_API_TOKEN
        """
        url = os.environ.get("JENKINS_URL")
        if not url:
            return None

        api_token = os.environ.get("JENKINS_API_TOKEN")
        if not api_token:
            return None

        ssl_verify_str = os.environ.get("JENKINS_SSL_VERIFY", "true").lower()
        ssl_verify = ssl_verify_str not in ("false", "0", "no")

        return JenkinsCredentials(
            url=url.rstrip("/"),
            username=os.environ.get("JENKINS_USERNAME", "admin"),
            api_token=api_token,
            ssl_verify=ssl_verify,
            timeout=int(os.environ.get("JENKINS_TIMEOUT", "30")),
        )

    def get_credentials(self, session_name: str = "default") -> Optional[JenkinsCredentials]:
        """
        Get credentials using layered lookup.

        Order: env vars (for 'default') → memory cache → file cache → None
        """
        # For the default session, try environment variables first
        if session_name == "default":
            env_creds = self.get_from_env()
            if env_creds:
                return env_creds

        # Check memory cache (includes file cache loaded at startup)
        if session_name in self._memory_cache:
            return self._memory_cache[session_name]

        return None

    def save_credentials(
        self,
        session_name: str,
        url: str,
        username: str = "admin",
        api_token: Optional[str] = None,
        ssl_verify: bool = True,
        timeout: int = 30,
    ) -> JenkinsCredentials:
        """Save credentials to memory and file cache."""
        creds = JenkinsCredentials(
            url=url.rstrip("/"),
            username=username,
            api_token=api_token,
            ssl_verify=ssl_verify,
            timeout=timeout,
        )
        self._memory_cache[session_name] = creds
        self._save_file_cache()
        return creds

    def delete_credentials(self, session_name: str) -> bool:
        """Delete credentials for a session from all caches."""
        if session_name in self._memory_cache:
            del self._memory_cache[session_name]
            self._save_file_cache()
            return True
        return False

    def list_sessions(self) -> dict[str, dict]:
        """List all cached session credentials (with tokens masked)."""
        result = {}

        # Include env-based default if available
        env_creds = self.get_from_env()
        if env_creds and "default" not in self._memory_cache:
            result["default (env)"] = env_creds.masked_dict()

        for name, cred in self._memory_cache.items():
            result[name] = cred.masked_dict()

        return result

    def clear_all(self):
        """Clear all cached credentials."""
        self._memory_cache.clear()
        if self._cache_file.exists():
            try:
                self._cache_file.unlink()
            except OSError:
                pass
