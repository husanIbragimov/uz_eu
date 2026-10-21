from django.urls import path

from apps.projects.views import (
    AttachmentDetailAPIView,
    CommentDetailAPIView,
    GlobalSearchAPIView,
    MainTaskDetailAPIView,
    SubtaskAttachmentCreateAPIView,
    SubtaskDetailAPIView,
    SubtaskListCreateAPIView,
    SubtaskReorderAPIView,
)

# Objects addressed by their own id (main tasks, subtasks, attachments, comments) + global search.
urlpatterns = [
    path("main-tasks/<int:pk>/", MainTaskDetailAPIView.as_view(), name="main-task-detail"),
    path("main-tasks/<int:main_task_pk>/subtasks/", SubtaskListCreateAPIView.as_view(), name="subtasks"),
    path("main-tasks/<int:main_task_pk>/subtasks/reorder/", SubtaskReorderAPIView.as_view(), name="subtasks-reorder"),
    path("subtasks/<int:pk>/", SubtaskDetailAPIView.as_view(), name="subtask-detail"),
    path(
        "subtasks/<int:subtask_pk>/attachments/",
        SubtaskAttachmentCreateAPIView.as_view(),
        name="subtask-attachments",
    ),
    path("attachments/<int:pk>/", AttachmentDetailAPIView.as_view(), name="attachment-detail"),
    path("comments/<int:pk>/", CommentDetailAPIView.as_view(), name="comment-detail"),
    path("search/", GlobalSearchAPIView.as_view(), name="search"),
]
