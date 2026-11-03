# Transcribe website

Modest public landing (plain HTML/CSS, minimal JS for mobile nav). Product front door: hero → what the app does → outcomes → privacy → first path → install.

- Open `index.html` locally, or deploy via GitHub Pages (`.github/workflows/pages.yml`).
- Landing stills live in [images/](images/) and are copied from `docs/images/` by `make docs-media` (synthetic sample notebook; never real pages).
- Footer version should match [pyproject.toml](../pyproject.toml) `version` (currently **1.4.0**). `tests/unit/test_sphinx_docs.py` fails if they diverge.
- Install snippet matches README: Docker first (`HOST_PROJECTS_DIR` + `docker compose up --build transcribe-web`); open `http://127.0.0.1:8510/`; native `./transcribe.sh setup` / `ui` is advanced.
- First-path copy matches README / Sphinx Start here: Open sample **or** New notebook → Transcribe → Review → Analyse.
- Docs CTAs point at the **Sphinx HTML guide** published beside this landing (`./guide/`), rebuilt from `docs/` on every qualifying `main` push.
- The sticky header nav is shared with `/guide/` via `website/chrome/` (Sphinx injects the same chrome).
- Full local preview (landing + guide): `pip install -e '.[docs]' && make pages-site` then open `_site/index.html`.
- Ko-fi support link in footer: https://ko-fi.com/C0C1XK8G
