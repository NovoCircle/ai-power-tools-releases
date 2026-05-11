# ai-power-tools-releases

Public installer downloads for **AI Power Tools for Enterprise Architect** — the Sparx EA automation MCP server from NovoCircle.

## Downloads

- **Claude Desktop edition (`.mcpb`)** — latest:
  https://github.com/NovoCircle/ai-power-tools-releases/releases/latest/download/AI-Power-Tools-for-Enterprise-Architect.mcpb
- **VS Code edition (`.vsix`, sideload)** — latest:
  https://github.com/NovoCircle/ai-power-tools-releases/releases/latest/download/ai-power-tools-ea.vsix
  Or install from the VS Code Marketplace: https://marketplace.visualstudio.com/items?itemName=NovoCircle.ai-power-tools-ea

A license key is required. Purchase or manage your subscription at https://store.novocircle.com.

## Auto-updates

The Claude Desktop edition checks https://api.github.com/repos/NovoCircle/ai-power-tools-releases/releases/latest on a 24h cadence and surfaces a notice through `get_repository_info` when a newer release is available. The VS Code edition auto-updates via the Marketplace.

## Source

This repo hosts only the published binaries. Source code is private at NovoCircle/ai-power-tools.
