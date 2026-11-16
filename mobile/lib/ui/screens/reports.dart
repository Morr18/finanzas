import 'package:flutter/material.dart';

import '../../data/models.dart';
import '../../data/utils.dart';
import '../theme.dart';
import '../widgets.dart';

class ReportsScreen extends StatefulWidget {
  const ReportsScreen({super.key});

  @override
  State<ReportsScreen> createState() => _ReportsScreenState();
}

class _ReportData {
  const _ReportData({
    required this.summary,
    required this.series,
    required this.expenseTotals,
    required this.incomeTotals,
    required this.years,
    required this.yearRows,
  });

  final CategorySummary summary;
  final List<MonthlyPoint> series;
  final List<CategoryTotal> expenseTotals;
  final List<CategoryTotal> incomeTotals;
  final List<int> years;
  final List<YearRow> yearRows;
}

class _ReportsScreenState extends State<ReportsScreen> {
  bool _yearMode = false;
  String _month = monthKey();
  int _year = DateTime.now().year;
  String _breakdown = 'egreso';

  Future<_ReportData> _load() async {
    final db = AppScope.of(context).db;
    final bounds = monthBounds(_month);
    final summary = await db.summary(bounds.$1, bounds.$2);
    final series = await db.monthlySeries(months: 6);
    final expense = await db.categoryTotals('egreso', bounds.$1, bounds.$2);
    final income = await db.categoryTotals('ingreso', bounds.$1, bounds.$2);
    final years = await db.yearsWithData();
    final yearRows = await db.yearTotals(_year);
    return _ReportData(
      summary: summary,
      series: series,
      expenseTotals: expense,
      incomeTotals: income,
      years: years,
      yearRows: yearRows,
    );
  }

