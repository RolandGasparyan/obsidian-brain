# Audit & Deploy Log

## 2026-07-25 — RO-SUPREME-RUN

- Restored the existing `empire-world` image in a reversible container with localhost `3010:3000` binding.
- Corrected Nginx `/world` proxy path handling; public route now returns `200`.
- Corrected Nginx `/api/empire/` prefix stripping to the sync service root; public route now returns `200` JSON.
- Moved Nginx backup files outside `sites-enabled` and reloaded successfully; config syntax is valid.
- Booking health remained `200 OK`; no secrets or trading gates were modified.
