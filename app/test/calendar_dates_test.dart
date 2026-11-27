import 'package:flutter_test/flutter_test.dart';
import 'package:schulpilot/calendar_dates.dart';
import 'package:schulpilot/exams_scope.dart';

void main() {
  test('Berliner Zeitumstellung ist im dafür gestarteten Test aktiv', () {
    if (const bool.fromEnvironment('CHECK_BERLIN_DST')) {
      expect(
        DateTime(2026, 3, 29).timeZoneOffset,
        isNot(DateTime(2026, 3, 30).timeZoneOffset),
      );
      expect(
        DateTime(2026, 10, 25).timeZoneOffset,
        isNot(DateTime(2026, 10, 26).timeZoneOffset),
      );
    }
  });
  test(
    'Frühling und Herbst enthalten jeden lokalen Kalendertag genau einmal',
    () {
      for (final caseData in [
        (
          DateTime(2026, 3, 28),
          DateTime(2026, 3, 31),
          ['2026-03-28', '2026-03-29', '2026-03-30', '2026-03-31'],
        ),
        (
          DateTime(2026, 10, 24),
          DateTime(2026, 10, 27),
          ['2026-10-24', '2026-10-25', '2026-10-26', '2026-10-27'],
        ),
      ]) {
        final days = calendarDays(caseData.$1, caseData.$2).toList();
        expect(days.map(examDate).toList(), caseData.$3);
        expect(days.every((date) => date.hour == 0), isTrue);
        expect(calendarDayDifference(caseData.$1, caseData.$2), 3);
      }
    },
  );

  test('Grenze und Schaltjahr werden als Kalendertage gerechnet', () {
    expect(
      calendarDayDifference(DateTime(2026, 3, 29), DateTime(2027, 3, 29)),
      365,
    );
    expect(
      calendarDayDifference(DateTime(2024, 1, 1), DateTime(2025, 1, 1)),
      366,
    );
    expect(
      calendarDayDifference(DateTime(2026, 1, 2), DateTime(2026, 1, 1)),
      -1,
    );
    expect(calendarDays(DateTime(2026, 1, 2), DateTime(2026, 1, 1)), isEmpty);
    expect(
      calendarDays(DateTime(2024, 2, 28), DateTime(2024, 3, 1)).map(examDate),
      ['2024-02-28', '2024-02-29', '2024-03-01'],
    );
  });

  test('Fotofilter schließt den letzten ausgewählten Tag vollständig ein', () {
    for (final selected in [DateTime(2026, 3, 29), DateTime(2026, 10, 25)]) {
      final lastMinute = DateTime(
        selected.year,
        selected.month,
        selected.day,
        23,
        59,
      );
      final nextDay = nextCalendarDay(selected);
      expect(isWithinCalendarDates(lastMinute, selected, selected), isTrue);
      expect(isWithinCalendarDates(nextDay, selected, selected), isFalse);
      expect(examDate(nextDay), isNot(examDate(selected)));
    }
  });
}
