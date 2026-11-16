import 'package:flutter/material.dart';

import '../data/database.dart';
import '../data/models.dart';
import '../data/utils.dart';
import 'theme.dart';

/// Estado global de la app móvil.
///
/// Guarda el acceso a la base y expone helpers de formato y conversión para que
/// las pantallas no tengan que repetir la lógica de moneda de visualización.
class AppState extends ChangeNotifier {
  AppState(this.db);

  final AppDatabase db;
  int _revision = 0;

  int get revision => _revision;

  String get themeSetting => db.setting('theme', 'light');

  ThemeMode get themeMode {
    switch (themeSetting) {
      case 'dark':
        return ThemeMode.dark;
      case 'system':
        return ThemeMode.system;
      default:
        return ThemeMode.light;
    }
  }

  /// Código seleccionado en «Ver en», vacío cuando se ve en la moneda base.
  String get displayCurrency {
    final stored = db.setting('display_currency', '').trim().toUpperCase();
    if (stored.isEmpty || stored == db.baseCurrency) return '';
    final hasRate = db.fxRates.any((rate) => rate.currency == stored);
    return hasRate ? stored : '';
  }

  String get shownCurrency =>
      displayCurrency.isEmpty ? db.baseCurrency : displayCurrency;

  bool get isConverted => displayCurrency.isNotEmpty;

  String get symbol => currencySymbol(shownCurrency, db.currencySymbolSetting);

  bool get isSpanish => db.isSpanishNumbers;

  String fmt(int cents, {bool plus = false}) => money(
        cents,
        symbol: symbol,
        plus: plus,
        es: isSpanish,
      );

  String fmtCompact(int cents) => moneyCompact(
        cents,
        symbol: symbol,
        es: isSpanish,
      );

  /// Convierte centavos de [from] a la moneda de visualización.
  int convert(int cents, String from, [String? date]) =>
      db.convertBetween(cents, from, shownCurrency, date);

  String fmtFrom(int cents, String from, {String? date, bool plus = false}) =>
      fmt(convert(cents, from, date), plus: plus);

  String fmtBase(int cents, {bool plus = false}) =>
      fmtFrom(cents, db.baseCurrency, plus: plus);

  Future<void> setTheme(String value) async {
    await db.setSetting('theme', value);
    bump();
  }

  Future<void> setNumberFormat(String value) async {
    await db.setSetting('number_format', value);
    bump();
  }

  Future<void> setDisplayCurrency(String value) async {
    await db.setSetting('display_currency', value.trim().toUpperCase());
    bump();
  }

  Future<void> reload() async {
    await db.loadCaches();
    bump();
  }

  void bump() {
    _revision++;
    notifyListeners();
  }
}

class AppScope extends InheritedNotifier<AppState> {
  const AppScope({
    super.key,
    required AppState state,
    required super.child,
  }) : super(notifier: state);

  static AppState of(BuildContext context) {
    final scope = context.dependOnInheritedWidgetOfExactType<AppScope>();
    assert(scope != null, 'AppScope no encontrado en el árbol de widgets.');
    return scope!.notifier!;
  }
}

// ---------------------------------------------------------------- utilidades

Color hexColor(String value, [Color fallback = const Color(0xFF6366F1)]) {
  var text = value.trim().replaceAll('#', '');
  if (text.length == 3) {
    text = text.split('').map((char) => '$char$char').join();
  }
  if (text.length != 6) return fallback;
  final parsed = int.tryParse(text, radix: 16);
  if (parsed == null) return fallback;
  return Color(0xFF000000 | parsed);
}

const List<String> paletteColors = [
  '#6366f1',
  '#0ea5e9',
  '#06b6d4',
  '#10b981',
  '#22c55e',
  '#eab308',
  '#f59e0b',
  '#f97316',
  '#ef4444',
  '#ec4899',
  '#a855f7',
  '#8b5cf6',
  '#64748b',
  '#94a3b8',
];

void showMessage(BuildContext context, String message, {bool error = false}) {
  final colors = FinColors.of(context);
  ScaffoldMessenger.of(context)
    ..hideCurrentSnackBar()
    ..showSnackBar(
      SnackBar(
        content: Text(message),
        backgroundColor: error ? colors.red : null,
      ),
    );
}

