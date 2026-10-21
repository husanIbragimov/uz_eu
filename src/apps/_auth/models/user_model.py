from django.contrib.auth.models import AbstractUser
from django.db import models

from apps._auth.managers.user_manager import UserManager
from apps.common.choices import ROLE_KEYS, ROLE_SIDES, UserRoleChoice
from apps.common.locale import TranslatableText as T
from apps.common.locale import getTextLazy as _
from apps.common.models import BaseModel


class User(AbstractUser, BaseModel):
    role = models.IntegerField(
        choices=UserRoleChoice.choices, default=UserRoleChoice.VIEWER,
    )
    avatar = models.ImageField(
        upload_to="avatars/", null=True, blank=True, verbose_name=_(T.avatar),
    )
    is_active = models.BooleanField(
        default=True, help_text=_(T.user_with_is_active_help_text), verbose_name=_(T.active),
    )

    objects = UserManager()

    USERNAME_FIELD = "username"

    class Meta:
        verbose_name = _(T.user)

    def __str__(self):
        return self.username

    @property
    def is_admin(self) -> bool:
        return self.is_superuser or self.role == UserRoleChoice.ADMIN

    @property
    def is_representative(self) -> bool:
        return self.role in ROLE_SIDES

    @property
    def role_key(self) -> str:
        return ROLE_KEYS.get(UserRoleChoice(self.role), "viewer")

    @property
    def side(self) -> str | None:
        """`eu` / `uz` for representatives, used for the comment side badge."""
        side = ROLE_SIDES.get(UserRoleChoice(self.role))
        return side.value if side else None

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip() or self.username
