from .env import env

# Subtask deadline indicator: "yellow / risk of delay" when not completed and <= N days are left.
DEADLINE_RISK_DAYS = env.int("DEADLINE_RISK_DAYS", 7)

# Attachments on subtasks and comments
ATTACHMENT_MAX_SIZE_MB = env.int("ATTACHMENT_MAX_SIZE_MB", 25)
ATTACHMENT_ALLOWED_EXTENSIONS = env.list(
    "ATTACHMENT_ALLOWED_EXTENSIONS",
    default=["pdf", "doc", "docx", "xls", "xlsx", "jpg", "jpeg", "png", "dwg"],
)

# Authors may edit/delete their own comments only within this window (admins always can).
COMMENT_EDIT_WINDOW_MINUTES = env.int("COMMENT_EDIT_WINDOW_MINUTES", 15)
