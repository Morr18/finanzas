import 'package:flutter/material.dart';

import '../../data/models.dart';
import '../../data/utils.dart';
import '../theme.dart';
import '../widgets.dart';

class BudgetsScreen extends StatefulWidget {
  const BudgetsScreen({super.key});

  @override
  State<BudgetsScreen> createState() => _BudgetsScreenState();
}

class _BudgetData {
  const _BudgetData({required this.rows, required this.previous});

  final List<BudgetRow> rows;
  final Map<int, int> previous;

  int get totalBudget => rows.fold(0, (sum, row) => sum + row.budget);
  int get totalSpent => rows.fold(0, (sum, row) => sum + row.spent);
}

class _BudgetsScreenState extends State<BudgetsScreen> {
  String _month = monthKey();

  Future<_BudgetData> _load() async {
    final db = AppScope.of(context).db;
    final rows = await db.budgetsForMonth(_month);
    final previousRows = await db.budgetsForMonth(shiftMonth(_month, -1));
    return _BudgetData(
      rows: rows,
      previous: {for (final row in previousRows) row.categoryId: row.spent},
    );
  }

  Future<void> _edit(BudgetRow row, Map<int, int> previous) async {
    final state = AppScope.of(context);
    final db = state.db;
    final day = monthBounds(_month).$2;
    // Se captura en la moneda de visualización y se guarda en la moneda base.
    final current = state.convert(row.budget, db.baseCurrency, day);
    final previousSpent = state.convert(
      previous[row.categoryId] ?? 0,
      db.baseCurrency,
      day,
    );
    final result = await showModalBottomSheet<int?>(
      context: context,
      isScrollControlled: true,
      useSafeArea: true,
      builder: (_) => _BudgetEditor(
        row: row,
        month: _month,
        current: current,
        previousSpent: previousSpent,
      ),
    );
    if (result == null) return;
    final base = state.convert(result, state.shownCurrency, day);
    await db.setBudget(row.categoryId, base);
    state.bump();
  }

  @override
  Widget build(BuildContext context) {
    final state = AppScope.of(context);
    final colors = FinColors.of(context);
    return ScreenBody(
      child: DbFutureBuilder<_BudgetData>(
        key: ValueKey(_month),
        load: _load,
        builder: (context, data) {
          final active = data.rows.where((row) => row.budget > 0).toList();
          final inactive = data.rows.where((row) => row.budget <= 0).toList();
          final ratio =
              data.totalBudget == 0 ? 0.0 : data.totalSpent / data.totalBudget;
          final statusColor = ratio > 1
              ? colors.red
              : ratio > 0.85
                  ? colors.amber
                  : colors.primary;
          return ListView(
            padding: const EdgeInsets.fromLTRB(16, 6, 16, 96),
            children: [
              Align(
                alignment: Alignment.centerLeft,
                child: MonthSelector(
                  monthKey: _month,
                  onChanged: (value) => setState(() => _month = value),
                ),
              ),
              const SizedBox(height: 12),
              Container(
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
                        Text(
                          'Presupuesto del mes',
                          style: TextStyle(
                            fontSize: 13,
                            fontWeight: FontWeight.w700,
                            color: colors.text,
                          ),
                        ),
                        const Spacer(),
                        Text(
                          pctText(data.totalSpent, data.totalBudget),
                          style: TextStyle(
                            fontSize: 12,
                            fontWeight: FontWeight.w700,
                            color: ratio > 1 ? colors.red : colors.muted,
                          ),
                        ),
                      ],
                    ),
                    const SizedBox(height: 8),
                    Row(
                      crossAxisAlignment: CrossAxisAlignment.end,
                      children: [
                        Expanded(
                          child: FittedBox(
                            fit: BoxFit.scaleDown,
                            alignment: Alignment.centerLeft,
                            child: Text(
                              state.fmtBase(data.totalSpent),
                              style: TextStyle(
                                fontSize: 24,
                                fontWeight: FontWeight.w800,
                                color: ratio > 1 ? colors.red : colors.text,
                              ),
                            ),
                          ),
                        ),
                        Text(
                          'de ${state.fmtBase(data.totalBudget)}',
                          style: TextStyle(fontSize: 12.5, color: colors.muted),
                        ),
                      ],
                    ),
                    const SizedBox(height: 9),
                    ProgressTrack(
                      ratio: ratio,
                      color: statusColor,
                      height: 8,
                    ),
                    const SizedBox(height: 7),
                    Text(
                      data.totalBudget == 0
                          ? 'Aún no defines presupuestos. Toca una categoría para empezar.'
                          : 'Disponible: ${state.fmtBase(data.totalBudget - data.totalSpent)}.',
                      style: TextStyle(fontSize: 11.5, color: colors.muted),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 16),
              if (data.rows.isEmpty)
                const EmptyState(
                  icon: Icons.pie_chart_outline,
                  title: 'Sin categorías de gasto',
                  message:
                      'Crea categorías de gasto para asignarles un presupuesto.',
                )
              else
                SectionCard(
                  title: 'Categorías de gasto',
                  subtitle: 'Toca una categoría para definir su límite',
                  padding: const EdgeInsets.fromLTRB(4, 14, 4, 6),
                  child: Column(
                    children: [
                      for (final row in active)
                        _BudgetRowTile(
                          row: row,
                          onTap: () => _edit(row, data.previous),
                        ),
                      if (active.isNotEmpty && inactive.isNotEmpty)
                        Padding(
                          padding: const EdgeInsets.fromLTRB(12, 10, 12, 4),
                          child: Row(
                            children: [
                              Text(
                                'SIN PRESUPUESTO',
                                style: TextStyle(
                                  fontSize: 10.5,
                                  fontWeight: FontWeight.w800,
                                  letterSpacing: 0.5,
                                  color: colors.subtle,
                                ),
                              ),
                              const SizedBox(width: 8),
                              Expanded(child: Divider(color: colors.border)),
                            ],
                          ),
                        ),
                      for (final row in inactive)
                        _BudgetRowTile(
                          row: row,
                          onTap: () => _edit(row, data.previous),
                        ),
                    ],
                  ),
                ),
              const SizedBox(height: 12),
              Container(
                padding: const EdgeInsets.all(13),
                decoration: BoxDecoration(
                  color: colors.cardSoft,
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(color: colors.border),
                ),
                child: Text(
                  'Los presupuestos se guardan en ${state.db.baseCurrency} y se '
                  'capturan en ${state.shownCurrency}. Si cambias «Ver en», el '
                  'límite sigue representando el mismo valor.',
                  style: TextStyle(fontSize: 11.5, color: colors.muted),
                ),
              ),
            ],
          );
        },
      ),
    );
  }
}

