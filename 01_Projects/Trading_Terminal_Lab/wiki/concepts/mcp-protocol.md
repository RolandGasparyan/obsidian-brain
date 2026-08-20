---
title: MCP Protocol
created: 2026-08-20
updated: 2026-08-20
type: concept
tags: [mcp-protocol, stdio, api, architecture]
sources: [Trading_Terminal_Lab_Codebase.md]
confidence: high
---

# MCP Protocol

Model Context Protocol — a stdio-based protocol for exposing tools to AI agents.

## Overview

MCP allows an AI agent (like [[hermes-agent]]) to call tools exposed by a server process. The server runs as a subprocess, communicating via JSON-RPC over stdin/stdout. No network port is needed.

## In Trading Terminal Lab

[[mcp-server]] implements 6 tools:
- `get_market_data`, `place_order`, `cancel_order`, `get_portfolio`, `get_orders`, `get_trades`

These tools let any MCP-compatible agent query [[trading-engine]] and place trades programmatically.

## Advantages

- **Zero network overhead** — no HTTP server needed for MCP
- **Agent-native** — designed for AI agent consumption
- **Composable** — multiple MCP servers can coexist

## Related

- [[mcp-server]] — implementation
- [[trading-engine]] — engine being exposed
- [[hermes-agent]] — primary consumer