Future<bool> confirmAction(
  BuildContext context, {
  required String title,
  required String message,
  String confirmLabel = 'Confirmar',
  bool destructive = false,
}) async {
  final colors = FinColors.of(context);
  final result = await showDialog<bool>(
    context: context,
    builder: (context) => AlertDialog(
      title: Text(title),
      content: Text(message),
      actions: [
        TextButton(
          onPressed: () => Navigator.pop(context, false),
          child: const Text('Cancelar'),
        ),
        FilledButton(
          style: destructive
              ? FilledButton.styleFrom(backgroundColor: colors.red)
              : null,
          onPressed: () => Navigator.pop(context, true),
          child: Text(confirmLabel),
        ),
      ],
    ),
  );
  return result ?? false;
}

// ---------------------------------------------------------------- widgets

class SectionCard extends StatelessWidget {
  const SectionCard({
    super.key,
    this.title,
    this.subtitle,
    this.action,
    required this.child,
    this.padding = const EdgeInsets.all(16),
  });

  final String? title;
  final String? subtitle;
  final Widget? action;
  final Widget child;
  final EdgeInsets padding;

  @override
  Widget build(BuildContext context) {
    final colors = FinColors.of(context);
    return Container(
      decoration: BoxDecoration(
        color: colors.card,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: colors.border),
      ),
      padding: padding,
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          if (title != null || action != null) ...[
            Row(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      if (title != null)
                        Text(
                          title!,
                          style: TextStyle(
                            fontSize: 15.5,
                            fontWeight: FontWeight.w700,
                            color: colors.text,
                          ),
                        ),
                      if (subtitle != null)
                        Padding(
                          padding: const EdgeInsets.only(top: 2),
                          child: Text(
                            subtitle!,
                            style: TextStyle(
                              fontSize: 12.5,
                              color: colors.muted,
                            ),
                          ),
                        ),
                    ],
                  ),
                ),
                if (action != null) action!,
              ],
            ),
            const SizedBox(height: 12),
          ],
          child,
        ],
      ),
    );
  }
}

/// Monto ya convertido a la moneda de visualización.
class MoneyText extends StatelessWidget {
  const MoneyText(
    this.cents, {
    super.key,
    this.plus = false,
    this.size = 16,
    this.color,
    this.weight = FontWeight.w700,
  });

  final int cents;
  final bool plus;
  final double size;
  final Color? color;
  final FontWeight weight;

  @override
  Widget build(BuildContext context) {
    final state = AppScope.of(context);
    final colors = FinColors.of(context);
    return Text(
      state.fmt(cents, plus: plus),
      style: TextStyle(
        fontSize: size,
        fontWeight: weight,
        color: color ?? colors.text,
        fontFeatures: const [FontFeature.tabularFigures()],
      ),
    );
  }
}

/// Monto guardado en la moneda de una cuenta, convertido para mostrarse.
class AccountMoneyText extends StatelessWidget {
  const AccountMoneyText(
    this.cents, {
    super.key,
    required this.currency,
    this.date,
    this.plus = false,
    this.size = 16,
    this.color,
    this.weight = FontWeight.w700,
  });

  final int cents;
  final String currency;
  final String? date;
  final bool plus;
  final double size;
  final Color? color;
  final FontWeight weight;

  @override
  Widget build(BuildContext context) {
    final state = AppScope.of(context);
    final colors = FinColors.of(context);
    return Text(
      state.fmtFrom(cents, currency, date: date, plus: plus),
      style: TextStyle(
        fontSize: size,
        fontWeight: weight,
        color: color ?? colors.text,
        fontFeatures: const [FontFeature.tabularFigures()],
      ),
    );
  }
}

class StatCard extends StatelessWidget {
  const StatCard({
    super.key,
    required this.label,
    required this.value,
    required this.icon,
    required this.color,
    this.caption,
  });

  final String label;
  final String value;
  final IconData icon;
  final Color color;
  final String? caption;

