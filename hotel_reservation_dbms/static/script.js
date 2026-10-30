/**
 * Hotel Reservation System - Simple Client-Side Validation
 * Plain JavaScript (Beginner Friendly, No Frameworks)
 */

document.addEventListener('DOMContentLoaded', function () {
    // 1. Validate Booking Form Check-out > Check-in
    const bookingForm = document.getElementById('bookingForm');
    if (bookingForm) {
        const checkInInput = document.getElementById('check_in');
        const checkOutInput = document.getElementById('check_out');
        const errorBox = document.getElementById('dateValidationError');

        bookingForm.addEventListener('submit', function (event) {
            if (checkInInput.value && checkOutInput.value) {
                const checkInDate = new Date(checkInInput.value);
                const checkOutDate = new Date(checkOutInput.value);

                if (checkOutDate <= checkInDate) {
                    event.preventDefault(); // Stop form submission
                    if (errorBox) {
                        errorBox.style.display = 'block';
                    } else {
                        alert('Check-out date must be strictly after the check-in date.');
                    }
                    checkOutInput.focus();
                } else {
                    if (errorBox) {
                        errorBox.style.display = 'none';
                    }
                }
            }
        });

        // Hide error message when user modifies dates
        checkInInput.addEventListener('change', function () {
            if (errorBox) errorBox.style.display = 'none';
        });
        checkOutInput.addEventListener('change', function () {
            if (errorBox) errorBox.style.display = 'none';
        });
    }

    // 2. Validate Home Page Availability Search Form
    const searchForm = document.querySelector('.search-form');
    if (searchForm) {
        searchForm.addEventListener('submit', function (event) {
            const checkIn = searchForm.querySelector('input[name="check_in"]');
            const checkOut = searchForm.querySelector('input[name="check_out"]');
            if (checkIn && checkOut && checkIn.value && checkOut.value) {
                if (new Date(checkOut.value) <= new Date(checkIn.value)) {
                    event.preventDefault();
                    alert('Check-out date must be strictly after the check-in date.');
                    checkOut.focus();
                }
            }
        });
    }
});
