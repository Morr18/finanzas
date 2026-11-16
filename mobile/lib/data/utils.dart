import 'dart:math' as math;

import 'package:intl/intl.dart';

const List<String> meses = [
  'Enero',
  'Febrero',
  'Marzo',
  'Abril',
  'Mayo',
  'Junio',
  'Julio',
  'Agosto',
  'Septiembre',
  'Octubre',
  'Noviembre',
  'Diciembre',
];

const List<String> mesesCortos = [
  'Ene',
  'Feb',
  'Mar',
  'Abr',
  'May',
  'Jun',
  'Jul',
  'Ago',
  'Sep',
  'Oct',
  'Nov',
  'Dic',
];

const List<String> diasSemana = [
  'Lunes',
  'Martes',
  'Miércoles',
  'Jueves',
  'Viernes',
  'Sábado',
  'Domingo',
];

const Map<String, String> frecuenciaLabels = {
  'mensual': 'Mensual',
  'quincenal': 'Quincenal',
  'semanal': 'Semanal',
  'anual': 'Anual',
};

const Map<String, String> currencySymbols = {
  'USD': 'US\$',
  'EUR': '€',
  'GBP': '£',
  'MXN': 'MX\$',
  'ARS': 'AR\$',
  'CLP': 'CL\$',
  'COP': 'CO\$',
  'PEN': 'S/',
  'BRL': 'R\$',
  'UYU': '\$U',
  'PYG': '₲',
  'BOB': 'Bs',
  'CRC': '₡',
  'DOP': 'RD\$',
  'GTQ': 'Q',
  'HNL': 'L',
  'NIO': 'C\$',
  'PAB': 'B/.',
  'VES': 'Bs.',
  'JPY': '¥',
  'CNY': 'CN¥',
  'CAD': 'CA\$',
  'AUD': 'A\$',
  'CHF': 'CHF ',
  'INR': '₹',
};

String normalizeCurrency(String? code) {
  final value = (code ?? '').trim().toUpperCase();
  if (value.isEmpty) return '';
  if (!RegExp(r'^[A-Z]{3}$').hasMatch(value)) {
    throw const FormatException(
        'Usa un código ISO de 3 letras, por ejemplo USD.');
  }
  return value;
}

String currencySymbol(String code, String baseSymbol) {
  final key = code.trim().toUpperCase();
  if (key.isEmpty) return baseSymbol;
  return currencySymbols[key] ?? '$key ';
}

String todayIso() => isoDate(DateTime.now());

String isoDate(DateTime date) => '${date.year.toString().padLeft(4, '0')}-'
    '${date.month.toString().padLeft(2, '0')}-'
    '${date.day.toString().padLeft(2, '0')}';

DateTime parseIso(String value) => DateTime.parse(value);

String fmtDate(String iso) {
  final date = DateTime.tryParse(iso);
  if (date == null) return iso;
  return '${date.day.toString().padLeft(2, '0')}/'
      '${date.month.toString().padLeft(2, '0')}/${date.year}';
}

String fmtDateShort(String iso) {
  final date = DateTime.tryParse(iso);
  if (date == null) return iso;
  final now = DateTime.now();
  final today = DateTime(now.year, now.month, now.day);
  final target = DateTime(date.year, date.month, date.day);
  if (target == today) return 'Hoy';
  if (target == today.subtract(const Duration(days: 1))) return 'Ayer';
  return '${date.day.toString().padLeft(2, '0')}/${date.month.toString().padLeft(2, '0')}';
}

String monthKey([DateTime? value]) {
  final date = value ?? DateTime.now();
  return '${date.year.toString().padLeft(4, '0')}-'
      '${date.month.toString().padLeft(2, '0')}';
}

String monthName(String key) {
  final parts = key.split('-');
  final month = int.tryParse(parts.length > 1 ? parts[1] : '') ?? 1;
  return meses[(month - 1).clamp(0, 11)];
}

int daysInMonth(int year, int month) => DateTime(year, month + 1, 0).day;

DateTime dateInMonth(int year, int month, int day) =>
    DateTime(year, month, day.clamp(1, daysInMonth(year, month)));

(String, String) monthBounds(String key) {
  final parts = key.split('-');
  final year = int.parse(parts[0]);
  final month = int.parse(parts[1]);
  final first = DateTime(year, month, 1);
  final last = DateTime(year, month + 1, 0);
  return (isoDate(first), isoDate(last));
}

String shiftMonth(String key, int delta) {
  final parts = key.split('-');
  final date = DateTime(int.parse(parts[0]), int.parse(parts[1]) + delta, 1);
  return monthKey(date);
}

List<String> recentMonthKeys(int count) {
  final now = DateTime.now();
  return List.generate(
    count,
    (index) => monthKey(DateTime(now.year, now.month - (count - 1 - index), 1)),
  );
}

int roundDiv(int value, int divisor) {
  final sign = value < 0 ? -1 : 1;
  final abs = value.abs();
  final quotient = abs ~/ divisor;
  final remainder = abs % divisor;
  return sign * (remainder * 2 >= divisor ? quotient + 1 : quotient);
}

String money(
  int cents, {
  String symbol = '\$',
  bool plus = false,
  bool es = false,
  bool decimals = true,
}) {
  final value = (cents == 0 ? 0 : cents.abs()) / 100;
  final pattern = decimals ? '#,##0.00' : '#,##0';
  final body = NumberFormat(pattern, es ? 'es' : 'en_US').format(value);
  if (cents < 0) return '-$symbol$body';
  if (plus && cents > 0) return '+$symbol$body';
  return '$symbol$body';
}

