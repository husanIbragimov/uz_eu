"""One-time, idempotent import of projects / stages / tasks from the legacy PMI system.

The platform has no runtime dependency on PMI. This command reads a PMI export (JSON file, or a one-off
HTTP fetch of the same document) and writes the data into the platform's own tables, keeping the
original PMI ids in `legacy_pmi_id`. Rows whose `legacy_pmi_id` already exists are skipped, so the
command can be re-run safely.

Expected JSON shape (unknown keys are ignored):

    {"projects": [{
        "id": "PMI-101", "name": "...", "category": "ongoing", "status": "in_progress",
        "cost": 120.5, "sector": "Energy", "countries": ["DE", "FR"],
        "region": "Samarkand region", "district": "Urgut", "program": "...", "initiator": "Ministry of Energy",
        "eu_partners": ["KfW Development Bank"], "uz_partners": ["Uzbekcement JSC"], "description": "...",
        "stages": [{"id": "PMI-S-1", "title": "Negotiations", "position": 1,
                    "tasks": [{"id": "PMI-T-1", "title": "...", "description": "...", "deadline": "2026-03-14",
                               "status": "completed", "completed_at": "2026-03-10T09:12:00Z"}]}]
    }]}
"""

import json
from datetime import date

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils.dateparse import parse_datetime

from apps.audit.services import AuditService
from apps.projects.choices import ProjectCategory, ProjectStatus, SubtaskStatus
from apps.projects.models import MainTask, Project, Subtask
from apps.projects.services.project_service import (
    MAIN_TASK_AUDIT_FIELDS,
    PROJECT_AUDIT_FIELDS,
    get_or_create_organizations,
)
from apps.projects.services.task_service import SUBTASK_AUDIT_FIELDS
from apps.reference.models import Country, Region, Sector

PMI_STATUS_MAP = {
    "new": SubtaskStatus.NOT_STARTED,
    "todo": SubtaskStatus.NOT_STARTED,
    "not_started": SubtaskStatus.NOT_STARTED,
    "in_progress": SubtaskStatus.IN_PROGRESS,
    "active": SubtaskStatus.IN_PROGRESS,
    "review": SubtaskStatus.UNDER_REVIEW,
    "under_review": SubtaskStatus.UNDER_REVIEW,
    "done": SubtaskStatus.COMPLETED,
    "completed": SubtaskStatus.COMPLETED,
}


class ImportReport:
    def __init__(self):
        self.counts = {
            "projects_imported": 0,
            "projects_skipped": 0,
            "main_tasks_imported": 0,
            "main_tasks_skipped": 0,
            "subtasks_imported": 0,
            "subtasks_skipped": 0,
        }
        self.errors: list[str] = []
        self.warnings: list[str] = []

    def as_dict(self) -> dict:
        return {**self.counts, "errors": self.errors, "warnings": self.warnings}


