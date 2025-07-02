SHELL := /bin/bash
BASE_DIR := $(shell pwd)

# NOTE: prometheus-dev and prometheus-prod have been merged into a single prometheus server under tools/prometheus/prometheus-mcp-server

# MCP Server directories - adjust if needed
MCP_SERVERS = datadog-mcp-server pagerduty-mcp-server prometheus k8s

.PHONY: install-uv setup-all $(MCP_SERVERS)

# Default goal
all: setup-all

install-uv:
	@echo "Installing uv..."
	curl -LsSf https://astral.sh/uv/install.sh | sh
	@echo "uv installation complete. Please ensure ~/.cargo/bin is in your PATH."
	@echo "You might need to source your shell profile (e.g., source ~/.zshrc or source ~/.bashrc)"

setup-all: $(addprefix setup-,$(MCP_SERVERS))

# Specific rule for prometheus
setup-prometheus:
	@echo "Setting up $(BASE_DIR)/tools/prometheus/prometheus-mcp-server..."
	@cd "$(BASE_DIR)/tools/prometheus/prometheus-mcp-server" && uv venv && uv sync
	@echo "Setup complete for $(BASE_DIR)/tools/prometheus/prometheus-mcp-server."

# Generic setup rule for other servers (k8s, datadog-mcp-server, pagerduty-mcp-server)
# This rule is used if a more specific one (like setup-prometheus) isn't found.
setup-%:
	@echo "Setting up $(BASE_DIR)/tools/$*..."
	@cd "$(BASE_DIR)/tools/$*" && uv venv && uv sync
	@echo "Setup complete for $(BASE_DIR)/tools/$*."

clean:
	@echo "Cleaning up virtual environments..."
	@for server in $(MCP_SERVERS); do \
		target_subdir=""; \
		if [ "$$server" = "prometheus" ]; then \
			target_subdir="/prometheus-mcp-server"; \
		fi; \
		cleanup_path="$(BASE_DIR)/tools/$$server$$target_subdir/.venv"; \
		echo "Cleaning $$cleanup_path..."; \
		rm -rf "$$cleanup_path"; \
	done
	@echo "Cleanup complete."

help:
	@echo "Available targets:"
	@echo "  all                : Sets up all MCP servers (default)."
	@echo "  install-uv         : Installs the uv tool."
	@echo "  setup-all          : Sets up virtual environments for all MCP servers."
	@echo "  setup-<server_name>: Sets up the virtual environment for a specific server."
	@echo "                       (e.g., make setup-datadog-mcp-server)"
	@echo "  clean              : Removes all created virtual environments."
	@echo "  help               : Shows this help message." 