  @override
  Widget build(BuildContext context) {
    final colors = FinColors.of(context);
    return Container(
      padding: const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: colors.card,
        borderRadius: BorderRadius.circular(16),
        border: Border.all(color: colors.border),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Container(
                width: 30,
                height: 30,
                decoration: BoxDecoration(
                  color: color.withValues(alpha: 0.12),
                  borderRadius: BorderRadius.circular(9),
                ),
                child: Icon(icon, size: 17, color: color),
              ),
              const SizedBox(width: 8),
              Expanded(
                child: Text(
                  label,
                  maxLines: 1,
                  overflow: TextOverflow.ellipsis,
                  style: TextStyle(
                    fontSize: 12,
                    fontWeight: FontWeight.w600,
                    color: colors.muted,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 10),
          FittedBox(
            fit: BoxFit.scaleDown,
            alignment: Alignment.centerLeft,
            child: Text(
              value,
              style: TextStyle(
                fontSize: 19,
                fontWeight: FontWeight.w800,
                color: colors.text,
                fontFeatures: const [FontFeature.tabularFigures()],
              ),
            ),
          ),
          if (caption != null)
            Padding(
              padding: const EdgeInsets.only(top: 3),
              child: Text(
                caption!,
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style: TextStyle(fontSize: 11.5, color: colors.subtle),
              ),
            ),
        ],
      ),
    );
  }
}

class EmptyState extends StatelessWidget {
  const EmptyState({
    super.key,
    required this.icon,
    required this.title,
    this.message,
    this.action,
  });

  final IconData icon;
  final String title;
  final String? message;
  final Widget? action;

  @override
  Widget build(BuildContext context) {
    final colors = FinColors.of(context);
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 34, horizontal: 22),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Container(
            width: 52,
            height: 52,
            decoration: BoxDecoration(
              color: colors.cardSoft,
              shape: BoxShape.circle,
              border: Border.all(color: colors.border),
            ),
            child: Icon(icon, color: colors.subtle, size: 24),
          ),
          const SizedBox(height: 12),
          Text(
            title,
            textAlign: TextAlign.center,
            style: TextStyle(
              fontSize: 14.5,
              fontWeight: FontWeight.w700,
              color: colors.text,
            ),
          ),
          if (message != null) ...[
            const SizedBox(height: 4),
            Text(
              message!,
              textAlign: TextAlign.center,
              style: TextStyle(fontSize: 12.5, color: colors.muted),
            ),
          ],
          if (action != null) ...[
            const SizedBox(height: 14),
            action!,
          ],
        ],
      ),
    );
  }
}

class ProgressTrack extends StatelessWidget {
  const ProgressTrack({
    super.key,
    required this.ratio,
    required this.color,
    this.height = 7,
  });

  final double ratio;
  final Color color;
  final double height;

  @override
  Widget build(BuildContext context) {
    final colors = FinColors.of(context);
    return ClipRRect(
      borderRadius: BorderRadius.circular(999),
      child: LinearProgressIndicator(
        value: ratio.clamp(0, 1),
        minHeight: height,
        backgroundColor: colors.grid,
        valueColor: AlwaysStoppedAnimation<Color>(color),
      ),
    );
  }
}

class ColorDot extends StatelessWidget {
  const ColorDot(this.color, {super.key, this.size = 10});

  final Color color;
  final double size;

  @override
  Widget build(BuildContext context) {
    return Container(
      width: size,
      height: size,
      decoration: BoxDecoration(color: color, shape: BoxShape.circle),
    );
  }
}

class LabeledField extends StatelessWidget {
  const LabeledField({
    super.key,
    required this.label,
    required this.child,
    this.help,
  });

  final String label;
  final Widget child;
  final String? help;

  @override
  Widget build(BuildContext context) {
    final colors = FinColors.of(context);
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          label,
          style: TextStyle(
            fontSize: 12.5,
            fontWeight: FontWeight.w600,
            color: colors.muted,
          ),
        ),
        const SizedBox(height: 6),
        child,
        if (help != null)
          Padding(
            padding: const EdgeInsets.only(top: 5),
            child: Text(
              help!,
              style: TextStyle(fontSize: 11.5, color: colors.subtle),
            ),
          ),
      ],
    );
  }
}

