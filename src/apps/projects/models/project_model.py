from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models

from apps.common.choices import SideChoice
from apps.common.locale import TranslatableText as T
from apps.common.locale import getTextLazy as _
from apps.common.models import SoftDeleteModel
from apps.projects.choices import ProjectCategory, ProjectStatus

PROJECT_CODE_PREFIX = "UZEU"


class Project(SoftDeleteModel):
    code = models.CharField(max_length=32, unique=True, null=True, editable=False, verbose_name=_(T.project_code))
    name = models.CharField(max_length=500, verbose_name=_(T.project_name))
    category = models.CharField(
        max_length=16,
        choices=ProjectCategory.choices,
        default=ProjectCategory.ONGOING,
        db_index=True,
        verbose_name=_(T.category),
    )
    status = models.CharField(
        max_length=16,
        choices=ProjectStatus.choices,
        default=ProjectStatus.NOT_STARTED,
        db_index=True,
        verbose_name=_(T.status),
    )
    # million EUR
    cost = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
        verbose_name=_(T.project_cost),
    )
    # Nullable in the DB only so legacy PMI rows with gaps can be imported; the API requires them.
    sector = models.ForeignKey(
        "reference.Sector",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="projects",
        verbose_name=_(T.sector),
    )
    countries = models.ManyToManyField(
        "reference.Country", blank=True, related_name="projects", verbose_name=_(T.countries)
    )
    # A district-level Region; the project's region is `district.parent`.
    district = models.ForeignKey(
        "reference.Region",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="projects",
        limit_choices_to={"parent__isnull": False},
        verbose_name=_(T.district),
    )
    program = models.CharField(max_length=255, blank=True, default="", verbose_name=_(T.program))
    initiator = models.ForeignKey(
        "reference.Organization",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="initiated_projects",
        limit_choices_to={"side": SideChoice.UZ},
        verbose_name=_(T.initiator),
    )
    eu_partners = models.ManyToManyField(
        "reference.Organization",
        blank=True,
        related_name="eu_projects",
        limit_choices_to={"side": SideChoice.EU},
        verbose_name=_(T.eu_partners),
    )
    uz_partners = models.ManyToManyField(
        "reference.Organization",
        blank=True,
        related_name="uz_projects",
        limit_choices_to={"side": SideChoice.UZ},
        verbose_name=_(T.uz_partners),
    )
    description = models.TextField(blank=True, default="", verbose_name=_(T.description))
    legacy_pmi_id = models.CharField(max_length=64, unique=True, null=True, blank=True, verbose_name=_(T.legacy_pmi_id))
    members = models.ManyToManyField(
        "_auth.User",
        through="ProjectMember",
        through_fields=("project", "user"),
        related_name="member_projects",
        blank=True,
    )

    class Meta:
        ordering = ("-updated_at", "-id")
        verbose_name = _(T.project)
        verbose_name_plural = _(T.projects)

    def __str__(self):
        return f"{self.code} {self.name}" if self.code else self.name

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if not self.code:
            self.code = f"{PROJECT_CODE_PREFIX}-{self.pk:05d}"
            type(self).all_objects.filter(pk=self.pk).update(code=self.code)

    @property
    def region(self):
        return self.district.parent if self.district_id else None


class ProjectMember(models.Model):
    """Users assigned to a project; membership (plus admin) grants edit rights."""

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="memberships")
    user = models.ForeignKey("_auth.User", on_delete=models.CASCADE, related_name="project_memberships")
    added_by = models.ForeignKey("_auth.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("created_at",)
        verbose_name = _(T.project_member)
        verbose_name_plural = _(T.project_members)
        constraints = [models.UniqueConstraint(fields=["project", "user"], name="unique_project_member")]

    def __str__(self):
        return f"{self.user} @ {self.project}"


class CategoryHistory(models.Model):
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="category_history")
    from_category = models.CharField(
        max_length=16, choices=ProjectCategory.choices, null=True, blank=True, verbose_name=_(T.from_category)
    )
    to_category = models.CharField(max_length=16, choices=ProjectCategory.choices, verbose_name=_(T.to_category))
    changed_by = models.ForeignKey("_auth.User", on_delete=models.SET_NULL, null=True, blank=True, related_name="+")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at", "-id")
        verbose_name = _(T.category_history)
        verbose_name_plural = _(T.category_history)

    def __str__(self):
        return f"{self.project_id}: {self.from_category} -> {self.to_category}"