class _BudgetRowTile extends StatelessWidget {
  const _BudgetRowTile({required this.row, required this.onTap});

  final BudgetRow row;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final colors = FinColors.of(context);
    final state = AppScope.of(context);
    final over = row.budget > 0 && row.spent > row.budget;
    final accent = over ? colors.red : hexColor(row.color);
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(12),
      child: Padding(
        padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
        child: Column(
          children: [
            Row(
              children: [
                ColorDot(hexColor(row.color), size: 9),
                const SizedBox(width: 8),
                Expanded(
                  child: Text(
                    row.name,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: TextStyle(
                      fontSize: 13.5,
                      fontWeight: FontWeight.w600,
                      color: colors.text,
                    ),
                  ),
                ),
                const SizedBox(width: 6),
                if (row.budget == 0)
                  Text(
                    'Definir',
                    style: TextStyle(
                      fontSize: 11.5,
                      fontWeight: FontWeight.w600,
                      color: colors.primary,
                    ),
                  )
                else
                  Text(
                    '${state.fmtBase(row.spent)} / ${state.fmtBase(row.budget)}',
                    style: TextStyle(
                      fontSize: 11.5,
                      fontWeight: FontWeight.w600,
                      color: over ? colors.red : colors.muted,
                    ),
                  ),
              ],
            ),
            if (row.budget > 0) ...[
              const SizedBox(height: 7),
              ProgressTrack(ratio: row.ratio, color: accent, height: 5),
            ],
          ],
        ),
      ),
    );
  }
}

class _BudgetEditor extends StatefulWidget {
  const _BudgetEditor({
    required this.row,
    required this.month,
    required this.current,
    required this.previousSpent,
  });

  final BudgetRow row;
  final String month;
  final int current;
  final int previousSpent;

  @override
  State<_BudgetEditor> createState() => _BudgetEditorState();
}

class _BudgetEditorState extends State<_BudgetEditor> {
  late final TextEditingController _amount =
      TextEditingController(text: moneyInput(widget.current));

  @override
  void dispose() {
    _amount.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final colors = FinColors.of(context);
    final state = AppScope.of(context);
    return Padding(
      padding: EdgeInsets.only(bottom: MediaQuery.viewInsetsOf(context).bottom),
      child: SingleChildScrollView(
        padding: const EdgeInsets.fromLTRB(18, 8, 18, 16),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Center(
              child: Container(
                width: 38,
                height: 4,
                decoration: BoxDecoration(
                  color: colors.borderStrong,
                  borderRadius: BorderRadius.circular(999),
                ),
              ),
            ),
            const SizedBox(height: 14),
            Row(
              children: [
                ColorDot(hexColor(widget.row.color), size: 11),
                const SizedBox(width: 8),
                Expanded(
                  child: Text(
                    widget.row.name,
                    style: TextStyle(
                      fontSize: 17,
                      fontWeight: FontWeight.w800,
                      color: colors.text,
                    ),
                  ),
                ),
                IconButton(
                  onPressed: () => Navigator.pop(context),
                  icon: const Icon(Icons.close),
                ),
              ],
            ),
            const SizedBox(height: 4),
            Text(
              'Presupuesto de ${monthName(widget.month).toLowerCase()} · '
              'se guarda en ${state.db.baseCurrency}',
              style: TextStyle(fontSize: 12, color: colors.muted),
            ),
            const SizedBox(height: 14),
            LabeledField(
              label: 'Límite mensual (${state.shownCurrency})',
              help: widget.previousSpent > 0
                  ? 'El mes pasado gastaste ${state.fmt(widget.previousSpent)} en esta categoría.'
                  : 'Escribe 0 para quitar el presupuesto.',
              child: TextField(
                controller: _amount,
                autofocus: true,
                keyboardType:
                    const TextInputType.numberWithOptions(decimal: true),
                style: const TextStyle(
                  fontSize: 22,
                  fontWeight: FontWeight.w700,
                ),
                decoration: InputDecoration(
                  prefixText: '${state.symbol} ',
                  hintText: '0.00',
                ),
              ),
            ),
            const SizedBox(height: 16),
            Row(
              children: [
                if (widget.current > 0)
                  TextButton(
                    onPressed: () => Navigator.pop(context, 0),
                    child: Text('Quitar', style: TextStyle(color: colors.red)),
                  ),
                const Spacer(),
                Expanded(
                  flex: 2,
                  child: FilledButton(
                    onPressed: () {
                      final cents = parseAmount(_amount.text, allowZero: true);
                      if (cents == null) {
                        showMessage(
                          context,
                          'Escribe un monto válido.',
                          error: true,
                        );
                        return;
                      }
                      Navigator.pop(context, cents);
                    },
                    child: const Text('Guardar'),
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