class MonthSelector extends StatelessWidget {
  const MonthSelector({
    super.key,
    required this.monthKey,
    required this.onChanged,
  });

  final String monthKey;
  final ValueChanged<String> onChanged;

  @override
  Widget build(BuildContext context) {
    final colors = FinColors.of(context);
    final parts = monthKey.split('-');
    final year = parts.first;
    final label = '${monthName(monthKey)} $year';
    return Container(
      decoration: BoxDecoration(
        color: colors.card,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: colors.border),
      ),
      child: Row(
        mainAxisSize: MainAxisSize.min,
        children: [
          IconButton(
            visualDensity: VisualDensity.compact,
            icon: const Icon(Icons.chevron_left, size: 20),
            onPressed: () => onChanged(shiftMonth(monthKey, -1)),
            tooltip: 'Mes anterior',
          ),
          Text(
            label,
            style: TextStyle(
              fontSize: 13,
              fontWeight: FontWeight.w700,
              color: colors.text,
            ),
          ),
          IconButton(
            visualDensity: VisualDensity.compact,
            icon: const Icon(Icons.chevron_right, size: 20),
            onPressed: () => onChanged(shiftMonth(monthKey, 1)),
            tooltip: 'Mes siguiente',
          ),
        ],
      ),
    );
  }
}

class ColorPickerRow extends StatelessWidget {
  const ColorPickerRow({
    super.key,
    required this.selected,
    required this.onChanged,
  });

  final String selected;
  final ValueChanged<String> onChanged;

  @override
  Widget build(BuildContext context) {
    final colors = FinColors.of(context);
    return Wrap(
      spacing: 8,
      runSpacing: 8,
      children: paletteColors.map((code) {
        final active = code.toLowerCase() == selected.toLowerCase();
        return InkWell(
          borderRadius: BorderRadius.circular(999),
          onTap: () => onChanged(code),
          child: Container(
            width: 30,
            height: 30,
            decoration: BoxDecoration(
              color: hexColor(code),
              shape: BoxShape.circle,
              border: Border.all(
                color: active ? colors.text : Colors.transparent,
                width: 2,
              ),
            ),
            child: active
                ? const Icon(Icons.check, size: 15, color: Colors.white)
                : null,
          ),
        );
      }).toList(),
    );
  }
}

class BarPoint {
  const BarPoint(
      {required this.label, required this.income, required this.expense});

  final String label;
  final int income;
  final int expense;
}

/// Gráfico de barras agrupadas dibujado a mano para no añadir dependencias.
class SimpleBarChart extends StatelessWidget {
  const SimpleBarChart({
    super.key,
    required this.points,
    this.height = 190,
  });

  final List<BarPoint> points;
  final double height;

  @override
  Widget build(BuildContext context) {
    final colors = FinColors.of(context);
    return SizedBox(
      height: height,
      width: double.infinity,
      child: CustomPaint(
        painter: _BarChartPainter(
          points: points,
          incomeColor: colors.green,
          expenseColor: colors.red,
          gridColor: colors.grid,
          textColor: colors.muted,
          es: AppScope.of(context).isSpanish,
          symbol: AppScope.of(context).symbol,
        ),
      ),
    );
  }
}

class _BarChartPainter extends CustomPainter {
  _BarChartPainter({
    required this.points,
    required this.incomeColor,
    required this.expenseColor,
    required this.gridColor,
    required this.textColor,
    required this.es,
    required this.symbol,
  });

  final List<BarPoint> points;
  final Color incomeColor;
  final Color expenseColor;
  final Color gridColor;
  final Color textColor;
  final bool es;
  final String symbol;

