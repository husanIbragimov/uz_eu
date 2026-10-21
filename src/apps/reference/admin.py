from django.contrib import admin

from apps.common.locale import TranslatableText as T
from apps.common.locale import getTextLazy as _
from apps.reference.models import Country, MainTaskTemplate, Organization, Region, Sector


@admin.register(Sector)
class SectorAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "position")
    list_editable = ("position",)
    search_fields = ("name",)


@admin.register(Country)
class CountryAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "iso_code", "is_eu_member")
    list_filter = ("is_eu_member",)
    search_fields = ("name", "iso_code")


class DistrictInline(admin.TabularInline):
    model = Region
    fk_name = "parent"
    fields = ("name", "position")
    extra = 0
    verbose_name = _(T.district)
    verbose_name_plural = _(T.districts)


@admin.register(Region)
class RegionAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "parent", "position")
    list_filter = (("parent", admin.EmptyFieldListFilter),)
    search_fields = ("name", "parent__name")
    inlines = (DistrictInline,)

    def get_inlines(self, request, obj):
        # districts are leaves; only top-level regions get the inline district editor
        return self.inlines if obj is None or obj.parent_id is None else ()


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ("id", "name", "side")
    list_filter = ("side",)
    search_fields = ("name",)


@admin.register(MainTaskTemplate)
class MainTaskTemplateAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "position", "is_active")
    list_editable = ("position", "is_active")
