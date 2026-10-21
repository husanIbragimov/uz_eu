"""List records whose English value is empty while another language is filled in.

Covers both multilingual patterns:
- sibling columns: `name_ru` / `name_uz` / `name_en`
- JSON translation dicts: {"ru": "...", "uz": "...", "en": ""}

Nothing is translated automatically: the CSV is handed to the client to fill in.
"""

import csv
import io

from django.apps import apps
from django.core.management.base import BaseCommand
from django.db import models

OTHER_LANGUAGES = ("ru", "uz")


def _translatable_columns(model) -> list[tuple[str, list[str]]]:
    names = {field.name for field in model._meta.concrete_fields}
    columns = []
    for name in names:
        if name.endswith("_en"):
            base = name[:-3]
            others = [f"{base}_{lang}" for lang in OTHER_LANGUAGES if f"{base}_{lang}" in names]
            if others:
                columns.append((name, others))
    return columns


def _json_fields(model) -> list[str]:
    return [field.name for field in model._meta.concrete_fields if isinstance(field, models.JSONField)]


class Command(BaseCommand):
    help = "Report records with an empty English value (`*_en` columns or JSON translation dicts) as CSV."

    def add_arguments(self, parser):
        parser.add_argument("--output", help="CSV path (default: stdout)")

    def handle(self, *args, **options):
        rows = []
        for model in apps.get_models():
            manager = getattr(model, "all_objects", model._default_manager)
            for en_field, others in _translatable_columns(model):
                for obj in manager.all().only("pk", en_field, *others):
                    if not (getattr(obj, en_field) or "").strip() and any(getattr(obj, f) for f in others):
                        rows.append([model._meta.label, obj.pk, en_field, *(getattr(obj, f) for f in others[:1])])
            for json_field in _json_fields(model):
                for obj in manager.all().only("pk", json_field):
                    value = getattr(obj, json_field)
                    if not isinstance(value, dict) or not any(lang in value for lang in (*OTHER_LANGUAGES, "en")):
                        continue
                    if not (value.get("en") or "").strip() and any(value.get(lang) for lang in OTHER_LANGUAGES):
                        sample = next(value[lang] for lang in OTHER_LANGUAGES if value.get(lang))
                        rows.append([model._meta.label, obj.pk, json_field, sample])

        buffer = io.StringIO()
        writer = csv.writer(buffer)
        writer.writerow(["model", "id", "field", "existing_non_english_value"])
        writer.writerows(rows)
        if options.get("output"):
            with open(options["output"], "w", newline="", encoding="utf-8") as fh:
                fh.write(buffer.getvalue())
        else:
            self.stdout.write(buffer.getvalue(), ending="")
        self.stderr.write(self.style.SUCCESS(f"{len(rows)} record(s) are missing an English value."))