  @override
  void paint(Canvas canvas, Size size) {
    if (points.isEmpty) return;
    const leftPad = 8.0;
    const rightPad = 8.0;
    const topPad = 18.0;
    const labelHeight = 20.0;

    final chartHeight = size.height - topPad - labelHeight;
    final maxValue = points.fold<int>(
      0,
      (max, point) =>
          [max, point.income, point.expense].reduce((a, b) => a > b ? a : b),
    );
    final scaleMax = maxValue <= 0 ? 1.0 : maxValue.toDouble();

    final gridPaint = Paint()
      ..color = gridColor
      ..strokeWidth = 1;
    for (var i = 0; i <= 3; i++) {
      final y = topPad + chartHeight * i / 3;
      canvas.drawLine(
          Offset(leftPad, y), Offset(size.width - rightPad, y), gridPaint);
    }

    final available = size.width - leftPad - rightPad;
    final slot = available / points.length;
    final barWidth = (slot * 0.28).clamp(3.0, 16.0);

    for (var i = 0; i < points.length; i++) {
      final point = points[i];
      final center = leftPad + slot * i + slot / 2;

      void drawBar(int value, double offset, Color color) {
        final ratio = value / scaleMax;
        final barHeight = ratio * chartHeight;
        if (barHeight <= 0.4) return;
        final rect = RRect.fromRectAndRadius(
          Rect.fromLTWH(
            center + offset - barWidth / 2,
            topPad + chartHeight - barHeight,
            barWidth,
            barHeight,
          ),
          const Radius.circular(3),
        );
        canvas.drawRRect(rect, Paint()..color = color);
      }

      drawBar(point.income, -barWidth * 0.62, incomeColor);
      drawBar(point.expense, barWidth * 0.62, expenseColor);

      final label = TextPainter(
        text: TextSpan(
          text: point.label,
          style: TextStyle(fontSize: 10, color: textColor),
        ),
        textDirection: TextDirection.ltr,
      )..layout(maxWidth: slot);
      label.paint(
        canvas,
        Offset(center - label.width / 2, size.height - labelHeight + 5),
      );
    }

    if (scaleMax > 1) {
      final top = TextPainter(
        text: TextSpan(
          text: moneyCompact(scaleMax.round(), symbol: symbol, es: es),
          style: TextStyle(fontSize: 9.5, color: textColor),
        ),
        textDirection: TextDirection.ltr,
      )..layout();
      top.paint(canvas, const Offset(leftPad, 1));
    }
  }

  @override
  bool shouldRepaint(covariant _BarChartPainter oldDelegate) {
    return oldDelegate.points != points ||
        oldDelegate.incomeColor != incomeColor ||
        oldDelegate.expenseColor != expenseColor;
  }
}

class KindBadge extends StatelessWidget {
  const KindBadge({super.key, required this.kind});

  final String kind;

  @override
  Widget build(BuildContext context) {
    final colors = FinColors.of(context);
    final label = switch (kind) {
      'ingreso' => 'Ingreso',
      'egreso' => 'Gasto',
      _ => 'Transferencia',
    };
    final color = switch (kind) {
      'ingreso' => colors.green,
      'egreso' => colors.red,
      _ => colors.blue,
    };
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
      decoration: BoxDecoration(
        color: color.withValues(alpha: 0.12),
        borderRadius: BorderRadius.circular(999),
      ),
      child: Text(
        label,
        style: TextStyle(
          fontSize: 10.5,
          fontWeight: FontWeight.w700,
          color: color,
        ),
      ),
    );
  }
}

/// Cuerpo de pantalla con botón flotante opcional.
///
/// Las pantallas viven dentro del shell principal, que ya aporta la barra
/// inferior; este Scaffold interno coloca el FAB por encima del contenido.
class ScreenBody extends StatelessWidget {
  const ScreenBody({super.key, required this.child, this.fab});

  final Widget child;
  final Widget? fab;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      backgroundColor: Colors.transparent,
      body: child,
      floatingActionButton: fab,
    );
  }
}

Future<void> pushScreen(
  BuildContext context,
  String title,
  Widget child,
) {
  return Navigator.of(context).push(
    MaterialPageRoute<void>(
      builder: (_) => Scaffold(
        appBar: AppBar(title: Text(title)),
        body: SafeArea(child: child),
      ),
    ),
  );
}

/// Carga datos de la base y se vuelve a ejecutar cuando cambia [AppState.revision].
class DbFutureBuilder<T> extends StatefulWidget {
  const DbFutureBuilder({
    super.key,
    required this.load,
    required this.builder,
    this.loading,
    this.errorBuilder,
  });

