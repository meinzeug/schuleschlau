/// Advance a local calendar date without assuming that a day has 24 hours.
DateTime nextCalendarDay(DateTime date) =>
    DateTime(date.year, date.month, date.day + 1);

/// Count calendar dates independently of 23- or 25-hour local days.
int calendarDayDifference(DateTime start, DateTime end) => DateTime.utc(
  end.year,
  end.month,
  end.day,
).difference(DateTime.utc(start.year, start.month, start.day)).inDays;

/// Iterate local dates at midnight without adding a fixed 24-hour duration.
Iterable<DateTime> calendarDays(DateTime start, DateTime end) sync* {
  final last = DateTime(end.year, end.month, end.day);
  for (
    var date = DateTime(start.year, start.month, start.day);
    !date.isAfter(last);
    date = nextCalendarDay(date)
  ) {
    yield date;
  }
}

/// Date-picker endpoints are inclusive; [value] is in the same local timezone.
bool isWithinCalendarDates(DateTime value, DateTime start, DateTime end) =>
    !value.isBefore(DateTime(start.year, start.month, start.day)) &&
    value.isBefore(nextCalendarDay(end));
