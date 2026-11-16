import 'package:flutter/material.dart';
import 'package:flutter_localizations/flutter_localizations.dart';

import 'data/database.dart';
import 'ui/screens/accounts.dart';
import 'ui/screens/budgets.dart';
import 'ui/screens/categories.dart';
import 'ui/screens/dashboard.dart';
import 'ui/screens/recurring.dart';
import 'ui/screens/reports.dart';
import 'ui/screens/rules.dart';
import 'ui/screens/settings.dart';
import 'ui/screens/transactions.dart';
import 'ui/theme.dart';
import 'ui/widgets.dart';

class FinanzasApp extends StatefulWidget {
  const FinanzasApp({
    super.key,
    required this.db,
    this.recurringCreated = 0,
  });

  final AppDatabase db;
  final int recurringCreated;

  @override
  State<FinanzasApp> createState() => _FinanzasAppState();
}

class _FinanzasAppState extends State<FinanzasApp> {
  late final AppState _state = AppState(widget.db);

  @override
  void dispose() {
    _state.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return AppScope(
      state: _state,
      child: AnimatedBuilder(
        animation: _state,
        builder: (context, _) {
          return MaterialApp(
            title: 'Finanzas',
            debugShowCheckedModeBanner: false,
            locale: const Locale('es'),
            supportedLocales: const [Locale('es'), Locale('en')],
            localizationsDelegates: const [
              GlobalMaterialLocalizations.delegate,
              GlobalWidgetsLocalizations.delegate,
              GlobalCupertinoLocalizations.delegate,
            ],
            theme: buildTheme(Brightness.light),
            darkTheme: buildTheme(Brightness.dark),
            themeMode: _state.themeMode,
            home: HomeShell(recurringCreated: widget.recurringCreated),
          );
        },
      ),
    );
  }
}

class HomeShell extends StatefulWidget {
  const HomeShell({super.key, this.recurringCreated = 0});

  final int recurringCreated;

  @override
  State<HomeShell> createState() => _HomeShellState();
}

class _HomeShellState extends State<HomeShell> {
  int _index = 0;
  bool _notifiedRecurring = false;

  static const _bottom = <String>[
    'dashboard',
    'transactions',
    'budgets',
    'reports',
    'more',
  ];

  @override
  void initState() {
    super.initState();
    if (widget.recurringCreated > 0 && !_notifiedRecurring) {
      _notifiedRecurring = true;
      WidgetsBinding.instance.addPostFrameCallback((_) {
        if (!mounted) return;
        showMessage(
          context,
          'Se generaron ${widget.recurringCreated} movimientos recurrentes.',
        );
      });
    }
  }

  static String _titleFor(String section) {
    switch (section) {
      case 'dashboard':
        return 'Resumen';
      case 'transactions':
        return 'Movimientos';
      case 'budgets':
        return 'Presupuestos';
      case 'reports':
        return 'Reportes';
      case 'accounts':
        return 'Cuentas';
      case 'categories':
        return 'Categorías';
      case 'recurring':
        return 'Recurrentes';
      case 'rules':
        return 'Reglas';
      case 'settings':
        return 'Ajustes';
      default:
        return 'Más';
    }
  }

  Widget _pageFor(String section) {
    switch (section) {
      case 'dashboard':
        return const DashboardScreen();
      case 'transactions':
        return const TransactionsScreen();
      case 'budgets':
        return const BudgetsScreen();
      case 'reports':
        return const ReportsScreen();
      case 'accounts':
        return const AccountsScreen();
      case 'categories':
        return const CategoriesScreen();
      case 'recurring':
        return const RecurringScreen();
      case 'rules':
        return const RulesScreen();
      case 'settings':
        return const SettingsScreen();
      default:
        return const MoreScreen();
    }
  }

  void _open(String section) {
    final index = _bottom.indexOf(section);
    if (index >= 0) {
      setState(() => _index = index);
    } else {
      Navigator.of(context).push(
        MaterialPageRoute<void>(
          builder: (_) => _SectionPage(section: section),
        ),
      );
    }
  }

