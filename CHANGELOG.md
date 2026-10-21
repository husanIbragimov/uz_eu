# Changelog

## Uzbekistan–EU Global Gateway Investment Platform — feature upgrade

All endpoints are under `/api/v1/`; interactive docs at `/api/docs/`.

### Roles (RBAC)

| Role | `User.role` | Rights |
|---|---|---|
| `admin` | 0 | Everything: manages users, members, reference data (Django admin); deletes projects; global audit log. |
| `viewer` | 1 | Read-only public data. Never sees contacts, comments, members, category history or audit log. |
| `uz_representative` | 2 | Creates projects; edits projects they are assigned to. Comment badge 🇺🇿 Uzbek side. |
| `eu_representative` | 3 | Same as above for the European side. Comment badge 🇪🇺 European side. |

Edit rights on a project = admin or a row in `ProjectMember` (the creator is added automatically; admins
assign others via `POST /projects/{id}/members/`). Role value `1` was the template's generic "user" and is now `viewer`.

### Task 1 — Categories and analytics
- `Project.category`: `ongoing` / `upcoming` / `potential` (default `ongoing`).
- `GET /projects/stats/` → `{total, by_category: {ongoing: {count, total_cost, total_cost_display}, upcoming: {...}, potential: {count}}}`.
- `PATCH /projects/{id}/category/` `{category}` — keeps tasks, comments and files; writes `CategoryHistory` + audit log.
- `GET /projects/{id}/category-history/`.

### Task 2 — Independent project management (PMI)
- The repository contained **no PMI integration** (no API client, sync job, env vars or foreign ids), so nothing had to be removed at runtime.
- `legacy_pmi_id` (nullable, unique) on `Project`, `MainTask`, `Subtask`.
- One-time import: `python manage.py import_pmi --file export.json [--dry-run] [--report report.json]`
  (or `--url ... --token ...` for a single fetch; wrapper `scripts/import_pmi.sh`). Idempotent — existing
  `legacy_pmi_id`s are skipped; prints imported / skipped / errors / warnings. Expected JSON format is documented
  at the top of `src/apps/projects/management/commands/import_pmi.py`.
- Native CRUD and personal dashboard: `GET /projects/my/`.

### Task 3 — Tasks, subtasks, comments, notifications
- New projects get the default main-task template (`reference.MainTaskTemplate`, editable in admin).
- Main tasks: `GET|POST /projects/{id}/main-tasks/`, `GET|PATCH|DELETE /main-tasks/{id}/`, `POST /projects/{id}/main-tasks/reorder/ {ids}`.
  Status is derived from subtasks (`pending` / `in_progress` / `completed`).
- Subtasks: `GET|POST /main-tasks/{id}/subtasks/`, `GET|PATCH|DELETE /subtasks/{id}/`, `POST /main-tasks/{id}/subtasks/reorder/`.
  Deadline required; workflow status `not_started|in_progress|under_review|completed`; computed `deadline_indicator`
  `green|yellow|red` (yellow threshold `DEADLINE_RISK_DAYS`, default 7).
- Attachments: `POST /subtasks/{id}/attachments/` (multipart `file`), `GET|DELETE /attachments/{id}/`.
  Allowed `ATTACHMENT_ALLOWED_EXTENSIONS`, max `ATTACHMENT_MAX_SIZE_MB` (default 25).
- Comments: `GET|POST /projects/{id}/comments/?main_task=` (multipart, repeated `files`), `GET|PATCH|DELETE /comments/{id}/`.
  Author may edit/delete within `COMMENT_EDIT_WINDOW_MINUTES` (default 15), admin always; previous text is kept in the audit log.
- Notifications (bell): `GET /notifications/?unread=true`, `GET /notifications/unread-count/`, `POST /notifications/{id}/read/`,
  `POST /notifications/read-all/`. Created for new comments, subtask status changes and approaching deadlines
  (Celery beat task `apps.projects.tasks.notify_approaching_deadlines` daily 06:00 UTC, run by the `celery-beat`
  compose service, or `python manage.py notify_deadlines` from cron).
- Global search: `GET /search/?q=`.

### Task 4 — Projects table
`GET /projects/?category=&search=&sector=&country=&initiator=&status=&region=&district=&sort=&order=&page=&page_size=`
— `sort` ∈ `project_id, name, sector, country, cost, partner, initiator, status, category, updated`; default 20 rows;
each row has `row_number`; invalid params return field-level 400 errors.

### Task 6 — Project Passport
- `GET /projects/{id}/` (read), `POST /projects/` (create), `PUT|PATCH /projects/{id}/` (edit). Saving General Information
  and the full `contacts` list happens in one transaction (`id` → update, no `id` → create, omitted → soft-deleted).
- Contacts also individually: `GET|POST /projects/{id}/contacts/`, `GET|PATCH|DELETE /projects/{id}/contacts/{cid}/`.
  Email validated, phone normalized to international format (`+998 90 123 45 67` → `+998901234567`).
- Contacts are omitted from responses for viewers and guests.

### Task 7 — English only
- `LANGUAGE_CODE = "en"`, `LANGUAGES = [("en", "English")]`, `LocaleMiddleware` removed.
- `/ru/...`, `/uz/...` (and `/en/...`) → 301 to the unprefixed URL (`apps.common.middleware`).
- `python manage.py report_missing_english [--output file.csv]` lists records with an empty English value in
  `*_en` columns or JSON translation dicts (nothing is machine-translated).

### Cross-cutting
- **Audit log** (`apps.audit`): every create/update/delete of projects, passport fields, partners, contacts, members,
  tasks, subtasks, comments and attachments — who, when, entity, field, old → new. `GET /projects/{id}/audit-log/`
  (project team), `GET /audit-logs/` (admin).
- **Soft delete** (`deleted_at`) for projects, contacts, main tasks, subtasks, comments, attachments.
- **Money** `DECIMAL(14,2)` million EUR with `*_display` (`4,820`); dates in UTC with `deadline_display` (`DD.MM.YYYY`)
  and `created_at_display` (`14 Mar 2026, 09:12`).
- **Reference data** (`apps.reference`, seeded by migration `reference.0002`, re-runnable with
  `python manage.py seed_reference_data`): sectors, EU-27 countries (with flag emoji), Uzbekistan regions and districts in
  one self-referencing `Region` tree (`GET /reference/regions/?parent=<id>`), organizations, main-task template.

### Fixes to the template
- `MIGRATION_MODULES` was keyed by module path (`apps._auth`) instead of app label (`_auth`), so the dev/prod split was
  silently ignored. Fixed; the existing `_auth` and `upload` migrations were moved into `migrations/dev/` and copied to `migrations/prod/`.
- `BaseGenericAPI.perform_check` now passes the serializer context (request) to the validating serializer.
- Celery beat was documented but never ran: added `django_celery_beat` to `INSTALLED_APPS` and a `celery-beat` service
  (`DatabaseScheduler`) to `docker/docker-compose.yml`. Periodic tasks are also editable in Django admin.
