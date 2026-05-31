# Security

Do not commit real notification keys, API tokens, cookies, browser exports, or local state files.

Use `.env.example` as a template and keep your private values in `.env`.
Use `examples/config.example.yaml` as a template and keep private monitor configs in `config.yaml`.

If a secret is accidentally committed or pasted publicly, rotate it immediately at the provider side.

## Supported Use

Signal Watcher is intended for public or user-authorized monitoring and personal reminders.

Please do not use this project to bypass captchas, evade platform protections, scrape private data, spam services, or automate paid checkout/payment flows.

## Reporting a Vulnerability

Open a GitHub security advisory or create a private issue with enough detail to reproduce the problem. Avoid posting real tokens, cookies, browser exports, or account identifiers.
