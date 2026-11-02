# Security Policy

Transcribe is a **local-first, single-user** handwritten notebook OCR workbench. The trust domain is the machine user who runs the process, plus the default loopback web bind.

## Reporting a vulnerability

Prefer private disclosure. Use GitHub **privately reported vulnerabilities** ([Report a vulnerability](https://github.com/glen-w/Transcribe/security/advisories/new)) when the repository has that feature enabled. Do **not** open a public Issue for sensitive vulnerability details. Public Issues are appropriate only for **non-sensitive** security questions (for example clarifying local trust-domain assumptions).

## Trust model (summary)

- Default Docker Compose publishes the web UI on **`127.0.0.1:8510` only** (`TRANSCRIBE_BIND_HOST`).
- The process inside the container still listens so the published host port can reach it.
- Setting `TRANSCRIBE_BIND_HOST=0.0.0.0` exposes the UI on the LAN **without authentication**.
- Since 1.2, the native `transcribe-ui` entry refuses a non-loopback `TRANSCRIBE_HOST` bind unless `TRANSCRIBE_ALLOW_LAN=1` acknowledges that exposure (`transcribe.net_guard`). Inside the container the bind is `0.0.0.0` by design; the Compose host publish above is what decides real exposure.
- LAN exposure grants unauthenticated access to **page images**, **OCR/analysis text**, **configuration-visible operations**, and **destructive** backup/restore or delete actions available in the UI.

## Related surfaces

- Local vs remote Ollama (page images leave the machine on a remote host): [docs/known_limitations.md](docs/known_limitations.md) · [docs/runtime/ocr.md](docs/runtime/ocr.md)
- Workspace backup ZIPs contain page images and text — treat as sensitive local files: [docs/backup_and_restore.md](docs/backup_and_restore.md)
- Docker bind and mounts: [docs/runtime/docker.md](docs/runtime/docker.md)