String moneyCompact(int cents, {String symbol = '', bool es = false}) {
  final value = cents / 100;
  final sign = value < 0 ? '-' : '';
  final abs = value.abs();
  if (abs >= 1000000) {
    return '$sign$symbol${NumberFormat('#,##0.#', es ? 'es' : 'en_US').format(abs / 1000000)} M';
  }
  if (abs >= 1000) {
    return '$sign$symbol${NumberFormat('#,##0.#', es ? 'es' : 'en_US').format(abs / 1000)} k';
  }
  return '$sign$symbol${NumberFormat('#,##0', es ? 'es' : 'en_US').format(abs)}';
}

String moneyInput(int cents, {bool es = false}) {
  if (cents == 0) return '';
  final raw = (cents / 100).toStringAsFixed(2);
  return es ? raw.replaceAll('.', ',') : raw;
}

String formatRate(double rate, {bool es = false}) {
  var text = NumberFormat('#,##0.######', es ? 'es' : 'en_US').format(rate);
  return text;
}

/// Acepta 1,234.56 y 1.234,56. Devuelve centavos o null si no es válido.
int? parseAmount(String raw, {bool allowZero = false}) {
  if (raw.contains('-')) return null;
  var text = raw.replaceAll(RegExp(r'[^\d.,]'), '');
  if (text.isEmpty || !RegExp(r'^[\d.,]+$').hasMatch(text)) return null;
  if (!RegExp(r'\d').hasMatch(text)) return null;

  final hasDot = text.contains('.');
  final hasComma = text.contains(',');
  if (hasDot && hasComma) {
    if (text.lastIndexOf(',') > text.lastIndexOf('.')) {
      text = text.replaceAll('.', '').replaceAll(',', '.');
    } else {
      text = text.replaceAll(',', '');
    }
  } else if (hasComma) {
    final parts = text.split(',');
    if (parts.length == 2 && parts.last.length <= 2) {
      text = text.replaceAll(',', '.');
    } else {
      text = text.replaceAll(',', '');
    }
  } else if (hasDot) {
    final parts = text.split('.');
    if (parts.length > 2 || (parts.length == 2 && parts.last.length > 2)) {
      text = text.replaceAll('.', '');
    }
  }

  final value = double.tryParse(text);
  if (value == null || value < 0 || (value == 0 && !allowZero)) return null;
  return (value * 100).round();
}

String pctText(int part, int whole) {
  if (whole == 0) return '—';
  return '${(part / whole * 100).round()}%';
}

double pct(int part, int whole) => whole == 0 ? 0 : part / whole * 100;

String truncate(String text, int max) =>
    text.length <= max ? text : '${text.substring(0, max - 1)}…';

String scheduleText(Map<String, dynamic> rule) {
  final frequency = rule['frequency'] as String? ?? 'mensual';
  final day = (rule['day'] as int?) ?? 1;
  if (frequency == 'quincenal') return 'Quincenal · días 1 y 16';
  if (frequency == 'semanal') {
    return 'Semanal · ${diasSemana[day % 7].toLowerCase()}';
  }
  if (frequency == 'anual') {
    final month = (rule['month'] as int?) ?? 1;
    return 'Anual · ${month.toString().padLeft(2, '0')}/${day.toString().padLeft(2, '0')}';
  }
  return 'Mensual · día $day';
}

Iterable<DateTime> iterRecurringDates(
  Map<String, dynamic> rule,
  DateTime after,
  DateTime until, {
  int limit = 600,
}) sync* {
  DateTime start;
  try {
    start = DateTime.parse(rule['start_date'] as String);
  } catch (_) {
    return;
  }
  final lower = start.isAfter(after) ? start : after;
  if (lower.isAfter(until)) return;

  final frequency = rule['frequency'] as String? ?? 'mensual';
  final day = (rule['day'] as int?) ?? 1;
  final month = (rule['month'] as int?) ?? 1;
  var produced = 0;

  if (frequency == 'mensual' || frequency == 'quincenal') {
    var year = lower.year;
    var monthCursor = lower.month;
    while (true) {
      final candidates = frequency == 'quincenal'
          ? const [1, 16]
          : [day.clamp(1, daysInMonth(year, monthCursor))];
      for (final candidateDay in candidates) {
        final candidate = DateTime(year, monthCursor, candidateDay);
        if (!candidate.isBefore(lower) && !candidate.isAfter(until)) {
          yield candidate;
          produced++;
          if (produced >= limit) return;
        } else if (candidate.isAfter(until)) {
          return;
        }
      }
      monthCursor++;
      if (monthCursor == 13) {
        year++;
        monthCursor = 1;
      }
      if (DateTime(year, monthCursor, 1).isAfter(until)) return;
    }
  } else if (frequency == 'semanal') {
    final target = day % 7;
    // DateTime.weekday usa 1 = lunes; las reglas usan 0 = lunes.
    final candidateDay =
        lower.add(Duration(days: (target - (lower.weekday - 1)) % 7));
    var candidate = candidateDay;
    while (!candidate.isAfter(until)) {
      yield candidate;
      produced++;
      if (produced >= limit) return;
      candidate = candidate.add(const Duration(days: 7));
    }
  } else if (frequency == 'anual') {
    var year = lower.year;
    while (true) {
      final candidate = dateInMonth(year, month, day);
      if (!candidate.isBefore(lower) && !candidate.isAfter(until)) {
        yield candidate;
        produced++;
        if (produced >= limit) return;
      }
      if (candidate.isAfter(until)) return;
      year++;
    }
  }
}

String? nextRecurringDate(Map<String, dynamic> rule, {DateTime? after}) {
  final lower = after ?? DateTime.now();
  final horizon = lower.add(const Duration(days: 366 * 3 + 2));
  for (final candidate in iterRecurringDates(rule, lower, horizon)) {
    return isoDate(candidate);
  }
  return null;
}

double clamp(double value, double min, double max) =>
    math.min(max, math.max(min, value));
