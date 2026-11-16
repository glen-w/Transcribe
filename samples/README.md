# Sample notebook

The shipped fixture lives in the package so wheel, Docker, and editable installs
all see it: [`src/transcribe/samples/demo-notebook/`](../src/transcribe/samples/demo-notebook/).

**Workflow → New notebook → Open sample** (or Home → **Open sample notebook**)
creates the notebook in `TRANSCRIBE_PROJECTS_DIR` through the normal create +
import path and seeds page text so Analyse Quick works without OCR. Placeholder
pages are generated in memory; nothing is written into the install.