  @override
  Widget build(BuildContext context) {
    final state = AppScope.of(context);
    final colors = FinColors.of(context);
    return ScreenBody(
      child: DbFutureBuilder<_ReportData>(
        key: ValueKey('$_month|$_year'),
        load: _load,
        builder: (context, data) {
          return ListView(
            padding: const EdgeInsets.fromLTRB(16, 8, 16, 96),
            children: [
              SegmentedButton<bool>(
                segments: const [
                  ButtonSegment(
                    value: false,
                    label: Text('Mes'),
                    icon: Icon(Icons.calendar_month_outlined, size: 16),
                  ),
                  ButtonSegment(
                    value: true,
                    label: Text('Año'),
                    icon: Icon(Icons.calendar_today_outlined, size: 16),
                  ),
                ],
                selected: {_yearMode},
                showSelectedIcon: false,
                onSelectionChanged: (value) =>
                    setState(() => _yearMode = value.first),
              ),
              const SizedBox(height: 12),
              if (!_yearMode) ...[
                Align(
                  alignment: Alignment.centerLeft,
                  child: MonthSelector(
                    monthKey: _month,
                    onChanged: (value) => setState(() => _month = value),
                  ),
                ),
                const SizedBox(height: 12),
                Row(
                  children: [
                    Expanded(
                      child: StatCard(
                        label: 'Ingresos',
                        value: state.fmtBase(data.summary.income),
                        icon: Icons.south_west,
                        color: colors.green,
                      ),
                    ),
                    const SizedBox(width: 10),
                    Expanded(
                      child: StatCard(
                        label: 'Gastos',
                        value: state.fmtBase(data.summary.expense),
                        icon: Icons.north_east,
                        color: colors.red,
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 10),
                StatCard(
                  label: 'Balance del mes',
                  value: state.fmtBase(data.summary.net, plus: true),
                  icon: Icons.account_balance_wallet_outlined,
                  color: data.summary.net < 0 ? colors.red : colors.green,
                  caption:
                      'Tasa de ahorro: ${pctText(data.summary.net, data.summary.income)}',
                ),
                const SizedBox(height: 12),
                SectionCard(
                  title: 'Últimos 6 meses',
                  subtitle: 'Ingresos vs. gastos en ${state.shownCurrency}',
                  child: Column(
                    children: [
                      SimpleBarChart(
                        points: [
                          for (final point in data.series)
                            BarPoint(
                              label: mesesCortos[
                                  (int.tryParse(point.key.split('-')[1]) ?? 1) -
                                      1],
                              income: state.convert(
                                point.income,
                                state.db.baseCurrency,
                                '${point.key}-01',
                              ),
                              expense: state.convert(
                                point.expense,
                                state.db.baseCurrency,
                                '${point.key}-01',
                              ),
                            ),
                        ],
                      ),
                      const SizedBox(height: 8),
                      Row(
                        mainAxisAlignment: MainAxisAlignment.center,
                        children: [
                          _LegendDot(color: colors.green, label: 'Ingresos'),
                          const SizedBox(width: 16),
                          _LegendDot(color: colors.red, label: 'Gastos'),
                        ],
                      ),
                    ],
                  ),
                ),
                const SizedBox(height: 12),
                SectionCard(
                  title: 'Por categoría',
                  action: SegmentedButton<String>(
                    style: const ButtonStyle(
                      visualDensity: VisualDensity.compact,
                      tapTargetSize: MaterialTapTargetSize.shrinkWrap,
                    ),
                    segments: const [
                      ButtonSegment(value: 'egreso', label: Text('Gastos')),
                      ButtonSegment(value: 'ingreso', label: Text('Ingresos')),
                    ],
                    selected: {_breakdown},
                    showSelectedIcon: false,
                    onSelectionChanged: (value) =>
                        setState(() => _breakdown = value.first),
                  ),
                  child: _CategoryBreakdown(
                    rows: _breakdown == 'egreso'
                        ? data.expenseTotals
                        : data.incomeTotals,
                    total: _breakdown == 'egreso'
                        ? data.summary.expense
                        : data.summary.income,
                    kind: _breakdown,
                  ),
                ),
              ] else ...[
                Row(
                  children: [
                    Expanded(
                      child: DropdownButtonFormField<int>(
                        initialValue: data.years.contains(_year)
                            ? _year
                            : data.years.first,
                        isExpanded: true,
                        items: [
                          for (final year in data.years)
                            DropdownMenuItem(
                              value: year,
                              child: Text('Año $year'),
                            ),
                        ],
                        onChanged: (value) =>
                            setState(() => _year = value ?? _year),
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 12),
                _YearSummary(rows: data.yearRows),
                const SizedBox(height: 12),
                SectionCard(
                  title: 'Detalle mensual',
                  subtitle: 'Ingresos, gastos y balance',
                  padding: const EdgeInsets.fromLTRB(12, 14, 12, 8),
                  child: Column(
                    children: [
                      for (final row in data.yearRows) _YearRowTile(row: row),
                    ],
                  ),
                ),
              ],
            ],
          );
        },
      ),
    );
  }
}

class _LegendDot extends StatelessWidget {
  const _LegendDot({required this.color, required this.label});

  final Color color;
  final String label;

  @override
  Widget build(BuildContext context) {
    return Row(
      children: [
        Container(
          width: 8,
          height: 8,
          decoration: BoxDecoration(color: color, shape: BoxShape.circle),
        ),
        const SizedBox(width: 5),
        Text(
          label,
          style: TextStyle(fontSize: 11, color: FinColors.of(context).muted),
        ),
      ],
    );
  }
}

class _CategoryBreakdown extends StatelessWidget {
  const _CategoryBreakdown({
    required this.rows,
    required this.total,
    required this.kind,
  });

  final List<CategoryTotal> rows;
  final int total;
  final String kind;

  @override
  Widget build(BuildContext context) {
    final colors = FinColors.of(context);
    final state = AppScope.of(context);
    if (rows.isEmpty) {
      return EmptyState(
        icon: Icons.donut_large,
        title:
            kind == 'egreso' ? 'Sin gastos este mes' : 'Sin ingresos este mes',
        message: 'Registra movimientos para ver el desglose.',
      );
    }
    final accent = kind == 'egreso' ? colors.red : colors.green;
    return Column(
      children: [
        for (final row in rows.take(12))
          Padding(
            padding: const EdgeInsets.only(bottom: 12),
            child: Column(
              children: [
                Row(
                  children: [
                    ColorDot(hexColor(row.color), size: 8),
                    const SizedBox(width: 7),
                    Expanded(
                      child: Text(
                        row.name,
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                        style: TextStyle(fontSize: 12.5, color: colors.text),
                      ),
                    ),
                    Text(
                      pctText(row.total, total),
                      style: TextStyle(
                        fontSize: 10.5,
                        color: colors.subtle,
                      ),
                    ),
                    const SizedBox(width: 8),
                    Text(
                      state.fmtBase(row.total),
                      style: TextStyle(
                        fontSize: 12.5,
                        fontWeight: FontWeight.w700,
                        color: colors.text,
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 5),
                ProgressTrack(
                  ratio: total == 0 ? 0 : row.total / total,
                  color: accent,
                  height: 5,
                ),
              ],
            ),
          ),
      ],
    );
  }
}

class _YearSummary extends StatelessWidget {
  const _YearSummary({required this.rows});

  final List<YearRow> rows;

  @override
  Widget build(BuildContext context) {
    final state = AppScope.of(context);
    final colors = FinColors.of(context);
    final income = rows.fold<int>(0, (sum, row) => sum + row.income);
    final expense = rows.fold<int>(0, (sum, row) => sum + row.expense);
    final best = rows.reduce(
      (a, b) => a.net >= b.net ? a : b,
    );
    return Container(
      padding: const EdgeInsets.all(16),
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
              Expanded(
                child: _YearCell(
                  label: 'Ingresos',
                  value: state.fmtBase(income),
                  color: colors.green,
                ),
              ),
              Expanded(
                child: _YearCell(
                  label: 'Gastos',
                  value: state.fmtBase(expense),
                  color: colors.red,
                ),
              ),
              Expanded(
                child: _YearCell(
                  label: 'Balance',
                  value: state.fmtBase(income - expense, plus: true),
                  color: income - expense < 0 ? colors.red : colors.green,
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),
          Text(
            'Mejor mes: ${monthName(best.key)} · ${state.fmtBase(best.net, plus: true)}',
            style: TextStyle(fontSize: 11.5, color: colors.muted),
          ),
        ],
      ),
    );
  }
}

class _YearCell extends StatelessWidget {
  const _YearCell({
    required this.label,
    required this.value,
    required this.color,
  });

  final String label;
  final String value;
  final Color color;

  @override
  Widget build(BuildContext context) {
    final colors = FinColors.of(context);
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(label, style: TextStyle(fontSize: 10.5, color: colors.muted)),
        const SizedBox(height: 2),
        FittedBox(
          fit: BoxFit.scaleDown,
          alignment: Alignment.centerLeft,
          child: Text(
            value,
            style: TextStyle(
              fontSize: 14,
              fontWeight: FontWeight.w700,
              color: color,
            ),
          ),
        ),
      ],
    );
  }
}

class _YearRowTile extends StatelessWidget {
  const _YearRowTile({required this.row});

  final YearRow row;

  @override
  Widget build(BuildContext context) {
    final state = AppScope.of(context);
    final colors = FinColors.of(context);
    if (row.income == 0 && row.expense == 0) {
      return Padding(
        padding: const EdgeInsets.symmetric(vertical: 7),
        child: Row(
          children: [
            SizedBox(
              width: 34,
              child: Text(
                mesesCortos[row.month - 1],
                style: TextStyle(fontSize: 11.5, color: colors.subtle),
              ),
            ),
            Expanded(
              child: Text(
                'Sin movimientos',
                style: TextStyle(fontSize: 11.5, color: colors.subtle),
              ),
            ),
          ],
        ),
      );
    }
    final maxValue = row.income > row.expense ? row.income : row.expense;
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 6),
      child: Row(
        children: [
          SizedBox(
            width: 34,
            child: Text(
              mesesCortos[row.month - 1],
              style: TextStyle(
                fontSize: 11.5,
                fontWeight: FontWeight.w600,
                color: colors.muted,
              ),
            ),
          ),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Row(
                  children: [
                    Container(
                      width: maxValue == 0 ? 0 : 90 * row.income / maxValue,
                      height: 6,
                      decoration: BoxDecoration(
                        color: colors.green,
                        borderRadius: BorderRadius.circular(3),
                      ),
                    ),
                    if (row.income > 0) const SizedBox(width: 4),
                    Text(
                      state.fmtBase(row.income),
                      style: TextStyle(fontSize: 10.5, color: colors.muted),
                    ),
                  ],
                ),
                const SizedBox(height: 3),
                Row(
                  children: [
                    Container(
                      width: maxValue == 0 ? 0 : 90 * row.expense / maxValue,
                      height: 6,
                      decoration: BoxDecoration(
                        color: colors.red,
                        borderRadius: BorderRadius.circular(3),
                      ),
                    ),
                    if (row.expense > 0) const SizedBox(width: 4),
                    Text(
                      state.fmtBase(row.expense),
                      style: TextStyle(fontSize: 10.5, color: colors.muted),
                    ),
                  ],
                ),
              ],
            ),
          ),
          const SizedBox(width: 8),
          Text(
            state.fmtBase(row.net, plus: true),
            style: TextStyle(
              fontSize: 12,
              fontWeight: FontWeight.w700,
              color: row.net < 0 ? colors.red : colors.green,
            ),
          ),
        ],
      ),
    );
  }
}
