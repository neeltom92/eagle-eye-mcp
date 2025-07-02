


## Eagle-Eye: the 'On-Call & Observability MCP Server'

Eagle-Eye is a set of read-only MCP servers created to assist with on-call duties and provide Observability insights to make on-call life easier using the power of AI.

Eagle-Eye interacts with the following services using the MCP servers:

*   Kubernetes (k8s)
*   PagerDuty
*   Prometheus
*   Datadog
*   *...many more coming soon!  are in the process of adding more built-in MCP servers.*

It's written in Python using the [FastMCP framework](https://gofastmcp.com/getting-started/welcome). The MCP server code is located in respective directories under the `tools/` folder.

## MCP protocol overview

MCP is an open protocol created by Anthropic (founders of Claude AI) that standardizes the way AI apps connect and interact with external tools, services, and data sources using the APIs those services expose, its like a proxy that sits between the AI client and the service.

- https://docs.anthropic.com/en/docs/agents-and-tools/mcp
- https://blog.bytebytego.com/i/159075598/what-is-mcp

## Why the need for an in-house MCP server?

* Most third-party MCP servers are open source and built by unknown authors. They pose security risks (e.g., potential backdoors, data exfiltration).
* We currently lack formal guardrails for their use. For example, we could add a third-party MCP server to Cursor IDE/Qcli and request it to fetch pods from Kubernetes—but instead of fetching them, it could delete the pods.
* There's some good reads on MCP security issues:

-- https://invariantlabs.ai/blog/mcp-github-vulnerability

--  https://www.lasso.security/blog/why-mcp-agents-are-the-next-cyber-battleground


## Project Setup

This project uses `uv` for Python environment and package management.
**Recommended First-Time Setup:**

1.  Clone the repo and switch to the `develop` branch (currently, the code is not merged to `main` since active work is going on in this repo to make it better).
2.  We've added a `Makefile` to make installation easier.

    1.  **Install `uv` and Setup Environments:**

        *Step 1: Install `uv`*
        ```bash
        make install-uv
        ```
        After this command completes, **ensure `uv` is in your system's `PATH`**. You might need to source your shell profile (e.g., `source ~/.zshrc` or `source ~/.bashrc`) or open a new terminal window for the changes to take effect.

        *Step 2: Set up Virtual Environments & Install Dependencies*
        Once `uv` is installed and accessible in your PATH, run:
        ```bash
        make setup-all
        ```
        This will create virtual environments for all MCP server tools and install their dependencies. You can also just run `make`, which defaults to `setup-all`.


## Cursor IDE Integration (mcp.json)

To use these MCP servers you need access to Cursor IDE, and configure the `mcp.json` file. To get access to Cursor IDE please reach out to the IT Team. 

*...why not chatGPT ? openAI desktop app doesnt yet support [MCP servers](https://x.com/OpenAIDevs/status/1904957755829481737?lang=en).*

1. Open Cursor IDE.
2. Go to `Settings` > `Cursor settings`.
3. Click on `Add a global MCP`.
4. Paste the JSON configuration below, making the necessary updates for PagerDuty and Datadog credentials.

![image](https://github.com/user-attachments/assets/47cda3d4-b6ee-43d5-99a1-90f65df3699c)


**Important: Three changes need to be made in the JSON below:**

*   Replace `REPLACE_DIRECTORY/eagle-eye/...` paths with the correct **absolute path** to the `eagle-eye` directory on your system (e.g., `/Users/your_username/path/to/eagle-eye/...`).

*   Replace placeholder values for PAGERDUTY_API_KEY, DD_APP_KEY, DD_API_KEY keys/tokens with the read-only credentials

* Replace `PAGERDUTY_USER_TOKEN` with your own personal token. Since this token varies with permission, the MCP behavior will be different. You can find it in PagerDuty by clicking My Profile --> User Settings --> Create API User Token

<img width="806" alt="image" src="https://github.com/user-attachments/assets/7a45b9e8-b048-40f1-bf7f-86faf6461744" />

![image](https://github.com/user-attachments/assets/8a6315b2-e9a0-43c9-96d0-38a0fef619a2)

```json
{
  "mcpServers": {
    "k8s-readonly-mcp": {
      "command": "uv",
      "args": [
        "--directory",
        "REPLACE_DIRECTORY/eagle-eye/tools/k8s",
        "run",
        "main.py"
      ],
      "description": "Runs the Eagle Eye application using uv."
    },
    "pagerduty-readonly-mcp-server": {
      "command": "uv",
      "args": [
        "--directory",
        "REPLACE_DIRECTORY/eagle-eye/tools/pagerduty-mcp-server/src/pagerduty_mcp_server",
        "run",
        "-m",
        "pagerduty_mcp_server.main"
      ],
      "id": "pagerduty-mcp-server",
      "name": "pagerduty-mcp-server",
      "description": "pagerduty-mcp-server",
      "env": {
        "PAGERDUTY_API_KEY": "YOUR_PAGERDUTY_API_KEY_HERE",
        "PAGERDUTY_USER_TOKEN": "YOUR_PERSONAL USER TOKEN HERE"

      }
    },
    "prometheus-mcp-server": {
      "command": "uv",
      "args": [
        "--directory",
        "REPLACE_DIRECTORY/eagle-eye/tools/prometheus/prometheus-mcp-server/src/prometheus_mcp_server",
        "run",
        "main.py"
      ],
      "env": {
        "PROMETHEUS": "<REPLACE_WITH_PROM_URL>"
      }
    },
    "datadog-readonly-mcp-server": {
      "command": "uv",
      "args": [
        "--directory",
        "REPLACE_DIRECTORY/eagle-eye/tools/datadog-mcp-server/src/datadog_mcp_server",
        "run",
        "main.py"
      ],
      "description": "datadog-mcp-server",
      "env": {
        "DD_API_KEY": "YOUR_DATADOG_API_KEY_HERE",
        "DD_APP_KEY": "YOUR_DATADOG_APP_KEY_HERE"
      }
    }
  }
}
```




## Demo

To check why a Kubernetes pod is crashing, you can ask Cursor like below as shown in snapshot(for k8s MCP to work need VPN access and also switch to the corresponding cluster using kubectx.)


## Roadmap


More integrations and automations to come...

## Credits
* https://github.com/Flux159/mcp-server-kubernetes
* https://github.com/wpfleger96/pagerduty-mcp-server
* https://github.com/MaitreyaM/WEB-SCRAPING-MCP
