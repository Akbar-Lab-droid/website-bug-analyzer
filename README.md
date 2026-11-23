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

Open the link above, paste a URL — a bare domain like `example.com` works,
the `https://` is added for you — and hit Analyze. The page is fetched
through a first-party proxy
([website-bug-proxy](https://github.com/Akbar-Lab-Droid/website-bug-proxy),
Vercel serverless) first, then public CORS proxies (allorigins, codetabs,
cors.lol, corsproxy.io) as fallbacks, which is why it works from a static
page with no backend. Link checks are capped at 15 and image checks at 10 so results
stay fast. If every proxy is down, the "paste HTML" option analyses page
source you paste yourself, entirely in your browser — and a link the proxy
could not reach is reported as "could not verify", never as broken.

Two things the web version cannot do: read security headers (the proxy does
not expose them) and follow redirects. Use the CLI for the full audit.

## Protecting your code

`scripts/protect.py` builds a protected copy of a Python program so it
is harder to copy and rewrite casually:

```sh
python3 scripts/protect.py analyzer.py
python3 dist/analyzer.pyc https://example.com
```

It compiles the program to optimised bytecode (`.pyc`) with docstrings
stripped. The copy runs exactly like the original, but there is no
readable source left to copy: no comments, no docstrings, no plain-text
code. A built-in smoke test runs the protected copy against
`https://example.com` and compares its output with the original before
reporting success. The `.pyc` file is a build artifact (ignored by
`.gitignore`) — the readable source stays in the repository.

Be honest about what this stops: bytecode can be decompiled with
public tools, so this blocks casual recoding, not a determined person.
Real protection needs a compiled binary (PyInstaller, Nuitka, Cython),
a private repository, or a licence other than MIT (which allows reuse).
The tool also never hides code in an encoded blob — encoded payloads
look exactly like malware to every scanner, including repo-safety-check.

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