  @override
  Widget build(BuildContext context) {
    final colors = FinColors.of(context);
    final section = _bottom[_index];
    return Scaffold(
      appBar: AppBar(
        title: Text(_titleFor(section)),
        actions: const [
          _CurrencyChip(),
          SizedBox(width: 8),
        ],
      ),
      drawer: _AppDrawer(current: section, onSelect: _open),
      body: SafeArea(
        child: _index == _bottom.length - 1
            ? MoreScreen(onNavigate: _open)
            : _pageFor(section),
      ),
      bottomNavigationBar: DecoratedBox(
        decoration: BoxDecoration(
          border: Border(top: BorderSide(color: colors.border)),
        ),
        child: NavigationBar(
          selectedIndex: _index,
          onDestinationSelected: (value) => setState(() => _index = value),
          destinations: const [
            NavigationDestination(
              icon: Icon(Icons.dashboard_outlined),
              selectedIcon: Icon(Icons.dashboard),
              label: 'Resumen',
            ),
            NavigationDestination(
              icon: Icon(Icons.receipt_long_outlined),
              selectedIcon: Icon(Icons.receipt_long),
              label: 'Movimientos',
            ),
            NavigationDestination(
              icon: Icon(Icons.pie_chart_outline),
              selectedIcon: Icon(Icons.pie_chart),
              label: 'Presupuestos',
            ),
            NavigationDestination(
              icon: Icon(Icons.bar_chart_outlined),
              selectedIcon: Icon(Icons.bar_chart),
              label: 'Reportes',
            ),
            NavigationDestination(
              icon: Icon(Icons.widgets_outlined),
              selectedIcon: Icon(Icons.widgets),
              label: 'Más',
            ),
          ],
        ),
      ),
    );
  }
}

class _SectionPage extends StatelessWidget {
  const _SectionPage({required this.section});

  final String section;

  @override
  Widget build(BuildContext context) {
    final titles = <String, String>{
      'accounts': 'Cuentas',
      'categories': 'Categorías',
      'recurring': 'Recurrentes',
      'rules': 'Reglas',
      'settings': 'Ajustes',
    };
    final pages = <String, Widget>{
      'accounts': const AccountsScreen(),
      'categories': const CategoriesScreen(),
      'recurring': const RecurringScreen(),
      'rules': const RulesScreen(),
      'settings': const SettingsScreen(),
    };
    return Scaffold(
      appBar: AppBar(title: Text(titles[section] ?? 'Finanzas')),
      body: SafeArea(child: pages[section] ?? const SizedBox.shrink()),
    );
  }
}

class MoreScreen extends StatelessWidget {
  const MoreScreen({super.key, this.onNavigate});

  final ValueChanged<String>? onNavigate;

