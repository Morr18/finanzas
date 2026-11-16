import 'package:flutter/material.dart';

import '../../data/models.dart';
import '../../data/utils.dart';
import '../theme.dart';
import '../widgets.dart';
import 'accounts.dart';
import 'budgets.dart';
import 'settings.dart';
import 'transactions.dart';

class DashboardScreen extends StatefulWidget {
  const DashboardScreen({super.key});

  @override
  State<DashboardScreen> createState() => _DashboardScreenState();
}

class _DashData {
  const _DashData({
    required this.accounts,
    required this.totalBalance,
    required this.summary,
    required this.budgets,
    required this.recent,
    required this.missingRates,
  });

  final List<AccountBalance> accounts;
  final int totalBalance;
  final CategorySummary summary;
  final List<BudgetRow> budgets;
  final List<Tx> recent;
  final List<String> missingRates;
}

class _DashboardScreenState extends State<DashboardScreen> {
  String _month = monthKey();

  Future<_DashData> _load() async {
    final db = AppScope.of(context).db;
    final accounts = await db.accountBalances();
    final total =
        accounts.fold<int>(0, (sum, account) => sum + account.baseBalance);
    final bounds = monthBounds(_month);
    final summary = await db.summary(bounds.$1, bounds.$2);
    final budgets = await db.budgetsForMonth(_month);
    final recent = await db.transactions(limit: 6);
    final missing = await db.missingRates();
    return _DashData(
      accounts: accounts,
      totalBalance: total,
      summary: summary,
      budgets: budgets,
      recent: recent,
      missingRates: missing,
    );
  }

