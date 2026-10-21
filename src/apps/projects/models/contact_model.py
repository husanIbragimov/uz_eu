from django.db import models

from apps.common.choices import SideChoice
from apps.common.locale import TranslatableText as T
from apps.common.locale import getTextLazy as _
from apps.common.models import SoftDeleteModel
from apps.common.utils.phone_validator import international_phone_validator


class ProjectContact(SoftDeleteModel):
    """Responsible representative of the European or Uzbek side. Never exposed to viewers."""

    project = models.ForeignKey("projects.Project", on_delete=models.CASCADE, related_name="contacts")
    side = models.CharField(max_length=2, choices=SideChoice.choices, verbose_name=_(T.side))
    full_name = models.CharField(max_length=255, verbose_name=_(T.full_name))
    organization = models.CharField(max_length=255, verbose_name=_(T.organization))
    position = models.CharField(max_length=255, blank=True, default="", verbose_name=_(T.position))
    email = models.EmailField(blank=True, default="", verbose_name=_(T.email))
    phone = models.CharField(
        max_length=20,
        blank=True,
        default="",
        validators=[international_phone_validator],
        verbose_name=_(T.phone_number),
    )

    class Meta:
        ordering = ("side", "id")
        verbose_name = _(T.project_contact)
        verbose_name_plural = _(T.project_contacts)

    def __str__(self):
        return f"{self.full_name} ({self.organization})"
