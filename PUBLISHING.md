# Publishing Guide — Jenkins MCP

This guide walks you through publishing **jenkins-mcp** so developers and AI agents can discover and install it.

## Checklist

- [x] `README.md` with install instructions
- [x] `pyproject.toml` with metadata and console script
- [x] `smithery.yaml` for Smithery registry
- [x] `LICENSE` (MIT)
- [ ] Publish to PyPI
- [ ] Submit to Smithery
- [ ] Submit to Glama & Pulse MCP directories
- [ ] Set GitHub topics

---

## 1. Publish to PyPI

```bash
pip install build twine
cd jenkins-mcp
python -m build
twine upload dist/*
```

### MCP config after PyPI publish

```json
{
  "mcpServers": {
    "jenkins": {
      "command": "uvx",
      "args": ["pawangunjkar-jenkins-mcp"],
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

## 2. Submit to Smithery

1. Go to [https://smithery.ai](https://smithery.ai) → sign in with GitHub
2. Publish `Pawangunjkar/jenkins-mcp` repository
3. Smithery reads `smithery.yaml` (requires Jenkins URL, username, API token)

---

## 3. List on MCP Directories

| Directory | URL |
|-----------|-----|
| **Glama** | https://glama.ai/mcp/servers |
| **Pulse MCP** | https://www.pulsemcp.com |

Submit: `https://github.com/Pawangunjkar/jenkins-mcp`

---

## 4. GitHub Topics

```
mcp, model-context-protocol, mcp-server, jenkins, ci-cd, devops, build-automation, python
```

```bash
gh repo edit Pawangunjkar/jenkins-mcp \
  --add-topic mcp,model-context-protocol,mcp-server,jenkins,ci-cd,devops,python
```

---

## Support

- **Issues:** https://github.com/Pawangunjkar/jenkins-mcp/issues
- **Author:** Pawan Gunjkar — pawangunjkar@gmail.com
