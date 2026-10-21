from datetime import date, datetime, timedelta
from datetime import timezone as dt_timezone
from decimal import Decimal

from django.test import SimpleTestCase, TestCase, override_settings

from apps.common.choices import UserRoleChoice
from apps.common.utils.formatting import format_deadline, format_money, format_timestamp
from apps.projects.choices import DeadlineIndicator, MainTaskStatus, SubtaskStatus
from apps.projects.permissions import can_create_project, can_edit_project, can_view_private
from apps.projects.services import deadline_indicator, main_task_status
from apps.projects.tests.factories import make_admin, make_project, make_user

TODAY = date(2026, 3, 14)
DEADLINE = date(2026, 3, 21)


class DeadlineIndicatorTests(SimpleTestCase):
    def indicator(self, deadline, status=SubtaskStatus.IN_PROGRESS, completed_at=None, risk_days=7):
        return deadline_indicator(deadline, status, completed_at, today=TODAY, risk_days=risk_days)

    def test_more_than_n_days_left_is_green(self):
        self.assertEqual(self.indicator(TODAY + timedelta(days=8)), DeadlineIndicator.GREEN)

    def test_exactly_n_days_left_is_yellow(self):
        self.assertEqual(self.indicator(TODAY + timedelta(days=7)), DeadlineIndicator.YELLOW)

    def test_deadline_today_is_yellow(self):
        self.assertEqual(self.indicator(TODAY), DeadlineIndicator.YELLOW)

    def test_deadline_yesterday_is_red(self):
        self.assertEqual(self.indicator(TODAY - timedelta(days=1)), DeadlineIndicator.RED)

    def test_not_started_follows_same_rules(self):
        self.assertEqual(self.indicator(TODAY + timedelta(days=3), SubtaskStatus.NOT_STARTED), DeadlineIndicator.YELLOW)

    def test_risk_threshold_is_configurable(self):
        self.assertEqual(self.indicator(TODAY + timedelta(days=8), risk_days=10), DeadlineIndicator.YELLOW)

    @override_settings(DEADLINE_RISK_DAYS=3)
    def test_default_threshold_comes_from_settings(self):
        result = deadline_indicator(TODAY + timedelta(days=4), SubtaskStatus.IN_PROGRESS, today=TODAY)
        self.assertEqual(result, DeadlineIndicator.GREEN)

    def test_completed_on_deadline_is_green(self):
        completed = datetime(2026, 3, 21, 23, 59, tzinfo=dt_timezone.utc)
        self.assertEqual(self.indicator(DEADLINE, SubtaskStatus.COMPLETED, completed), DeadlineIndicator.GREEN)

    def test_completed_before_deadline_is_green_even_when_deadline_passed(self):
        completed = datetime(2026, 3, 1, 10, 0, tzinfo=dt_timezone.utc)
        result = self.indicator(TODAY - timedelta(days=5), SubtaskStatus.COMPLETED, completed)
        self.assertEqual(result, DeadlineIndicator.GREEN)

    def test_completed_after_deadline_is_red(self):
        completed = datetime(2026, 3, 22, 0, 1, tzinfo=dt_timezone.utc)
        self.assertEqual(self.indicator(DEADLINE, SubtaskStatus.COMPLETED, completed), DeadlineIndicator.RED)

    def test_completed_within_risk_window_is_green_not_yellow(self):
        completed = datetime(2026, 3, 14, 9, 0, tzinfo=dt_timezone.utc)
        self.assertEqual(self.indicator(TODAY + timedelta(days=2), SubtaskStatus.COMPLETED, completed), "green")

    def test_under_review_past_deadline_is_red(self):
        self.assertEqual(self.indicator(TODAY - timedelta(days=1), SubtaskStatus.UNDER_REVIEW), DeadlineIndicator.RED)


class MainTaskStatusTests(SimpleTestCase):
    def test_no_subtasks_is_pending(self):
        self.assertEqual(main_task_status(0, 0, 0), MainTaskStatus.PENDING)

    def test_all_not_started_is_pending(self):
        self.assertEqual(main_task_status(3, 0, 0), MainTaskStatus.PENDING)

    def test_any_started_is_in_progress(self):
        self.assertEqual(main_task_status(3, 0, 1), MainTaskStatus.IN_PROGRESS)

    def test_some_completed_is_in_progress(self):
        self.assertEqual(main_task_status(3, 2, 2), MainTaskStatus.IN_PROGRESS)

    def test_all_completed_is_completed(self):
        self.assertEqual(main_task_status(3, 3, 3), MainTaskStatus.COMPLETED)


class FormattingTests(SimpleTestCase):
    def test_money_has_thousands_separator(self):
        self.assertEqual(format_money(Decimal("4820.00")), "4,820")
        self.assertEqual(format_money(Decimal("1234567.5")), "1,234,567.50")

    def test_deadline_format(self):
        self.assertEqual(format_deadline(date(2026, 3, 4)), "04.03.2026")

    def test_timestamp_format(self):
        value = datetime(2026, 3, 14, 9, 12, tzinfo=dt_timezone.utc)
        self.assertEqual(format_timestamp(value), "14 Mar 2026, 09:12")


class PermissionRuleTests(TestCase):
    def setUp(self):
        self.admin = make_admin()
        self.uz = make_user(UserRoleChoice.UZ_REPRESENTATIVE)
        self.eu = make_user(UserRoleChoice.EU_REPRESENTATIVE)
        self.viewer = make_user(UserRoleChoice.VIEWER)
        self.project = make_project(self.uz, seed_default_tasks=False)

    def test_create_rights(self):
        self.assertTrue(can_create_project(self.admin))
        self.assertTrue(can_create_project(self.uz))
        self.assertTrue(can_create_project(self.eu))
        self.assertFalse(can_create_project(self.viewer))

    def test_creator_is_member_and_can_edit(self):
        self.assertTrue(can_edit_project(self.uz, self.project))

    def test_unassigned_representative_cannot_edit(self):
        self.assertFalse(can_edit_project(self.eu, self.project))
        self.assertFalse(can_view_private(self.eu, self.project))

    def test_assigned_representative_can_edit(self):
        self.project.memberships.create(user=self.eu)
        self.assertTrue(can_edit_project(self.eu, self.project))

    def test_admin_can_edit_any_project(self):
        self.assertTrue(can_edit_project(self.admin, self.project))

    def test_viewer_never_sees_private_data(self):
        self.assertFalse(can_view_private(self.viewer, self.project))
