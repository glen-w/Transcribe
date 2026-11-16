#!/usr/bin/env bash
# Open the bundled sample notebook inside the production image (first-run path).
# The image installs the wheel as a non-root user, so this proves the fixture is
# packaged and that nothing is written into the install.
set -euo pipefail

IMAGE="${TRANSCRIBE_IMAGE:-transcribe:latest}"

if ! command -v docker >/dev/null 2>&1; then
  echo "SKIP: docker not available"
  exit 0
fi

if ! docker image inspect "$IMAGE" >/dev/null 2>&1; then
  echo "ERROR: image $IMAGE not found; build first"
  exit 1
fi

docker run --rm --network none --entrypoint python \
  -e TRANSCRIBE_DATA_DIR=/tmp/tr/data \
  -e TRANSCRIBE_PROJECTS_DIR=/tmp/tr/projects \
  -e TRANSCRIBE_INBOX_DIR=/tmp/tr/inbox \
  -e TRANSCRIBE_EXPORT_DIR=/tmp/tr/exports \
  -w /tmp "$IMAGE" -c '
from pathlib import Path
from transcribe.ports import SystemClock, UuidGenerator
from transcribe.runtime_paths import RuntimePaths
from transcribe.services.project import ProjectService, open_project_paths
from transcribe.services.sample_notebook import install_sample_notebook

base = Path("/tmp/tr")
for name in ("data/config", "projects", "inbox", "exports"):
    (base / name).mkdir(parents=True, exist_ok=True)
runtime = RuntimePaths(
    repo_root=base,
    data_dir=base / "data",
    projects_dir=base / "projects",
    inbox_dir=base / "inbox",
    export_dir=base / "exports",
)
root = install_sample_notebook(runtime)
projects = ProjectService(open_project_paths(root), clock=SystemClock(), ids=UuidGenerator())
pages = projects.load().pages
assert len(pages) == 3, len(pages)
assert all(projects.load_page_result(p.page_id).effective_text() for p in pages)
print("sample notebook pages:", len(pages))
'

echo "OK: image sample notebook check passed"