  final Future<T> Function() load;
  final Widget Function(BuildContext context, T data) builder;
  final Widget? loading;
  final Widget Function(BuildContext context, Object error)? errorBuilder;

  @override
  State<DbFutureBuilder<T>> createState() => _DbFutureBuilderState<T>();
}

class _DbFutureBuilderState<T> extends State<DbFutureBuilder<T>> {
  Future<T>? _future;
  int _revision = -1;

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    final revision = AppScope.of(context).revision;
    if (_future == null || revision != _revision) {
      _revision = revision;
      _future = widget.load();
    }
  }

  @override
  Widget build(BuildContext context) {
    return FutureBuilder<T>(
      future: _future,
      builder: (context, snapshot) {
        if (snapshot.hasError) {
          if (widget.errorBuilder != null) {
            return widget.errorBuilder!(context, snapshot.error!);
          }
          return Center(
            child: Padding(
              padding: const EdgeInsets.all(24),
              child: Text(
                'No se pudieron cargar los datos.\n${snapshot.error}',
                textAlign: TextAlign.center,
                style: TextStyle(color: FinColors.of(context).red),
              ),
            ),
          );
        }
        if (!snapshot.hasData) {
          return widget.loading ??
              const Center(
                child: Padding(
                  padding: EdgeInsets.all(40),
                  child: CircularProgressIndicator(strokeWidth: 2.4),
                ),
              );
        }
        return widget.builder(context, snapshot.data as T);
      },
    );
  }
}

class TransactionTile extends StatelessWidget {
  const TransactionTile({super.key, required this.tx, this.onTap});

  final Tx tx;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    final colors = FinColors.of(context);
    final state = AppScope.of(context);
    final color = tx.kind == 'ingreso'
        ? colors.green
        : tx.kind == 'egreso'
            ? colors.red
            : colors.blue;
    final icon = tx.kind == 'ingreso'
        ? Icons.south_west
        : tx.kind == 'egreso'
            ? Icons.north_east
            : Icons.swap_horiz;
    final categoryColor = tx.categoryColor.isEmpty
        ? colors.primary
        : hexColor(tx.categoryColor, colors.primary);

    final subtitle = <String>[
      fmtDate(tx.date),
      tx.accountName.isEmpty ? 'Sin cuenta' : tx.accountName,
      if (tx.kind == 'transferencia' && tx.transferAccountName.isNotEmpty)
        '→ ${tx.transferAccountName}',
      if (tx.kind != 'transferencia' && tx.categoryName.isNotEmpty)
        tx.categoryName,
    ].join(' · ');

    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(12),
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 4, vertical: 10),
        child: Row(
          children: [
            Container(
              width: 38,
              height: 38,
              decoration: BoxDecoration(
                color: categoryColor.withValues(alpha: 0.13),
                borderRadius: BorderRadius.circular(11),
              ),
              child: Icon(icon, size: 19, color: categoryColor),
            ),
            const SizedBox(width: 11),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    tx.title,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: TextStyle(
                      fontSize: 14,
                      fontWeight: FontWeight.w600,
                      color: colors.text,
                    ),
                  ),
                  const SizedBox(height: 2),
                  Text(
                    subtitle,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: TextStyle(fontSize: 11.5, color: colors.muted),
                  ),
                ],
              ),
            ),
            const SizedBox(width: 8),
            Column(
              crossAxisAlignment: CrossAxisAlignment.end,
              children: [
                AccountMoneyText(
                  tx.amount,
                  currency: tx.accountCurrency,
                  date: tx.date,
                  plus: tx.kind == 'ingreso',
                  color: color,
                  size: 14,
                ),
                if (tx.kind == 'transferencia' &&
                    tx.transferAmount != null &&
                    tx.transferAccountName.isNotEmpty)
                  Padding(
                    padding: const EdgeInsets.only(top: 2),
                    child: Text(
                      '${state.isConverted ? '' : ''}'
                      '${money(tx.transferAmount!, symbol: currencySymbol(tx.transferCurrency, state.symbol))}',
                      style: TextStyle(fontSize: 10.5, color: colors.subtle),
                    ),
                  ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}
