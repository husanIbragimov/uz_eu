from django.urls import include, path

urlpatterns = [
    path(
        "auth/",
        include(("apps._auth.urls.auth_urls", "auth"), namespace="auth"),
    ),
    path(
        "user/",
        include(("apps._auth.urls.user_urls", "user"), namespace="user"),
    ),
    path("upload/", include(("apps.upload.urls", "upload"), namespace="upload")),
    path("reference/", include(("apps.reference.urls", "reference"), namespace="reference")),
    path("projects/", include(("apps.projects.urls.project_urls", "projects"), namespace="projects")),
    path("", include(("apps.projects.urls.workspace_urls", "workspace"), namespace="workspace")),
    path("notifications/", include(("apps.notifications.urls", "notifications"), namespace="notifications")),
    path("audit-logs/", include(("apps.audit.urls", "audit"), namespace="audit")),
]