  @override
  Widget build(BuildContext context) {
    final colors = FinColors.of(context);
    final items = <(String, String, IconData, String)>[
      (
        'accounts',
        'Cuentas',
        Icons.account_balance_wallet_outlined,
        'Saldos por cuenta y moneda'
      ),
      (
        'categories',
        'Categorías',
        Icons.local_offer_outlined,
        'Ingresos y gastos'
      ),
      ('recurring', 'Recurrentes', Icons.autorenew, 'Movimientos automáticos'),
      ('rules', 'Reglas', Icons.rule, 'Categoriza por texto'),
      (
        'settings',
        'Ajustes y respaldo',
        Icons.settings_outlined,
        'Moneda, tema y datos'
      ),
    ];
    final navigate = onNavigate ??
        (section) => Navigator.of(context).push(
              MaterialPageRoute<void>(
                builder: (_) => _SectionPage(section: section),
              ),
            );
    return ListView(
      padding: const EdgeInsets.fromLTRB(16, 8, 16, 24),
      children: [
        if (AppScope.of(context).isConverted)
          Container(
            margin: const EdgeInsets.only(bottom: 12),
            padding: const EdgeInsets.all(12),
            decoration: BoxDecoration(
              color: colors.primarySoft,
              borderRadius: BorderRadius.circular(12),
              border: Border.all(color: colors.primary.withValues(alpha: 0.25)),
            ),
            child: Row(
              children: [
                Icon(Icons.visibility_outlined,
                    size: 18, color: colors.primary),
                const SizedBox(width: 8),
                Expanded(
                  child: Text(
                    'Estás viendo los montos en '
                    '${AppScope.of(context).shownCurrency}. Los datos se '
                    'guardan en su moneda original.',
                    style: TextStyle(fontSize: 12.5, color: colors.primary),
                  ),
                ),
              ],
            ),
          ),
        Material(
          color: colors.card,
          clipBehavior: Clip.antiAlias,
          shape: RoundedRectangleBorder(
            borderRadius: BorderRadius.circular(16),
            side: BorderSide(color: colors.border),
          ),
          child: Column(
            children: [
              for (var index = 0; index < items.length; index++) ...[
                if (index > 0)
                  Divider(height: 1, indent: 58, color: colors.border),
                ListTile(
                  leading: Container(
                    width: 34,
                    height: 34,
                    decoration: BoxDecoration(
                      color: colors.primarySoft,
                      borderRadius: BorderRadius.circular(10),
                    ),
                    child:
                        Icon(items[index].$3, size: 18, color: colors.primary),
                  ),
                  title: Text(
                    items[index].$2,
                    style: const TextStyle(
                        fontSize: 14, fontWeight: FontWeight.w600),
                  ),
                  subtitle: Text(
                    items[index].$4,
                    style: TextStyle(fontSize: 11.5, color: colors.muted),
                  ),
                  trailing:
                      Icon(Icons.chevron_right, size: 20, color: colors.subtle),
                  onTap: () => navigate(items[index].$1),
                ),
              ],
            ],
          ),
        ),
        const SizedBox(height: 18),
        Center(
          child: Text(
            'Finanzas móvil · 100% offline',
            style: TextStyle(fontSize: 11.5, color: colors.subtle),
          ),
        ),
      ],
    );
  }
}

class _AppDrawer extends StatelessWidget {
  const _AppDrawer({required this.current, required this.onSelect});

  final String current;
  final ValueChanged<String> onSelect;

  @override
  Widget build(BuildContext context) {
    final colors = FinColors.of(context);
    final state = AppScope.of(context);
    final items = <(String, String, IconData)>[
      ('dashboard', 'Resumen', Icons.dashboard_outlined),
      ('transactions', 'Movimientos', Icons.receipt_long_outlined),
      ('budgets', 'Presupuestos', Icons.pie_chart_outline),
      ('reports', 'Reportes', Icons.bar_chart_outlined),
      ('accounts', 'Cuentas', Icons.account_balance_wallet_outlined),
      ('categories', 'Categorías', Icons.local_offer_outlined),
      ('recurring', 'Recurrentes', Icons.autorenew),
      ('rules', 'Reglas', Icons.rule),
      ('settings', 'Ajustes', Icons.settings_outlined),
    ];
    return Drawer(
      backgroundColor: colors.card,
      child: SafeArea(
        child: Column(
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Padding(
              padding: const EdgeInsets.fromLTRB(20, 22, 20, 14),
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Row(
                    children: [
                      Container(
                        width: 38,
                        height: 38,
                        decoration: BoxDecoration(
                          color: colors.primary,
                          borderRadius: BorderRadius.circular(12),
                        ),
                        child: const Icon(Icons.savings_outlined,
                            color: Colors.white, size: 21),
                      ),
                      const SizedBox(width: 10),
                      Text(
                        'Finanzas',
                        style: TextStyle(
                          fontSize: 18,
                          fontWeight: FontWeight.w800,
                          color: colors.text,
                        ),
                      ),
                    ],
                  ),
                  const SizedBox(height: 10),
                  Text(
                    'Moneda base: ${state.db.baseCurrency}',
                    style: TextStyle(fontSize: 12, color: colors.muted),
                  ),
                ],
              ),
            ),
            Divider(height: 1, color: colors.border),
            Expanded(
              child: ListView(
                padding: const EdgeInsets.symmetric(vertical: 8),
                children: items.map((item) {
                  final active = item.$1 == current;
                  return Padding(
                    padding:
                        const EdgeInsets.symmetric(horizontal: 10, vertical: 1),
                    child: ListTile(
                      dense: true,
                      shape: RoundedRectangleBorder(
                        borderRadius: BorderRadius.circular(10),
                      ),
                      selected: active,
                      selectedTileColor: colors.primarySoft,
                      leading: Icon(
                        item.$3,
                        size: 20,
                        color: active ? colors.primary : colors.muted,
                      ),
                      title: Text(
                        item.$2,
                        style: TextStyle(
                          fontSize: 13.5,
                          fontWeight:
                              active ? FontWeight.w700 : FontWeight.w500,
                          color: active ? colors.primary : colors.text,
                        ),
                      ),
                      onTap: () {
                        Scaffold.of(context).closeDrawer();
                        onSelect(item.$1);
                      },
                    ),
                  );
                }).toList(),
              ),
            ),
          ],
        ),
      ),
    );
  }
}

