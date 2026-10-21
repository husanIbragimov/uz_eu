from django.db import transaction

from apps.audit.services import AuditService
from apps.common.choices import SideChoice
from apps.projects.models import CategoryHistory, MainTask, Project, ProjectContact, ProjectMember
from apps.reference.models import MainTaskTemplate, Organization

PROJECT_AUDIT_FIELDS = (
    "name",
    "category",
    "status",
    "cost",
    "sector",
    "countries",
    "district",
    "program",
    "initiator",
    "eu_partners",
    "uz_partners",
    "description",
)
CONTACT_AUDIT_FIELDS = ("side", "full_name", "organization", "position", "email", "phone")
MAIN_TASK_AUDIT_FIELDS = ("title", "position")

# validated-data keys that are not plain model fields
_RELATION_KEYS = ("countries", "eu_partner_names", "uz_partner_names", "initiator_name", "contacts")


def get_or_create_organizations(names: list[str], side: str) -> list[Organization]:
    """Tag input: reuse an existing organization (case-insensitive) or add it to the reference table."""
    organizations = []
    for raw_name in names:
        name = raw_name.strip()
        if not name:
            continue
        organization = Organization.objects.filter(side=side, name__iexact=name).first()
        if organization is None:
            organization = Organization.objects.create(side=side, name=name)
        if organization not in organizations:
            organizations.append(organization)
    return organizations


class ProjectService:
    @staticmethod
    def _split(data: dict) -> tuple[dict, dict]:
        data = dict(data)
        relations = {key: data.pop(key) for key in _RELATION_KEYS if key in data}
        return data, relations

    @staticmethod
    def _apply_relations(project: Project, relations: dict) -> None:
        if "countries" in relations:
            project.countries.set(relations["countries"])
        if "eu_partner_names" in relations:
            project.eu_partners.set(get_or_create_organizations(relations["eu_partner_names"], SideChoice.EU))
        if "uz_partner_names" in relations:
            project.uz_partners.set(get_or_create_organizations(relations["uz_partner_names"], SideChoice.UZ))

    @staticmethod
    def _initiator(relations: dict):
        name = (relations.get("initiator_name") or "").strip()
        return get_or_create_organizations([name], SideChoice.UZ)[0] if name else None

    @classmethod
    @transaction.atomic
    def create(cls, user, data: dict, seed_default_tasks: bool = True) -> Project:
        fields, relations = cls._split(data)
        if "initiator_name" in relations:
            fields["initiator"] = cls._initiator(relations)
        project = Project.objects.create(created_by=user, updated_by=user, **fields)
        cls._apply_relations(project, relations)

        if user is not None:
            ProjectMember.objects.get_or_create(project=project, user=user, defaults={"added_by": user})
        CategoryHistory.objects.create(
            project=project, from_category=None, to_category=project.category, changed_by=user
        )
        AuditService.log_create(user, project, PROJECT_AUDIT_FIELDS, project_id=project.pk)

        if seed_default_tasks:
            cls.seed_default_main_tasks(user, project)
        if relations.get("contacts"):
            cls.sync_contacts(user, project, relations["contacts"])
        return project

    @staticmethod
    def seed_default_main_tasks(user, project: Project) -> list[MainTask]:
        templates = MainTaskTemplate.objects.filter(is_active=True)
        tasks = MainTask.objects.bulk_create(
            [
                MainTask(project=project, title=template.title, position=index, created_by=user, updated_by=user)
                for index, template in enumerate(templates, start=1)
            ]
        )
        for task in tasks:
            AuditService.log_create(user, task, MAIN_TASK_AUDIT_FIELDS, project_id=project.pk)
        return tasks

    @classmethod
    @transaction.atomic
    def update(cls, user, project: Project, data: dict) -> Project:
        """Passport save: general information and (optionally) the full contact list, atomically."""
        before = AuditService.snapshot(project, PROJECT_AUDIT_FIELDS)
        fields, relations = cls._split(data)
        if "initiator_name" in relations:
            fields["initiator"] = cls._initiator(relations)
        for name, value in fields.items():
            setattr(project, name, value)
        project.updated_by = user
        project.save()
        cls._apply_relations(project, relations)
        AuditService.log_update(user, project, before, project_id=project.pk)

        if "contacts" in relations:
            cls.sync_contacts(user, project, relations["contacts"])
        return project

    @staticmethod
    @transaction.atomic
    def change_category(user, project: Project, category: str) -> bool:
        """Move a project to another category; all tasks, comments and files stay attached."""
        old_category = project.category
        if old_category == category:
            return False
        project.category = category
        project.updated_by = user
        project.save(update_fields=["category", "updated_by", "updated_at"])
        CategoryHistory.objects.create(
            project=project, from_category=old_category, to_category=category, changed_by=user
        )
        AuditService.log_field(user, project, "category", old_category, category, project_id=project.pk)
        return True

    @staticmethod
    @transaction.atomic
    def delete(user, project: Project) -> None:
        project.soft_delete(user)
        AuditService.log_delete(user, project, project_id=project.pk)

    # --- contacts -------------------------------------------------------------------------------

    @classmethod
    def sync_contacts(cls, user, project: Project, items: list[dict]) -> None:
        """Items with `id` are updated, items without are created, missing ones are soft-deleted."""
        existing = {contact.pk: contact for contact in project.contacts.all()}
        kept = set()
        for item in items:
            item = dict(item)
            contact_id = item.pop("id", None)
            if contact_id:
                cls.update_contact(user, existing[contact_id], item)
                kept.add(contact_id)
            else:
                cls.create_contact(user, project, item)
        for contact_id, contact in existing.items():
            if contact_id not in kept:
                cls.delete_contact(user, contact)

    @staticmethod
    def create_contact(user, project: Project, data: dict) -> ProjectContact:
        contact = ProjectContact.objects.create(project=project, created_by=user, updated_by=user, **data)
        AuditService.log_create(user, contact, CONTACT_AUDIT_FIELDS, project_id=project.pk)
        return contact

    @staticmethod
    def update_contact(user, contact: ProjectContact, data: dict) -> ProjectContact:
        before = AuditService.snapshot(contact, CONTACT_AUDIT_FIELDS)
        for name, value in data.items():
            setattr(contact, name, value)
        contact.updated_by = user
        contact.save()
        AuditService.log_update(user, contact, before, project_id=contact.project_id)
        return contact

    @staticmethod
    def delete_contact(user, contact: ProjectContact) -> None:
        contact.soft_delete(user)
        AuditService.log_delete(user, contact, project_id=contact.project_id)

    # --- members --------------------------------------------------------------------------------

    @staticmethod
    def add_member(actor, project: Project, user) -> ProjectMember:
        membership, created = ProjectMember.objects.get_or_create(
            project=project, user=user, defaults={"added_by": actor}
        )
        if created:
            AuditService.log_create(actor, membership, ("user",), project_id=project.pk)
        return membership

    @staticmethod
    def remove_member(actor, membership: ProjectMember) -> None:
        AuditService.log_delete(actor, membership, project_id=membership.project_id, label=str(membership.user))
        membership.delete()
