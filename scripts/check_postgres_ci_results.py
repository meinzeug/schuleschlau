"""Fail closed when the dedicated PostgreSQL concurrency suite did not run."""

import sys
import xml.etree.ElementTree as ET
from pathlib import Path

REQUIRED_NOTICE_TESTS = {
    "test_confirmed_word_imports_do_not_hide_unreviewed_import",
    "test_foreign_view_only_calls_do_not_hide_eligible_call",
    "test_revoked_child_goal_events_do_not_hide_current_events",
    "test_displaced_round_receipt_rechecks_source_and_session",
    "test_displaced_exam_notice_rechecks_revision[ready]",
    "test_displaced_exam_notice_rechecks_revision[reminder]",
}
REQUIRED_EXAM_ROLE_TEST = (
    "backend.tests.test_exam_reviews", "test_parallel_parent_role_confirmations_have_one_winner"
)
REQUIRED_LIFECYCLE_TESTS = {
    ("backend.tests.test_job_interruption_race_roadmap", name)
    for name in (
        "test_interrupted_package_never_publishes_a_late_provider_result",
        "test_completed_package_wins_over_an_already_selected_reaper",
    )
} | {
    ("backend.tests.test_preferences_cas_2026", "test_parallel_preferences_same_revision_has_one_winner"),
} | {
    (
        "backend.tests.test_source_evaluation",
        f"test_child_or_family_erased_during_diagnosis_keeps_no_private_output[{cleanup}-{when}-{target}]",
    )
    for cleanup in (True, False)
    for when in ("during_provider", "after_output")
    for target in ("child", "family")
} | {
    ("backend.tests.test_schulbuddy_session_serialization", name)
    for name in (
        "test_held_revocation_cannot_enqueue_a_tutor_request",
        "test_held_revocation_cannot_publish_a_late_tutor_reply[None]",
        "test_held_revocation_cannot_publish_a_late_tutor_reply[42]",
        "test_tutor_commit_wins_before_real_session_revocation[enqueue]",
        "test_tutor_commit_wins_before_real_session_revocation[publish]",
        "test_family_call_session_first_conflicts_without_deadlock",
        "test_user_lock_busy_fails_closed_before_enqueuing_parent_request",
        "test_admin_disabling_parent_does_not_deadlock_with_parent_tutor",
    )
} | {
    ("backend.tests.test_schulbuddy_config_serialization", name)
    for name in (
        "test_notstop_committed_after_snapshot_discards_reply",
        "test_locked_provider_row_fails_closed_after_provider_call",
        "test_locked_provider_row_rolls_back_new_reservation",
        "test_real_emergency_stop_waits_only_for_short_final_commit",
        "test_overrun_conflict_retains_exact_cost_and_sets_stop[provider]",
        "test_overrun_conflict_retains_exact_cost_and_sets_stop[child_fee]",
        "test_known_cost_and_fee_without_prior_balance_remain_successful",
    )
} | {
    ("backend.tests.test_review_consent_stale_identity", name)
    for name in (
        "test_stale_loaded_installation_must_not_change_operator_approval[True]",
        "test_stale_loaded_installation_must_not_change_operator_approval[False]",
        "test_http_settings_interleaving_preserves_latest_approval[True]",
        "test_http_settings_interleaving_preserves_latest_approval[False]",
    )
} | {
    ("backend.tests.test_schulbuddy_installation_serialization", name)
    for name in (
        "test_completed_revocation_before_installation_lock_discards_work[enqueue]",
        "test_completed_revocation_before_installation_lock_discards_work[publish]",
        "test_operator_revocation_waits_for_guarded_commit[enqueue]",
        "test_operator_revocation_waits_for_guarded_commit[publish]",
        "test_admin_can_revoke_during_provider_call_and_known_cost_survives[None]",
        "test_admin_can_revoke_during_provider_call_and_known_cost_survives[42]",
        "test_busy_installation_row_fails_closed_with_no_duplicate_cost[enqueue]",
        "test_busy_installation_row_fails_closed_with_no_duplicate_cost[publish]",
        "test_installation_first_actor_never_deadlocks_with_tutor_usage_and_provider",
        "test_busy_installation_keeps_overrun_cost_once_and_sets_stop[provider]",
        "test_busy_installation_keeps_overrun_cost_once_and_sets_stop[child_fee]",
    )
}


def verify(path, minimum=20):
    root = ET.parse(path).getroot()
    if root.tag not in {"testsuite", "testsuites"}:
        raise ValueError("Not a JUnit test report")
    cases = root.findall(".//testcase")
    identities = [(case.get("classname"), case.get("name")) for case in cases]
    if len(cases) < minimum or len(set(identities)) != len(cases):
        raise ValueError("The expected distinct PostgreSQL tests did not all run")
    if any(not all(identity) for identity in identities):
        raise ValueError("A PostgreSQL test has no identity")
    if not REQUIRED_NOTICE_TESTS.issubset({name for _, name in identities}):
        raise ValueError("A required PostgreSQL notification regression is missing")
    if REQUIRED_EXAM_ROLE_TEST not in identities:
        raise ValueError("The PostgreSQL exam-role concurrency regression is missing")
    if not REQUIRED_LIFECYCLE_TESTS.issubset(set(identities)):
        raise ValueError("A required PostgreSQL lifecycle concurrency regression is missing")
    if any(next(root.iter(tag), None) is not None for tag in ("skipped", "failure", "error")):
        raise ValueError("A PostgreSQL test was skipped or failed")
    return len(cases)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit("Usage: check_postgres_ci_results.py REPORT.xml")
    try:
        count = verify(Path(sys.argv[1]))
    except (OSError, ET.ParseError, ValueError) as exc:
        raise SystemExit(f"PostgreSQL results not verified: {exc}") from exc
    print(f"Verified {count} distinct PostgreSQL test cases without skips.")
