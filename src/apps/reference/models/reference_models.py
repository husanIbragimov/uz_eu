from django.db import models

from apps.common.choices import SideChoice
from apps.common.locale import TranslatableText as T
from apps.common.locale import getTextLazy as _


class Sector(models.Model):
    name = models.CharField(max_length=128, unique=True, verbose_name=_(T.common_name))
    position = models.PositiveIntegerField(default=0, verbose_name=_(T.sort_order))

    class Meta:
        ordering = ("position", "name")
        verbose_name = _(T.sector)
        verbose_name_plural = _(T.sectors)

    def __str__(self):
        return self.name


class Country(models.Model):
    name = models.CharField(max_length=128, unique=True, verbose_name=_(T.common_name))
    iso_code = models.CharField(max_length=2, unique=True, verbose_name=_(T.iso_code))
    is_eu_member = models.BooleanField(default=True, verbose_name=_(T.is_eu_member))

    class Meta:
        ordering = ("name",)
        verbose_name = _(T.country)
        verbose_name_plural = _(T.countries)

    def __str__(self):
        return self.name

    @property
    def flag(self) -> str:
        """Flag emoji built from the ISO 3166-1 alpha-2 code (regional indicator symbols)."""
        return "".join(chr(0x1F1E6 + ord(char) - ord("A")) for char in self.iso_code.upper())


class RegionQuerySet(models.QuerySet):
    def regions(self):
        return self.filter(parent__isnull=True)

    def districts(self):
        return self.filter(parent__isnull=False)


class Region(models.Model):
    """Uzbekistan administrative units as one tree: regions (no parent) and their districts (parent = region)."""

    parent = models.ForeignKey(
        "self",
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="children",
        verbose_name=_(T.region),
    )
    name = models.CharField(max_length=128, verbose_name=_(T.common_name))
    position = models.PositiveIntegerField(default=0, verbose_name=_(T.sort_order))

    objects = RegionQuerySet.as_manager()

    class Meta:
        ordering = ("position", "name")
        verbose_name = _(T.region)
        verbose_name_plural = _(T.regions)
        constraints = [
            models.UniqueConstraint(fields=["parent", "name"], name="unique_region_name_per_parent"),
            models.UniqueConstraint(
                fields=["name"], condition=models.Q(parent__isnull=True), name="unique_top_level_region_name"
            ),
        ]

    def __str__(self):
        return self.name

    @property
    def is_district(self) -> bool:
        return self.parent_id is not None


class Organization(models.Model):
    """European partners (EIB, KfW, ...) and Uzbek partners / initiating agencies."""

    name = models.CharField(max_length=255, verbose_name=_(T.common_name))
    side = models.CharField(max_length=2, choices=SideChoice.choices, verbose_name=_(T.side))

    class Meta:
        ordering = ("name",)
        verbose_name = _(T.organization)
        verbose_name_plural = _(T.organizations)
        constraints = [models.UniqueConstraint(fields=["side", "name"], name="unique_organization_per_side")]

    def __str__(self):
        return self.name


class MainTaskTemplate(models.Model):
    """Default main tasks seeded into every newly created project."""

    title = models.CharField(max_length=255, unique=True, verbose_name=_(T.title))
    position = models.PositiveIntegerField(default=0, verbose_name=_(T.sort_order))
    is_active = models.BooleanField(default=True, verbose_name=_(T.active))

    class Meta:
        ordering = ("position", "id")
        verbose_name = _(T.main_task_template)
        verbose_name_plural = _(T.main_task_templates)

    def __str__(self):
        return self.title
