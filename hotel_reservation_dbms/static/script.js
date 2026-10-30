// Small client-side check to help users catch an invalid date range.
document.querySelectorAll('form').forEach(function (form) {
  form.addEventListener('submit', function (event) {
    const start = form.querySelector('input[name="check_in"]');
    const end = form.querySelector('input[name="check_out"]');
    if (start && end && start.value && end.value && end.value <= start.value) {
      event.preventDefault();
      alert('Check-out must be after check-in.');
    }
  });
});s