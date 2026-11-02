"""Workspace-wide doctor sweep: corpus doctor + a doctor pass per notebook."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from transcribe.corpus.paths import CorpusPaths
from transcribe.ports import SystemClock, UuidGenerator
from transcribe.runtime_paths import RuntimePaths
from transcribe.services.archive import discover_corpus_project_roots
from transcribe.services.corpus_doctor import CorpusDoctorService
from transcribe.services.doctor import DoctorReport, DoctorService
from transcribe.services.format_census import FormatFinding, run_format_census
from transcribe.services.project import ProjectService, open_project_paths


@dataclass
class WorkspaceDoctorResult:
    corpus_ok: bool
    corpus_findings: list = field(default_factory=list)
    notebook_reports: dict[str, DoctorReport] = field(default_factory=dict)
    failures: dict[str, str] = field(default_factory=dict)
    census_findings: list[FormatFinding] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        census_errors = any(item.severity == "error" for item in self.census_findings)
        return (
            self.corpus_ok
            and not self.failures
            and not census_errors
            and all(report.ok for report in self.notebook_reports.values())
        )

    @property
    def notebook_count(self) -> int:
        return len(self.notebook_reports) + len(self.failures)


def run_workspace_doctor(
    runtime: RuntimePaths, *, deep: bool = False
) -> WorkspaceDoctorResult:
    """Run corpus-doctor plus DoctorService over every discovered notebook."""
    corpus = CorpusDoctorService(CorpusPaths.from_runtime(runtime)).run(
        deep=deep, per_notebook=False
    )
    reports: dict[str, DoctorReport] = {}
    failures: dict[str, str] = {}
    for root in discover_corpus_project_roots(runtime):
        try:
            paths = open_project_paths(Path(root))
            projects = ProjectService(paths, clock=SystemClock(), ids=UuidGenerator())
            reports[str(root)] = DoctorService(paths, projects).run(deep=deep)
        except Exception as exc:  # noqa: BLE001 - one bad notebook must not hide the rest
            failures[str(root)] = str(exc)[:300]
    census = run_format_census(runtime)
    return WorkspaceDoctorResult(
        corpus_ok=corpus.ok,
        corpus_findings=list(corpus.findings),
        notebook_reports=reports,
        failures=failures,
        census_findings=list(census.findings),
    )


__all__ = ["WorkspaceDoctorResult", "run_workspace_doctor"]
