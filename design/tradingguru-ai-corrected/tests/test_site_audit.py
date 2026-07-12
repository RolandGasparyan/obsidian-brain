"""Static-site audit for design/tradingguru-ai-corrected/full-site/.

These tests fail if the corrected site regresses into demo-data territory or
loses its wiring to the real Gate.io + battle telemetry endpoints. They run
without a browser — just HTML + JS string inspection — so they're safe in CI.

Run via pytest:
    pytest design/tradingguru-ai-corrected/tests/

Or standalone:
    python3 design/tradingguru-ai-corrected/tests/test_site_audit.py
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SITE = HERE.parent / "full-site"
PAGES = ("index.html", "arena.html", "agents.html",
         "leaderboard.html", "governance.html", "about.html", "404.html")

# Strings that, if they appear OUTSIDE a transparency disclosure, are a
# regression to the old fabricated build. A line containing one of these
# strings is acceptable iff the same line also contains a "transparency
# marker" (NO / no / NOTICE / refuses / removed / disclosure / reject).
DEMO_TOKENS = (
    "$1,000,000",
    "WINNER TAKES ALL",
    "WINS THE POT",
    "WHALE HUNTER",
    "WR 73%",
)

TRANSPARENCY_MARKERS = (
    "no ", "NO ", "Notice", "NOTICE",
    "refuses", "removed", "reject", "disclosure",
    "removed in this corrected build",
    "without",
)

# Hard-fail strings — must NEVER appear anywhere, even in disclosures.
HARD_BANNED = (
    'data-mock="true"',
    'class="fake"',
    "lorem ipsum",
    "Lorem ipsum",
    # Specific fake stat strings the old build shipped
    'value">73%<',
    'value">$1,000,000<',
)


def _read(name: str) -> str:
    return (SITE / name).read_text(encoding="utf-8")


def _line_has_transparency_marker(line: str) -> bool:
    return any(m in line for m in TRANSPARENCY_MARKERS)


_DISCLOSURE_RE = re.compile(
    r'<div\s+class="disclosure"[^>]*>(.*?)</div>',
    re.DOTALL,
)


def _disclosure_blocks(text: str) -> str:
    """Concatenated text of every disclosure block on the page."""
    return "\n".join(m.group(1) for m in _DISCLOSURE_RE.finditer(text))


# ── tests ─────────────────────────────────────────────────────────────────


def test_site_directory_exists():
    assert SITE.is_dir(), f"missing site dir: {SITE}"
    for p in PAGES:
        assert (SITE / p).is_file(), f"missing page: {p}"
    assert (SITE / "css" / "site.css").is_file(), "missing css/site.css"
    assert (SITE / "js" / "app.js").is_file(), "missing js/app.js"


def test_no_demo_tokens_outside_disclosures():
    """Demo-data strings allowed only inside <div class="disclosure"> blocks."""
    bad = []
    for p in PAGES:
        text = _read(p)
        disclosed = _disclosure_blocks(text)
        # Strip every disclosure block from the page; anything left should be
        # demo-token-free.
        stripped = _DISCLOSURE_RE.sub("", text)
        for tok in DEMO_TOKENS:
            if tok in stripped:
                # find the offending line for the error message
                for lineno, line in enumerate(stripped.splitlines(), 1):
                    if tok in line:
                        bad.append(f"{p}  outside-disclosure  {tok!r}  →  {line.strip()[:120]}")
                        break
        # Sanity: confirm the disclosure block is the one declaring the token
        for tok in DEMO_TOKENS:
            if tok in text and tok not in stripped and tok not in disclosed:
                bad.append(f"{p}  found {tok!r} outside both stripped page and disclosures (parser bug)")
    assert not bad, "demo tokens found outside transparency disclosures:\n" + "\n".join(bad)


def test_hard_banned_strings_never_appear():
    bad = []
    for p in PAGES:
        text = _read(p)
        for tok in HARD_BANNED:
            if tok in text:
                bad.append(f"{p}  contains hard-banned token  {tok!r}")
    assert not bad, "\n".join(bad)


def test_every_page_loads_shared_js_and_css():
    for p in PAGES:
        text = _read(p)
        assert 'href="css/site.css"' in text, f"{p} missing site.css link"
        assert 'src="js/app.js"' in text, f"{p} missing js/app.js script"


def test_pages_link_to_each_other():
    """Every non-404 page must reference all the other primary nav routes."""
    nav_targets = {"index.html", "arena.html", "agents.html",
                   "leaderboard.html", "governance.html", "about.html"}
    for p in nav_targets:
        text = _read(p)
        for target in nav_targets:
            assert target in text, f"{p} missing nav link to {target}"


def test_index_has_real_data_hooks():
    text = _read("index.html")
    assert 'data-battle="capital"' in text, "capital cell must be data-driven"
    assert 'data-battle="alive_accounts"' in text, "alive_accounts cell must be data-driven"
    for pair in ("BTC_USDT", "ETH_USDT", "XRP_USDT", "SOL_USDT"):
        assert f'data-ticker="{pair}"' in text, f"index.html missing live ticker for {pair}"
    assert "data-conn-status" in text, "index.html missing connection-status element"


def test_arena_has_replay_hooks():
    text = _read("arena.html")
    for target in ("cursor_label", "event_feed", "boss_moments", "heatmap", "cycle_stats"):
        assert f'data-replay="{target}"' in text, f"arena.html missing data-replay={target}"


def test_agents_has_per_slot_hooks():
    text = _read("agents.html")
    for slot in (1, 2, 3):
        for field in ("status", "capital", "pnl", "trades", "open_positions", "daily_dd"):
            assert f'data-slot="{slot}" data-field="{field}"' in text, \
                f"agents.html missing data-slot={slot} data-field={field}"
    # No demo roster names
    assert "Whale Hunter" not in text
    assert "WR 73%" not in text or _line_has_transparency_marker(
        next(line for line in text.splitlines() if "WR 73%" in line)
    )


def test_leaderboard_has_lb_row_hooks():
    text = _read("leaderboard.html")
    # 3 accounts → 3 rows. We refuse to ship 8 empty rows that promise a roster
    # the L1 layer cannot actually populate.
    for n in (1, 2, 3):
        assert f'data-lb-row="{n}"' in text, f"leaderboard.html missing data-lb-row={n}"
    # Hardened columns: STATUS + ROUND PNL + SESSION PNL + TRADES TODAY + CAPITAL
    for col in ("STATUS", "ROUND PNL", "SESSION PNL", "TRADES TODAY", "CAPITAL"):
        assert col in text, f"leaderboard.html missing column {col}"


def test_leaderboard_has_championship_hooks():
    """The 60-min championship banner must wire to the publisher's
    championship block in /api/battle/terminal.json."""
    text = _read("leaderboard.html")
    for attr in (
        'data-championship="banner"',
        'data-championship="current_round_id"',
        'data-championship="current_round_leader"',
        'data-championship="overall_leader"',
        'data-championship="round_elapsed"',
        'data-championship="round_interval"',
        'data-championship="round_progress_bar"',
        'data-championship="completed_rounds_table"',
        'data-championship="completed_rounds_body"',
    ):
        assert attr in text, f"leaderboard.html missing {attr}"
    # round_pnl column on each row
    for n in (1, 2, 3):
        assert f'data-lb-row="{n}"' in text
    assert 'data-field="round_pnl"' in text, "leaderboard.html missing round_pnl field"


def test_js_renders_championship_from_publisher_block():
    """app.js must read champ data from `d.championship.*` (the shape written
    by canary_executor.publish_status), not from invented fields."""
    js = (SITE / "js" / "app.js").read_text(encoding="utf-8")
    for key in (
        "d.championship",
        "champ.current_round_id",
        "champ.current_round_leader",
        "champ.overall_leader",
        "champ.rounds",
        "champ.round_interval_sec",
        "round_pnl_usd",
        "winner_account_id",
    ):
        assert key in js, f"app.js missing reference to publisher field: {key}"


def test_js_only_fetches_allowed_endpoints():
    """app.js must only call the documented endpoints — no surprise hosts."""
    js = (SITE / "js" / "app.js").read_text(encoding="utf-8")
    allowed_urls = {
        "/api/battle/terminal.json",
        "/api/battle/live_battle.json",
        "/api/battle/replay-index.json",
        "/api/battle/replay-timeline.json",
        "/api/battle/replay-events-recent.json",
        "/api/battle/replay-bosses.json",
        "/api/battle/replay-heatmap.json",
        "https://api.gateio.ws/api/v4/spot/tickers",
    }
    # Any string literal looking like a URL (rough heuristic)
    found_urls = set(re.findall(r'"(https?://[^"]+|/api/[^"]+)"', js))
    extras = found_urls - allowed_urls
    assert not extras, f"app.js calls unexpected endpoints: {sorted(extras)}"


def test_js_has_no_hardcoded_pnl_or_winrate():
    js = (SITE / "js" / "app.js").read_text(encoding="utf-8")
    # Hard fail if anyone slipped a literal number into a fmtPct/fmtUSD call
    for banned in ("$1,000,000", "WINNER TAKES ALL", "Whale Hunter",
                   'win_rate":', '"73%"', '"100%"'):
        assert banned not in js, f"app.js contains banned literal {banned!r}"


def test_js_returns_dash_for_missing_values():
    """fmtUSD/fmtPct/fmtInt/fmtPrice/fmtTime must all return — when input is None/NaN."""
    js = (SITE / "js" / "app.js").read_text(encoding="utf-8")
    # Each formatter has an early-return DASH guard
    for fn in ("fmtUSD", "fmtPct", "fmtPrice", "fmtInt", "fmtTime", "fmtSignedUSD"):
        # match `function fmtX(...)` then `return DASH` before any other return
        pattern = re.compile(
            rf"function\s+{re.escape(fn)}\([^)]*\)\s*\{{[^}}]*?return\s+DASH",
            re.DOTALL,
        )
        assert pattern.search(js), f"{fn} missing DASH-guard in app.js"


def test_index_disclosure_block_present():
    """The transparency notice that explains the paper-mode posture must
    stay on the landing page — removing it has been the source of past drift."""
    text = _read("index.html")
    assert "PAPER MODE" in text
    assert 'class="disclosure"' in text
    # The notice paragraph itself
    lower = text.lower()
    assert "$1,000,000 prize" in lower
    assert "winner-takes-all pot" in lower
    assert "not financial advice" in lower


# ── standalone runner ─────────────────────────────────────────────────────


def _main() -> int:
    tests = [
        test_site_directory_exists,
        test_no_demo_tokens_outside_disclosures,
        test_hard_banned_strings_never_appear,
        test_every_page_loads_shared_js_and_css,
        test_pages_link_to_each_other,
        test_index_has_real_data_hooks,
        test_arena_has_replay_hooks,
        test_agents_has_per_slot_hooks,
        test_leaderboard_has_lb_row_hooks,
        test_leaderboard_has_championship_hooks,
        test_js_renders_championship_from_publisher_block,
        test_js_only_fetches_allowed_endpoints,
        test_js_has_no_hardcoded_pnl_or_winrate,
        test_js_returns_dash_for_missing_values,
        test_index_disclosure_block_present,
    ]
    passed = failed = 0
    for t in tests:
        try:
            t()
            print(f"  PASS  {t.__name__}")
            passed += 1
        except AssertionError as e:
            print(f"  FAIL  {t.__name__}  —  {e}")
            failed += 1
        except Exception as e:  # noqa: BLE001
            print(f"  ERR   {t.__name__}  —  {type(e).__name__}: {e}")
            failed += 1
    print(f"\nRESULT: {passed}/{passed + failed} passed · {failed} failed")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(_main())