class _CurrencyChip extends StatelessWidget {
  const _CurrencyChip();

  @override
  Widget build(BuildContext context) {
    final state = AppScope.of(context);
    final colors = FinColors.of(context);
    final options = state.db.availableDisplayCurrencies;
    final isForeign = state.isConverted;
    return PopupMenuButton<String>(
      tooltip: 'Ver montos en otra moneda',
      position: PopupMenuPosition.under,
      onSelected: (value) async {
        if (value == '__settings__') {
          await Navigator.of(context).push(
            MaterialPageRoute<void>(
              builder: (_) => const _SectionPage(section: 'settings'),
            ),
          );
          return;
        }
        await state.setDisplayCurrency(value);
      },
      itemBuilder: (context) => [
        for (final code in options)
          PopupMenuItem<String>(
            value: code,
            child: Row(
              children: [
                Icon(
                  code == state.shownCurrency
                      ? Icons.radio_button_checked
                      : Icons.radio_button_unchecked,
                  size: 17,
                  color: code == state.shownCurrency
                      ? colors.primary
                      : colors.subtle,
                ),
                const SizedBox(width: 9),
                Flexible(
                  child: Text(
                    code == state.db.baseCurrency ? '$code (base)' : code,
                    style: const TextStyle(fontSize: 14),
                  ),
                ),
              ],
            ),
          ),
        const PopupMenuDivider(),
        const PopupMenuItem<String>(
          value: '__settings__',
          child: Row(
            children: [
              Icon(Icons.tune, size: 17),
              SizedBox(width: 9),
              Flexible(
                child: Text(
                  'Administrar monedas',
                  style: TextStyle(fontSize: 14),
                ),
              ),
            ],
          ),
        ),
      ],
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 6),
        decoration: BoxDecoration(
          color: isForeign ? colors.primarySoft : colors.cardSoft,
          borderRadius: BorderRadius.circular(999),
          border: Border.all(
            color: isForeign
                ? colors.primary.withValues(alpha: 0.35)
                : colors.border,
          ),
        ),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            Icon(
              isForeign ? Icons.currency_exchange : Icons.visibility_outlined,
              size: 14,
              color: isForeign ? colors.primary : colors.muted,
            ),
            const SizedBox(width: 5),
            Text(
              state.shownCurrency,
              style: TextStyle(
                fontSize: 12,
                fontWeight: FontWeight.w700,
                color: isForeign ? colors.primary : colors.text,
              ),
            ),
            const SizedBox(width: 2),
            Icon(
              Icons.expand_more,
              size: 15,
              color: isForeign ? colors.primary : colors.muted,
            ),
          ],
        ),
      ),
    );
  }
}