  @override
  Widget build(BuildContext context) {
    final state = AppScope.of(context);
    return ScreenBody(
      fab: FloatingActionButton.extended(
        heroTag: 'dashboard_add',
        onPressed: () => showTransactionEditor(context),
        icon: const Icon(Icons.add),
        label: const Text('Movimiento'),
      ),
      child: DbFutureBuilder<_DashData>(
        key: ValueKey(_month),
        load: _load,
        builder: (context, data) {
          return ListView(
            padding: const EdgeInsets.fromLTRB(16, 6, 16, 96),
            children: [
              Row(
                children: [
                  Expanded(
                    child: MonthSelector(
                      monthKey: _month,
                      onChanged: (value) => setState(() => _month = value),
                    ),
                  ),
                  if (_month != monthKey())
                    TextButton(
                      onPressed: () => setState(() => _month = monthKey()),
                      child: const Text('Hoy'),
                    ),
                ],
              ),
              const SizedBox(height: 12),
              if (data.missingRates.isNotEmpty)
                _WarningBanner(
                  message:
                      'Falta el tipo de cambio de ${data.missingRates.join(', ')}. '
                      'Esos montos se muestran 1:1 hasta que registres una tasa.',
                  onTap: () => _openSettings(context),
                ),
              _BalanceCard(
                total: data.totalBalance,
                month: _month,
                summary: data.summary,
                accountCount: data.accounts.length,
              ),
              const SizedBox(height: 12),
              Row(
                children: [
                  Expanded(
                    child: StatCard(
                      label: 'Ingresos',
                      value: state.fmtBase(data.summary.income),
                      icon: Icons.south_west,
                      color: FinColors.of(context).green,
                    ),
                  ),
                  const SizedBox(width: 10),
                  Expanded(
                    child: StatCard(
                      label: 'Gastos',
                      value: state.fmtBase(data.summary.expense),
                      icon: Icons.north_east,
                      color: FinColors.of(context).red,
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 18),
              Text(
                'Acciones rápidas',
                style: TextStyle(
                  fontSize: 13,
                  fontWeight: FontWeight.w700,
                  color: FinColors.of(context).muted,
                ),
              ),
              const SizedBox(height: 8),
              Row(
                children: [
                  Expanded(
                    child: _QuickAction(
                      icon: Icons.add_circle_outline,
                      label: 'Ingreso',
                      color: FinColors.of(context).green,
                      onTap: () => showTransactionEditor(context,
                          initialKind: 'ingreso'),
                    ),
                  ),
                  const SizedBox(width: 8),
                  Expanded(
                    child: _QuickAction(
                      icon: Icons.remove_circle_outline,
                      label: 'Gasto',
                      color: FinColors.of(context).red,
                      onTap: () =>
                          showTransactionEditor(context, initialKind: 'egreso'),
                    ),
                  ),
                  const SizedBox(width: 8),
                  Expanded(
                    child: _QuickAction(
                      icon: Icons.swap_horiz,
                      label: 'Transferir',
                      color: FinColors.of(context).blue,
                      onTap: () => showTransferEditor(context),
                    ),
                  ),
                ],
              ),
              const SizedBox(height: 18),
              SectionCard(
                title: 'Cuentas',
                subtitle: 'Saldo actual en ${state.shownCurrency}',
                action: TextButton(
                  onPressed: () =>
                      pushScreen(context, 'Cuentas', const AccountsScreen()),
                  child: const Text('Ver todas'),
                ),
                child: data.accounts.isEmpty
                    ? const EmptyState(
                        icon: Icons.account_balance_wallet_outlined,
                        title: 'Sin cuentas',
                        message:
                            'Crea una cuenta para empezar a registrar movimientos.',
                      )
                    : Column(
                        children: [
                          for (final account in data.accounts.take(4))
                            _AccountRow(account: account),
                        ],
                      ),
              ),
              const SizedBox(height: 12),
              SectionCard(
                title: 'Presupuestos',
                subtitle: 'Avance de ${monthName(_month).toLowerCase()}',
                action: TextButton(
                  onPressed: () => pushScreen(
                      context, 'Presupuestos', const BudgetsScreen()),
                  child: const Text('Ver todos'),
                ),
                child: _BudgetPreview(budgets: data.budgets),
              ),
              const SizedBox(height: 12),
              SectionCard(
                title: 'Últimos movimientos',
                action: TextButton(
                  onPressed: () => pushScreen(
                      context, 'Movimientos', const TransactionsScreen()),
                  child: const Text('Ver todos'),
                ),
                child: data.recent.isEmpty
                    ? const EmptyState(
                        icon: Icons.receipt_long_outlined,
                        title: 'Todavía no hay movimientos',
                        message:
                            'Registra tu primer ingreso o gasto con el botón +.',
                      )
                    : Column(
                        children: [
                          for (final tx in data.recent)
                            TransactionTile(
                              tx: tx,
                              onTap: () =>
                                  showTransactionEditor(context, tx: tx),
                            ),
                        ],
                      ),
              ),
              const SizedBox(height: 12),
              const _OfflineHint(),
            ],
          );
        },
      ),
    );
  }

  void _openSettings(BuildContext context) {
    pushScreen(context, 'Ajustes', const SettingsScreen());
  }
}

class _WarningBanner extends StatelessWidget {
  const _WarningBanner({required this.message, this.onTap});

  final String message;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    final colors = FinColors.of(context);
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(12),
      child: Container(
        margin: const EdgeInsets.only(bottom: 12),
        padding: const EdgeInsets.all(12),
        decoration: BoxDecoration(
          color: colors.amberSoft,
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: colors.amber.withValues(alpha: 0.35)),
        ),
        child: Row(
          children: [
            Icon(Icons.info_outline, size: 18, color: colors.amber),
            const SizedBox(width: 8),
            Expanded(
              child: Text(
                message,
                style: TextStyle(fontSize: 12, color: colors.amber),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _BalanceCard extends StatelessWidget {
  const _BalanceCard({
    required this.total,
    required this.month,
    required this.summary,
    required this.accountCount,
  });

  final int total;
  final String month;
  final CategorySummary summary;
  final int accountCount;

  @override
  Widget build(BuildContext context) {
    final colors = FinColors.of(context);
    final state = AppScope.of(context);
    return Container(
      padding: const EdgeInsets.all(18),
      decoration: BoxDecoration(
        gradient: LinearGradient(
          begin: Alignment.topLeft,
          end: Alignment.bottomRight,
          colors: [colors.primary, colors.purple],
        ),
        borderRadius: BorderRadius.circular(18),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Row(
            children: [
              Icon(Icons.account_balance_wallet_outlined,
                  size: 16, color: Colors.white.withValues(alpha: 0.85)),
              const SizedBox(width: 6),
              Text(
                'Balance total',
                style: TextStyle(
                  fontSize: 12.5,
                  fontWeight: FontWeight.w600,
                  color: Colors.white.withValues(alpha: 0.9),
                ),
              ),
              const Spacer(),
              Container(
                padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
                decoration: BoxDecoration(
                  color: Colors.white.withValues(alpha: 0.18),
                  borderRadius: BorderRadius.circular(999),
                ),
                child: Text(
                  state.shownCurrency,
                  style: const TextStyle(
                    fontSize: 10.5,
                    fontWeight: FontWeight.w700,
                    color: Colors.white,
                  ),
                ),
              ),
            ],
          ),
          const SizedBox(height: 8),
          FittedBox(
            fit: BoxFit.scaleDown,
            alignment: Alignment.centerLeft,
            child: Text(
              state.fmtBase(total),
              style: const TextStyle(
                fontSize: 30,
                fontWeight: FontWeight.w800,
                color: Colors.white,
                fontFeatures: [FontFeature.tabularFigures()],
              ),
            ),
          ),
          const SizedBox(height: 12),
          Row(
            children: [
              Expanded(
                child: _BalanceFoot(
                  label: 'Este mes',
                  value: state.fmtBase(summary.net, plus: true),
                ),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: _BalanceFoot(label: 'Cuentas', value: '$accountCount'),
              ),
              const SizedBox(width: 10),
              Expanded(
                child: _BalanceFoot(
                  label: 'Ahorro',
                  value:
                      pctText(summary.income - summary.expense, summary.income),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}

class _BalanceFoot extends StatelessWidget {
  const _BalanceFoot({required this.label, required this.value});

  final String label;
  final String value;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Text(
          label,
          maxLines: 1,
          overflow: TextOverflow.ellipsis,
          style: TextStyle(
            fontSize: 10.5,
            color: Colors.white.withValues(alpha: 0.75),
          ),
        ),
        FittedBox(
          fit: BoxFit.scaleDown,
          alignment: Alignment.centerLeft,
          child: Text(
            value,
            maxLines: 1,
            style: const TextStyle(
              fontSize: 13,
              fontWeight: FontWeight.w700,
              color: Colors.white,
            ),
          ),
        ),
      ],
    );
  }
}

class _QuickAction extends StatelessWidget {
  const _QuickAction({
    required this.icon,
    required this.label,
    required this.color,
    required this.onTap,
  });

  final IconData icon;
  final String label;
  final Color color;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final colors = FinColors.of(context);
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(12),
      child: Container(
        padding: const EdgeInsets.symmetric(vertical: 12, horizontal: 8),
        decoration: BoxDecoration(
          color: colors.card,
          borderRadius: BorderRadius.circular(12),
          border: Border.all(color: colors.border),
        ),
        child: Column(
          children: [
            Icon(icon, size: 20, color: color),
            const SizedBox(height: 5),
            Text(
              label,
              maxLines: 1,
              overflow: TextOverflow.ellipsis,
              style: TextStyle(
                fontSize: 11.5,
                fontWeight: FontWeight.w600,
                color: colors.text,
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _AccountRow extends StatelessWidget {
  const _AccountRow({required this.account});

  final AccountBalance account;

  @override
  Widget build(BuildContext context) {
    final colors = FinColors.of(context);
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 7),
      child: Row(
        children: [
          ColorDot(hexColor(account.color), size: 9),
          const SizedBox(width: 9),
          Expanded(
            child: Row(
              children: [
                Flexible(
                  child: Text(
                    account.name,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: TextStyle(fontSize: 13.5, color: colors.text),
                  ),
                ),
                if (account.currency.isNotEmpty) ...[
                  const SizedBox(width: 6),
                  Container(
                    padding:
                        const EdgeInsets.symmetric(horizontal: 6, vertical: 1),
                    decoration: BoxDecoration(
                      color: colors.cardSoft,
                      borderRadius: BorderRadius.circular(5),
                      border: Border.all(color: colors.border),
                    ),
                    child: Text(
                      account.currency,
                      style: TextStyle(
                        fontSize: 9.5,
                        fontWeight: FontWeight.w700,
                        color: colors.muted,
                      ),
                    ),
                  ),
                ],
              ],
            ),
          ),
          AccountMoneyText(
            account.balance,
            currency: account.currency,
            size: 13.5,
            color: account.balance < 0 ? colors.red : colors.text,
          ),
        ],
      ),
    );
  }
}

class _BudgetPreview extends StatelessWidget {
  const _BudgetPreview({required this.budgets});

  final List<BudgetRow> budgets;

  @override
  Widget build(BuildContext context) {
    final colors = FinColors.of(context);
    final state = AppScope.of(context);
    final withBudget = budgets.where((row) => row.budget > 0).toList()
      ..sort((a, b) => b.ratio.compareTo(a.ratio));
    if (withBudget.isEmpty) {
      return const EmptyState(
        icon: Icons.pie_chart_outline,
        title: 'Sin presupuestos',
        message: 'Define un límite mensual por categoría.',
      );
    }
    return Column(
      children: [
        for (final row in withBudget.take(4))
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
                      '${state.fmtBase(row.spent)} / ${state.fmtBase(row.budget)}',
                      style: TextStyle(
                        fontSize: 11.5,
                        color:
                            row.spent > row.budget ? colors.red : colors.muted,
                        fontWeight: FontWeight.w600,
                      ),
                    ),
                  ],
                ),
                const SizedBox(height: 6),
                ProgressTrack(
                  ratio: row.ratio,
                  color: row.spent > row.budget ? colors.red : colors.primary,
                ),
              ],
            ),
          ),
      ],
    );
  }
}

class _OfflineHint extends StatelessWidget {
  const _OfflineHint();

  @override
  Widget build(BuildContext context) {
    final colors = FinColors.of(context);
    return Container(
      padding: const EdgeInsets.all(13),
      decoration: BoxDecoration(
        color: colors.cardSoft,
        borderRadius: BorderRadius.circular(12),
        border: Border.all(color: colors.border),
      ),
      child: Row(
        children: [
          Icon(Icons.wifi_off, size: 17, color: colors.muted),
          const SizedBox(width: 8),
          Expanded(
            child: Text(
              'Todo se guarda en este teléfono. Puedes exportar un respaldo '
              'desde Ajustes cuando quieras.',
              style: TextStyle(fontSize: 11.5, color: colors.muted),
            ),
          ),
        ],
      ),
    );
  }
}
