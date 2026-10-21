from django.db import models

from apps.common.locale import TranslatableText as T
from apps.common.locale import getTextLazy as _


class UserRoleChoice(models.IntegerChoices):
    ADMIN = 0, _(T.admin)
    # value 1 was the template's generic "user" role; it is now the read-only viewer
    VIEWER = 1, _(T.viewer)
    UZ_REPRESENTATIVE = 2, _(T.uz_representative)
    EU_REPRESENTATIVE = 3, _(T.eu_representative)


class SideChoice(models.TextChoices):
    EU = "eu", _(T.european_side)
    UZ = "uz", _(T.uzbek_side)


ROLE_KEYS = {
    UserRoleChoice.ADMIN: "admin",
    UserRoleChoice.VIEWER: "viewer",
    UserRoleChoice.UZ_REPRESENTATIVE: "uz_representative",
    UserRoleChoice.EU_REPRESENTATIVE: "eu_representative",
}

ROLE_SIDES = {
    UserRoleChoice.UZ_REPRESENTATIVE: SideChoice.UZ,
    UserRoleChoice.EU_REPRESENTATIVE: SideChoice.EU,
}
