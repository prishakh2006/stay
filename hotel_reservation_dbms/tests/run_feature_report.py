import unittest

from test_app import FeatureTests


REPORTS = (
    (
        "MySQL environment password",
        "MySQL connection uses MYSQL_PASSWORD and preserves default host, user, and database.",
        "test_mysql_connection_uses_environment_password",
    ),
    (
        "Missing MySQL password",
        "A missing MYSQL_PASSWORD produces a clear setup error before connecting.",
        "test_mysql_connection_requires_environment_password",
    ),
    (
        "Home and room listing",
        "Home and room pages render successfully.",
        "test_01_home_and_room_listing_render",
    ),
    (
        "Admin dashboard and navigation",
        "The admin dashboard renders, and public navigation exposes booking and login.",
        "test_01a_admin_dashboard_and_navigation",
    ),
    (
        "Customer phone validation",
        "Missing, placeholder, and malformed phone numbers are rejected.",
        "test_02_booking_phone_validation",
    ),
    (
        "Admin account creation",
        "The script stores an admin password hash and commits the account.",
        "test_03_admin_account_creation_script_hashes_password",
    ),
    (
        "Admin login",
        "Correct admin credentials create an admin session.",
        "test_04_admin_login_succeeds",
    ),
    (
        "Wrong password",
        "Incorrect credentials are rejected without authenticating.",
        "test_05_wrong_password_is_rejected",
    ),
    (
        "Customer registration",
        "Registration creates a customer and hashed customer account.",
        "test_06_customer_registration_creates_hashed_account",
    ),
    (
        "Customer login and logout",
        "Customer session is created on login and cleared on logout.",
        "test_07_customer_login_and_logout",
    ),
    (
        "Customer access restrictions",
        "Customers cannot open admin pages or cancel another customer's reservation.",
        "test_08_customer_cannot_access_admin_pages_or_other_bookings",
    ),
    (
        "Admin staff management",
        "Admins can list, add, and edit staff using parameterized SQL.",
        "test_09_admin_staff_management_add_and_edit",
    ),
    (
        "Staff deletion restriction",
        "Staff with reservations cannot be deleted.",
        "test_10_staff_with_reservations_cannot_be_deleted",
    ),
    (
        "Customer cancellation",
        "A customer cancellation updates only that customer's eligible booking.",
        "test_11_customer_can_cancel_own_eligible_booking",
    ),
    (
        "Admin cancellation",
        "Admin cancellation requires a reason and records the admin actor.",
        "test_12_admin_cancellation_requires_reason_and_records_it",
    ),
    (
        "Rebooking cancelled dates",
        "Availability checks exclude cancelled reservations and retain Booked overlap checks.",
        "test_13_cancelled_reservations_do_not_block_rebooking_query",
    ),
    (
        "Nearest date suggestions",
        "The nearest offsets are returned in +n, -n order with the same stay length.",
        "test_14_nearest_dates_use_order_and_keep_stay_length",
    ),
    (
        "Review submission",
        "A completed-stay customer review is inserted with the submitted details.",
        "test_15_completed_stay_review_is_saved",
    ),
    (
        "Duplicate review",
        "A duplicate review is rejected with a friendly message.",
        "test_16_duplicate_review_has_friendly_message",
    ),
    (
        "Review eligibility",
        "A review is refused when the customer's stay is not completed.",
        "test_17_reviews_for_incomplete_stays_are_refused",
    ),
    (
        "Average room-type rating",
        "The admin report displays average ratings grouped by room type.",
        "test_18_admin_sees_average_rating_per_room_type",
    ),
    (
        "Booking and payment features",
        "Existing booking and payment routes still accept valid requests.",
        "test_19_existing_booking_and_payment_routes_remain_available",
    ),
    (
        "Reservation overlap trigger",
        "The existing trigger message is preserved and failed booking is rolled back.",
        "test_20_overlap_trigger_error_message_is_preserved",
    ),
)


def main():
    failures = 0
    for name, expected, method_name in REPORTS:
        result = unittest.TestResult()
        FeatureTests(method_name).run(result)
        if result.wasSuccessful():
            actual = "Assertions passed."
            status = "PASS"
        else:
            failures += 1
            errors = result.errors + result.failures
            actual = " | ".join(
                detail.strip().splitlines()[-1] for _test, detail in errors)
            status = "FAIL"
        print(f"{name}\n  Expected: {expected}\n  Actual: {actual}\n  Result: {status}")
    print(f"\n{len(REPORTS) - failures}/{len(REPORTS)} feature checks passed.")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
