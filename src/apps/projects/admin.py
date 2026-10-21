from django.contrib import admin

from apps.projects.models import (
    Attachment,
    CategoryHistory,
    Comment,
    MainTask,
    Project,
    ProjectContact,
    ProjectMember,
    Subtask,
)


class ProjectMemberInline(admin.TabularInline):
    model = ProjectMember
    fk_name = "project"
    fields = ("user", "added_by", "created_at")
    readonly_fields = ("added_by", "created_at")
    autocomplete_fields = ("user",)
    extra = 0


class ProjectContactInline(admin.TabularInline):
    model = ProjectContact
    fields = ("side", "full_name", "organization", "position", "email", "phone")
    extra = 0


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ("id", "code", "name", "category", "status", "cost", "sector", "updated_at", "deleted_at")
    list_filter = ("category", "status", "sector")
    search_fields = ("code", "name", "legacy_pmi_id")
    readonly_fields = ("code", "created_by", "updated_by", "created_at", "updated_at")
    filter_horizontal = ("countries", "eu_partners", "uz_partners")
    inlines = (ProjectMemberInline, ProjectContactInline)

    def get_queryset(self, request):
        # admins can see (and restore) soft-deleted projects
        return Project.all_objects.select_related("sector")


@admin.register(CategoryHistory)
class CategoryHistoryAdmin(admin.ModelAdmin):
    list_display = ("id", "project", "from_category", "to_category", "changed_by", "created_at")
    list_filter = ("to_category",)


@admin.register(MainTask)
class MainTaskAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "project", "position", "deleted_at")
    search_fields = ("title", "project__name")


@admin.register(Subtask)
class SubtaskAdmin(admin.ModelAdmin):
    list_display = ("id", "title", "main_task", "deadline", "status", "completed_at", "deleted_at")
    list_filter = ("status",)
    search_fields = ("title",)


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ("id", "project", "author", "created_at", "edited_at", "deleted_at")
    search_fields = ("body",)


@admin.register(Attachment)
class AttachmentAdmin(admin.ModelAdmin):
    list_display = ("id", "file_name", "mime_type", "size", "subtask", "comment", "created_at")
