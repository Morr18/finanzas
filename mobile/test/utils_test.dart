import 'package:flutter_test/flutter_test.dart';
import 'package:finanzas_mobile/data/utils.dart';

void main() {
  group('parseAmount', () {
    test('acepta formatos en inglés y español', () {
      expect(parseAmount('1,234.56'), 123456);
      expect(parseAmount('1.234,56'), 123456);
      expect(parseAmount('1,234'), 123400);
      expect(parseAmount('1.234'), 123400);
      expect(parseAmount('1250'), 125000);
      expect(parseAmount('  MX\$ 1,000.50 '), 100050);
      expect(parseAmount('0.99'), 99);
    });

    test('rechaza montos inválidos o cero', () {
      expect(parseAmount(''), isNull);
      expect(parseAmount('abc'), isNull);
      expect(parseAmount('0'), isNull);
      expect(parseAmount('-5'), isNull);
      expect(parseAmount('0', allowZero: true), 0);
    });
  });

  group('fechas y meses', () {
    test('monthBounds respeta meses cortos y bisiestos', () {
      expect(monthBounds('2026-02'), ('2026-02-01', '2026-02-28'));
      expect(monthBounds('2024-02'), ('2024-02-01', '2024-02-29'));
      expect(monthBounds('2026-12'), ('2026-12-01', '2026-12-31'));
    });

    test('shiftMonth cruza años', () {
      expect(shiftMonth('2026-01', -1), '2025-12');
      expect(shiftMonth('2026-12', 1), '2027-01');
      expect(shiftMonth('2026-06', 0), '2026-06');
    });

    test('fmtDate usa día/mes/año', () {
      expect(fmtDate('2026-11-05'), '05/11/2026');
    });
  });

  group('recurrentes', () {
    Map<String, dynamic> rule({
      String frequency = 'mensual',
      int day = 1,
      int month = 1,
      String start = '2026-01-01',
    }) =>
        {
          'frequency': frequency,
          'day': day,
          'month': month,
          'start_date': start,
        };

    test('mensual respeta el último día del mes', () {
      final dates = iterRecurringDates(
        rule(day: 31, start: '2026-01-01'),
        DateTime(2026, 1, 1),
        DateTime(2026, 3, 31),
      ).map(isoDate).toList();
      expect(dates, ['2026-01-31', '2026-02-28', '2026-03-31']);
    });

    test('quincenal genera los días 1 y 16', () {
      final dates = iterRecurringDates(
        rule(frequency: 'quincenal'),
        DateTime(2026, 1, 1),
        DateTime(2026, 2, 16),
      ).map(isoDate).toList();
      expect(dates, ['2026-01-01', '2026-01-16', '2026-02-01', '2026-02-16']);
    });

    test('semanal avanza cada siete días', () {
      final dates = iterRecurringDates(
        {
          ...rule(frequency: 'semanal', day: 0, start: '2026-01-05'),
        },
        DateTime(2026, 1, 5),
        DateTime(2026, 1, 26),
      ).map(isoDate).toList();
      expect(dates, ['2026-01-05', '2026-01-12', '2026-01-19', '2026-01-26']);
    });

    test('anual usa mes y día', () {
      final dates = iterRecurringDates(
        rule(frequency: 'anual', month: 9, day: 15, start: '2025-01-01'),
        DateTime(2026, 1, 1),
        DateTime(2028, 12, 31),
      ).map(isoDate).toList();
      expect(dates, ['2026-09-15', '2027-09-15', '2028-09-15']);
    });

    test('nextRecurringDate devuelve la primera fecha futura', () {
      final next = nextRecurringDate(
        rule(day: 10, start: '2026-01-01'),
        after: DateTime(2026, 5, 11),
      );
      expect(next, '2026-06-10');
    });
  });

  test('pctText evita dividir entre cero', () {
    expect(pctText(50, 200), '25%');
    expect(pctText(0, 0), '—');
  });

  test('money respeta signo y separadores', () {
    expect(money(123456, symbol: 'MX\$'), 'MX\$1,234.56');
    expect(money(-5000, symbol: 'MX\$'), '-MX\$50.00');
    expect(money(0, symbol: 'MX\$', decimals: false), 'MX\$0');
  });
}
