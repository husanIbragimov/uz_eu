from django.urls import path

from apps.projects.views import (
    CategoryHistoryListAPIView,
    CommentListCreateAPIView,
    MainTaskListCreateAPIView,
    MainTaskReorderAPIView,
    MyProjectListAPIView,
    ProjectAuditLogAPIView,
    ProjectCategoryAPIView,
    ProjectContactDetailAPIView,
    ProjectContactListCreateAPIView,
    ProjectDetailAPIView,
    ProjectListCreateAPIView,
    ProjectMemberDeleteAPIView,
    ProjectMemberListCreateAPIView,
    ProjectStatsAPIView,
)

urlpatterns = [
    path("", ProjectListCreateAPIView.as_view(), name="list"),
    path("stats/", ProjectStatsAPIView.as_view(), name="stats"),
    path("my/", MyProjectListAPIView.as_view(), name="my"),
    path("<int:pk>/", ProjectDetailAPIView.as_view(), name="detail"),
    path("<int:project_pk>/category/", ProjectCategoryAPIView.as_view(), name="category"),
    path("<int:project_pk>/category-history/", CategoryHistoryListAPIView.as_view(), name="category-history"),
    path("<int:project_pk>/audit-log/", ProjectAuditLogAPIView.as_view(), name="audit-log"),
    path("<int:project_pk>/members/", ProjectMemberListCreateAPIView.as_view(), name="members"),
    path("<int:project_pk>/members/<int:user_id>/", ProjectMemberDeleteAPIView.as_view(), name="member-delete"),
    path("<int:project_pk>/contacts/", ProjectContactListCreateAPIView.as_view(), name="contacts"),
    path("<int:project_pk>/contacts/<int:pk>/", ProjectContactDetailAPIView.as_view(), name="contact-detail"),
    path("<int:project_pk>/main-tasks/", MainTaskListCreateAPIView.as_view(), name="main-tasks"),
    path("<int:project_pk>/main-tasks/reorder/", MainTaskReorderAPIView.as_view(), name="main-tasks-reorder"),
    path("<int:project_pk>/comments/", CommentListCreateAPIView.as_view(), name="comments"),
]