class Command(BaseCommand):
    help = "Import projects, stages (main tasks) and tasks (subtasks) from a PMI export. Safe to re-run."

    def add_arguments(self, parser):
        source = parser.add_mutually_exclusive_group(required=True)
        source.add_argument("--file", help="Path to the PMI JSON export (last cached data).")
        source.add_argument("--url", help="One-off fetch of the PMI export over HTTP (GET, JSON).")
        parser.add_argument("--token", help="Bearer token for --url.")
        parser.add_argument("--report", help="Write the JSON report to this path.")
        parser.add_argument("--dry-run", action="store_true", help="Validate and report without saving.")

    def handle(self, *args, **options):
        payload = self._load(options)
        report = ImportReport()

        for raw_project in payload.get("projects", []):
            pmi_id = str(raw_project.get("id") or "").strip()
            if not pmi_id:
                report.errors.append(f"Project without id skipped: {raw_project.get('name')!r}")
                continue
            try:
                with transaction.atomic():
                    self._import_project(raw_project, pmi_id, report)
                    if options["dry_run"]:
                        transaction.set_rollback(True)
            except Exception as exc:  # one broken project must not stop the whole import
                report.errors.append(f"Project {pmi_id}: {exc}")

        self._output(report, options)

    # --- loading --------------------------------------------------------------------------------

    def _load(self, options) -> dict:
        if options["file"]:
            try:
                with open(options["file"], encoding="utf-8") as fh:
                    return json.load(fh)
            except (OSError, ValueError) as exc:
                raise CommandError(f"Cannot read {options['file']}: {exc}") from exc

        import requests

        headers = {"Authorization": f"Bearer {options['token']}"} if options.get("token") else {}
        try:
            response = requests.get(options["url"], headers=headers, timeout=60)
            response.raise_for_status()
            return response.json()
        except (requests.RequestException, ValueError) as exc:
            raise CommandError(f"PMI is unavailable ({exc}); re-run with --file using the cached export.") from exc

    # --- mapping --------------------------------------------------------------------------------

    def _import_project(self, raw: dict, pmi_id: str, report: ImportReport) -> None:
        project = Project.all_objects.filter(legacy_pmi_id=pmi_id).first()
        if project is not None:
            report.counts["projects_skipped"] += 1
        else:
            project = self._create_project(raw, pmi_id, report)
            report.counts["projects_imported"] += 1

        for stage_index, raw_stage in enumerate(raw.get("stages", []), start=1):
            self._import_stage(project, raw_stage, stage_index, report)

    def _create_project(self, raw: dict, pmi_id: str, report: ImportReport) -> Project:
        category = raw.get("category") if raw.get("category") in ProjectCategory.values else ProjectCategory.ONGOING
        status = raw.get("status") if raw.get("status") in ProjectStatus.values else ProjectStatus.NOT_STARTED

        sector = None
        if raw.get("sector"):
            sector, _ = Sector.objects.get_or_create(name=raw["sector"].strip())

        district = None
        if raw.get("district"):
            district = (
                Region.objects.filter(
                    parent__name__iexact=(raw.get("region") or "").strip(), name__iexact=raw["district"].strip()
                ).first()
                or Region.objects.districts().filter(name__iexact=raw["district"].strip()).first()
            )
            if district is None:
                report.warnings.append(f"Project {pmi_id}: district {raw['district']!r} not found in reference")

        project = Project.objects.create(
            legacy_pmi_id=pmi_id,
            name=(raw.get("name") or pmi_id)[:500],
            category=category,
            status=status,
            cost=raw.get("cost") or "0.01",
            sector=sector,
            district=district,
            program=(raw.get("program") or "")[:255],
            description=raw.get("description") or "",
        )
        if raw.get("initiator"):
            project.initiator = get_or_create_organizations([raw["initiator"]], "uz")[0]
            project.save(update_fields=["initiator"])

        countries = list(Country.objects.filter(iso_code__in=[c.upper() for c in raw.get("countries", [])]))
        project.countries.set(countries)
        project.eu_partners.set(get_or_create_organizations(raw.get("eu_partners", []), "eu"))
        project.uz_partners.set(get_or_create_organizations(raw.get("uz_partners", []), "uz"))

        AuditService.log_create(None, project, PROJECT_AUDIT_FIELDS, project_id=project.pk)
        if not raw.get("cost"):
            report.warnings.append(f"Project {pmi_id}: missing cost, set to 0.01 - please correct")
        return project

    def _import_stage(self, project: Project, raw: dict, index: int, report: ImportReport) -> None:
        stage_id = str(raw.get("id") or "").strip()
        if not stage_id:
            report.errors.append(f"Project {project.legacy_pmi_id}: stage without id skipped")
            return
        main_task = MainTask.all_objects.filter(legacy_pmi_id=stage_id).first()
        if main_task is not None:
            report.counts["main_tasks_skipped"] += 1
        else:
            main_task = MainTask.objects.create(
                project=project,
                legacy_pmi_id=stage_id,
                title=(raw.get("title") or stage_id)[:255],
                position=raw.get("position") or index,
            )
            AuditService.log_create(None, main_task, MAIN_TASK_AUDIT_FIELDS, project_id=project.pk)
            report.counts["main_tasks_imported"] += 1

        for task_index, raw_task in enumerate(raw.get("tasks", []), start=1):
            self._import_task(project, main_task, raw_task, task_index, report)

    def _import_task(self, project: Project, main_task: MainTask, raw: dict, index: int, report) -> None:
        task_id = str(raw.get("id") or "").strip()
        if not task_id:
            report.errors.append(f"Stage {main_task.legacy_pmi_id}: task without id skipped")
            return
        if Subtask.all_objects.filter(legacy_pmi_id=task_id).exists():
            report.counts["subtasks_skipped"] += 1
            return
        try:
            deadline = date.fromisoformat(raw["deadline"])
        except (KeyError, TypeError, ValueError):
            report.errors.append(f"Task {task_id}: missing or invalid deadline {raw.get('deadline')!r}")
            return

        status = PMI_STATUS_MAP.get(str(raw.get("status", "")).lower(), SubtaskStatus.NOT_STARTED)
        completed_at = parse_datetime(raw["completed_at"]) if raw.get("completed_at") else None
        subtask = Subtask.objects.create(
            main_task=main_task,
            legacy_pmi_id=task_id,
            title=(raw.get("title") or task_id)[:255],
            description=raw.get("description") or "",
            deadline=deadline,
            status=status,
            completed_at=completed_at if status == SubtaskStatus.COMPLETED else None,
            position=raw.get("position") or index,
        )
        AuditService.log_create(None, subtask, SUBTASK_AUDIT_FIELDS, project_id=project.pk)
        report.counts["subtasks_imported"] += 1

    # --- report ---------------------------------------------------------------------------------

    def _output(self, report: ImportReport, options) -> None:
        prefix = "[DRY RUN] " if options["dry_run"] else ""
        for key, value in report.counts.items():
            self.stdout.write(f"{prefix}{key}: {value}")
        for warning in report.warnings:
            self.stdout.write(self.style.WARNING(f"warning: {warning}"))
        for error in report.errors:
            self.stdout.write(self.style.ERROR(f"error: {error}"))
        if options.get("report"):
            with open(options["report"], "w", encoding="utf-8") as fh:
                json.dump(report.as_dict(), fh, indent=2, ensure_ascii=False)
        style = self.style.WARNING if report.errors else self.style.SUCCESS
        self.stdout.write(style(f"{prefix}PMI import finished with {len(report.errors)} error(s)."))
