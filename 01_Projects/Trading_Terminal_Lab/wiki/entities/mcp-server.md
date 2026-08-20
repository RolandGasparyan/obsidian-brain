---
title: MCP Server
created: 2026-08-20
updated: 2026-08-20
type: entity
tags: [mcp, mcp-protocol, stdio, api, ai-agent]
sources: [Trading_Terminal_Lab_Codebase.md]
confidence: high
---

# MCP Server

The MCP (Model Context Protocol) server for [[trading-terminal-lab]]. Exposes 6 trading tools to AI agents via stdio transport.

## Overview

`src/mcp_server.py` implements a stdio-based MCP server that wraps [[trading-engine]] and makes it accessible to any MCP-compatible AI agent (Hermes, Claude, etc.).

## Tools

| Tool | Parameters | Returns |
|------|-----------|---------|
| `get_market_data` | `symbol?` | Price, bid, ask, volume, change_24h |
| `place_order` | `symbol, side, qty, order_type?, price?, stop_price?` | Order confirmation |
| `cancel_order` | `order_id` | Success/failure |
| `get_portfolio` | — | Cash, positions, total value, P&L |
| `get_orders` | `status?` | Order list |
| `get_trades` | — | Executed trade list |

## Transport

Uses stdio transport — the AI agent spawns the MCP server as a subprocess and communicates via JSON-RPCL over stdin/stdout. No network port needed.

## Related

- [[trading-engine]] — the engine this server wraps
- [[mcp-protocol]] — protocol overview
- [[hermes-agent]] — primary consumer
- [[order-management]] — order tools
