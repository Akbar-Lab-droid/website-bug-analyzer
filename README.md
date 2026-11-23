# Website Bug Analyzer

Analyze any website for bugs — broken links, missing SEO, missing security
headers — and get a heuristic guess whether the site was built with an AI
website builder or by a human.

Free CLI + web version. No sign-up, no token, nothing is stored.

- **CLI:** `python3 analyzer.py https://example.com`
- **Web:** https://akbar-lab-droid.github.io/website-bug-analyzer/

## What it checks

| Area | Checks |
| --- | --- |
| Availability | HTTP status, redirect count, response time, HTTPS vs HTTP |
| Security | Missing `Strict-Transport-Security`, `Content-Security-Policy`, `X-Frame-Options`, `X-Content-Type-Options`, `Referrer-Policy`; mixed content (http:// resources on an https page) |
| SEO basics | Title present and reasonably sized, meta description, canonical link, `lang` attribute, viewport meta, `<h1>` count and heading order |
| Links | Every link on the page (first 30 in the CLI, first 15 on the web) — 4xx/5xx/timeout is a high-severity finding |
| Images | Missing alt text, broken `src`, missing width/height |
| Performance | Linked CSS/JS files over 200 KB that are not minified |
| AI or human | Meta generator (Durable, Gamma, Mixo, …), builder footers ("Made with …"), generic AI-style copy, stock-photo domains |

Each finding costs health points: high −12, medium −6, low −3. The health
score starts at 100.

- **Good** (85–100) — exit code 0
- **Fair** (60–84) — exit code 1
- **Poor** (below 60) — exit code 2

## CLI usage

Python 3.8+ with the standard library only — no dependencies to install.

```bash
python3 analyzer.py https://example.com
python3 analyzer.py example.com --json
```

Example output:

```
website-bug-analyzer 1.0.0
URL: https://example.com
Final URL: https://example.com
HTTP 200  |  HTTPS  |  687 ms  |  0 redirect(s)

Health score: 55/100 — Poor

AI vs human (heuristic estimate, not proof):
  Likely human-built
  - No AI-builder signals found.

Findings: 8 (0 high, 7 medium, 1 low)
  [MEDIUM] Security: Missing security header: Strict-Transport-Security
  [MEDIUM] Security: Missing security header: Content-Security-Policy
  [MEDIUM] Security: Missing security header: X-Frame-Options
  [MEDIUM] Security: Missing security header: X-Content-Type-Options
  [MEDIUM] Security: Missing security header: Referrer-Policy
  [MEDIUM] SEO: Missing meta description
  [MEDIUM] SEO: No <h1> heading on the page
  [LOW] SEO: No canonical link tag
```

## Web version

Open the link above, paste a URL, hit Analyze. The page is fetched through
the public [allorigins.win](https://allorigins.win) CORS proxy, which is
why it works from a static page with no backend. Link checks are capped at
15 and image checks at 10 so results stay fast.

Two things the web version cannot do: read security headers (the proxy does
not expose them) and follow redirects. Use the CLI for the full audit.

## Running the tests

```bash
python3 -m unittest discover -s tests -v
```

The tests serve a deliberately broken fixture page (`tests/fixture-buggy.html`)
from a local HTTP server and assert the analyzer finds every planted bug:
missing title, description, lang, viewport and `<h1>`, a broken link, a
broken image, an image without alt text, a large unminified stylesheet, and
the AI-builder signals that should produce a "Likely AI-built" verdict.

## Limitations — read this before trusting a result

- **The AI-vs-human verdict is a heuristic guess, not proof.** A human can
  use an AI builder, and an AI-written page can be edited by a human until
  no signal is left. Treat the verdict as a starting point, not evidence.
- **The web version depends on a public CORS proxy.** If the proxy is down
  or the target site blocks it, analysis fails even though the site itself
  is fine.
- **Only the page you paste is audited**, not the whole site. A clean
  homepage says nothing about the checkout page.
- **Only the checks listed above run.** This tool does not test JavaScript
  behavior, accessibility beyond alt text, or anything behind a login.
- Always verify important findings by hand before acting on them.

## License

MIT — see [LICENSE](LICENSE).
