# Signal Watcher

[![CI](https://github.com/HANG939/signal-watcher/actions/workflows/ci.yml/badge.svg)](https://github.com/HANG939/signal-watcher/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

Signal Watcher is a self-hosted monitoring toolkit for public web signals and personal notification workflows.

It is designed for low-cost VPS deployments where you want to monitor public changes and receive timely alerts through WeChat, Telegram, WeCom, generic webhooks, or stdout.

## What It Can Monitor

- Public X/Twitter RSS feeds for new posts.
- Damai public project status signals for ticket availability changes.
- Generic webpage keyword changes, such as stock pages that stop showing `Unavailable`.

The project is a reminder system. It does not provide captcha bypassing, private-data scraping, platform rate-limit evasion, automatic checkout, or automatic payment.

## Quick Start

Requires Python 3.9+.

```bash
git clone https://github.com/HANG939/signal-watcher.git
cd signal-watcher
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r requirements.txt
cp .env.example .env
cp examples/config.example.yaml config.yaml
```

Edit `config.yaml` and enable the monitors you want. Put private notification tokens in `.env`.

Run one check:

```bash
set -a
. ./.env
set +a
PYTHONPATH=src python -m signal_watcher --config config.yaml --once --dry-run
```

Run continuously:

```bash
set -a
. ./.env
set +a
PYTHONPATH=src python -m signal_watcher --config config.yaml --watch
```

## Configuration Example

```yaml
state_file: .state/signal-watcher.json

notifiers:
  - type: serverchan
    sendkey: ${SERVERCHAN_SENDKEY}

monitors:
  - name: alpha-cat-x
    type: x_rss
    enabled: true
    username: Alpha_Cat
    interval_seconds: 30

  - name: dmit-stock
    type: web_keyword
    enabled: true
    url: https://www.dmit.io/cart.php
    title: "DMIT stock signal"
    message: "The monitored product may be available. Open the page and check manually."
    interval_seconds: 30
    notify_on: match
    absent_all:
      - Unavailable
```

See [examples/config.example.yaml](examples/config.example.yaml) for X/Twitter, Damai, and generic stock examples.

## Docker

```bash
cp .env.example .env
cp examples/config.example.yaml config.yaml
# Edit .env and config.yaml first.
docker compose up -d --build
```

Logs:

```bash
docker compose logs -f
```

State is stored in `.state/` and ignored by git.

## Legacy Scripts

The original single-purpose scripts are still available:

```bash
python3 src/x_watch.py
python3 src/damai_watch.py
```

Cron helpers are also kept:

```bash
bash scripts/install_x_cron.sh
bash scripts/install_damai_cron.sh
```

For new installs, prefer the config-based `signal_watcher` CLI.

## Notification Providers

Supported notifier types:

- `print`
- `serverchan`
- `telegram`
- `wecom`
- `webhook`

Secrets should be stored in `.env` and referenced from `config.yaml` with `${NAME}`.

## Development

```bash
python -m pip install -r requirements-dev.txt
bash scripts/check.sh
```

The check script runs unit tests, compiles Python files, validates shell scripts, and scans for common secret patterns.

## Safety Rules

Never commit:

- `.env`
- `config.yaml` with private tokens
- ServerChan keys, X bearer tokens, webhook URLs, cookies, or browser exports
- `.state/`
- local logs or debug JSON files

If a secret leaks, rotate it immediately at the provider side.

## Project Boundaries

Signal Watcher only monitors public or user-authorized signals and sends reminders. It should not be used for spam, bypassing access controls, evading platform protections, or automating paid checkout/payment flows.

## Roadmap

See [ROADMAP.md](ROADMAP.md).

## License

MIT
