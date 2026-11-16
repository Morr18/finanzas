import 'dart:async';

import 'package:flutter/material.dart';

import '../../data/models.dart';
import '../../data/utils.dart';
import '../theme.dart';
import '../widgets.dart';

Future<bool?> showTransactionEditor(
  BuildContext context, {
  Tx? tx,
  String? initialKind,
}) {
  return showModalBottomSheet<bool>(
    context: context,
    isScrollControlled: true,
    useSafeArea: true,
    builder: (_) => TransactionEditor(tx: tx, initialKind: initialKind),
  );
}

Future<bool?> showTransferEditor(BuildContext context) =>
    showTransactionEditor(context, initialKind: 'transferencia');

class TransactionsScreen extends StatefulWidget {
  const TransactionsScreen({super.key});

  @override
  State<TransactionsScreen> createState() => _TransactionsScreenState();
}

class _TxPage {
  const _TxPage({
    required this.items,
    required this.totals,
    required this.count,
    required this.accounts,
  });

  final List<Tx> items;
  final CategorySummary totals;
  final int count;
  final List<AccountBalance> accounts;
}

class _TransactionsScreenState extends State<TransactionsScreen> {
  final _search = TextEditingController();
  Timer? _debounce;
  String _query = '';
  String? _kind;
  int? _accountId;
  int _limit = 60;

  @override
  void dispose() {
    _debounce?.cancel();
    _search.dispose();
    super.dispose();
  }

  Future<_TxPage> _load() async {
    final db = AppScope.of(context).db;
    final items = await db.transactions(
      text: _query,
      kind: _kind,
      accountId: _accountId,
      limit: _limit,
    );
    final totals = await db.transactionTotals(
      text: _query,
      kind: _kind,
      accountId: _accountId,
    );
    final count = await db.transactionCount(
      text: _query,
      kind: _kind,
      accountId: _accountId,
    );
    final accounts = await db.accountBalances();
    return _TxPage(
        items: items, totals: totals, count: count, accounts: accounts);
  }

  void _onSearchChanged(String value) {
    _debounce?.cancel();
    _debounce = Timer(const Duration(milliseconds: 320), () {
      if (!mounted) return;
      setState(() {
        _query = value.trim();
        _limit = 60;
      });
    });
  }

  @override
  Widget build(BuildContext context) {
    final state = AppScope.of(context);
    final colors = FinColors.of(context);
    final key = '$_query|$_kind|$_accountId|$_limit';
    return ScreenBody(
      fab: FloatingActionButton(
        heroTag: 'tx_add',
        onPressed: () => showTransactionEditor(context),
        child: const Icon(Icons.add),
      ),
      child: DbFutureBuilder<_TxPage>(
        key: ValueKey(key),
        load: _load,
        builder: (context, data) {
          return Column(
            children: [
              Padding(
                padding: const EdgeInsets.fromLTRB(16, 4, 16, 0),
                child: Column(
                  children: [
                    TextField(
                      controller: _search,
                      onChanged: _onSearchChanged,
                      textInputAction: TextInputAction.search,
                      decoration: InputDecoration(
                        hintText: 'Buscar descripción, categoría, cuenta…',
                        prefixIcon: const Icon(Icons.search, size: 20),
                        suffixIcon: _search.text.isEmpty
                            ? null
                            : IconButton(
                                icon: const Icon(Icons.close, size: 18),
                                onPressed: () {
                                  _search.clear();
                                  setState(() {
                                    _query = '';
                                    _limit = 60;
                                  });
                                },
                              ),
                      ),
                    ),
                    const SizedBox(height: 9),
                    SizedBox(
                      height: 34,
                      child: ListView(
                        scrollDirection: Axis.horizontal,
                        children: [
                          _FilterChip(
                            label: 'Todos',
                            active: _kind == null,
                            onTap: () => setState(() {
                              _kind = null;
                              _limit = 60;
                            }),
                          ),
                          _FilterChip(
                            label: 'Ingresos',
                            active: _kind == 'ingreso',
                            color: colors.green,
                            onTap: () => setState(() {
                              _kind = 'ingreso';
                              _limit = 60;
                            }),
                          ),
                          _FilterChip(
                            label: 'Gastos',
                            active: _kind == 'egreso',
                            color: colors.red,
                            onTap: () => setState(() {
                              _kind = 'egreso';
                              _limit = 60;
                            }),
                          ),
                          _FilterChip(
                            label: 'Transferencias',
                            active: _kind == 'transferencia',
                            color: colors.blue,
                            onTap: () => setState(() {
                              _kind = 'transferencia';
                              _limit = 60;
                            }),
                          ),
                          if (data.accounts.isNotEmpty)
                            Padding(
                              padding: const EdgeInsets.only(left: 6),
                              child: PopupMenuButton<int?>(
                                tooltip: 'Filtrar por cuenta',
                                onSelected: (value) => setState(() {
                                  _accountId = value;
                                  _limit = 60;
                                }),
                                itemBuilder: (context) => [
                                  const PopupMenuItem<int?>(
                                    value: null,
                                    child: Text('Todas las cuentas'),
                                  ),
                                  for (final account in data.accounts)
                                    PopupMenuItem<int?>(
                                      value: account.id,
                                      child: Text(account.name),
                                    ),
                                ],
                                child: Container(
                                  padding: const EdgeInsets.symmetric(
                                    horizontal: 11,
                                    vertical: 6,
                                  ),
                                  decoration: BoxDecoration(
                                    color: _accountId == null
                                        ? colors.card
                                        : colors.primarySoft,
                                    borderRadius: BorderRadius.circular(999),
                                    border: Border.all(
                                      color: _accountId == null
                                          ? colors.border
                                          : colors.primary
                                              .withValues(alpha: 0.4),
                                    ),
                                  ),
                                  child: Row(
                                    children: [
                                      Icon(
                                          Icons.account_balance_wallet_outlined,
                                          size: 13,
                                          color: _accountId == null
                                              ? colors.muted
                                              : colors.primary),
                                      const SizedBox(width: 4),
                                      Text(
                                        _accountId == null
                                            ? 'Cuenta'
                                            : data.accounts
                                                .firstWhere(
                                                  (account) =>
                                                      account.id == _accountId,
                                                  orElse: () =>
                                                      data.accounts.first,
                                                )
                                                .name,
                                        style: TextStyle(
                                          fontSize: 11.5,
                                          fontWeight: FontWeight.w600,
                                          color: _accountId == null
                                              ? colors.muted
                                              : colors.primary,
                                        ),
                                      ),
                                    ],
                                  ),
                                ),
                              ),
                            ),
                        ],
                      ),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 10),
              Padding(
                padding: const EdgeInsets.symmetric(horizontal: 16),
                child: Container(
                  padding:
                      const EdgeInsets.symmetric(horizontal: 14, vertical: 11),
                  decoration: BoxDecoration(
                    color: colors.card,
                    borderRadius: BorderRadius.circular(13),
                    border: Border.all(color: colors.border),
                  ),
                  child: Row(
                    children: [
                      Expanded(
                        child: _TotalCell(
                          label: 'Ingresos',
                          value: state.fmtBase(data.totals.income),
                          color: colors.green,
                        ),
                      ),
                      Container(width: 1, height: 30, color: colors.border),
                      Expanded(
                        child: _TotalCell(
                          label: 'Gastos',
                          value: state.fmtBase(data.totals.expense),
                          color: colors.red,
                        ),
                      ),
                      Container(width: 1, height: 30, color: colors.border),
                      Expanded(
                        child: _TotalCell(
                          label: 'Neto',
                          value: state.fmtBase(data.totals.net, plus: true),
                          color:
                              data.totals.net < 0 ? colors.red : colors.green,
                        ),
                      ),
                    ],
                  ),
                ),
              ),
              const SizedBox(height: 4),
              Expanded(
                child: data.items.isEmpty
                    ? ListView(
                        children: [
                          EmptyState(
                            icon: Icons.receipt_long_outlined,
                            title: _query.isEmpty &&
                                    _kind == null &&
                                    _accountId == null
                                ? 'Sin movimientos'
                                : 'Sin resultados',
                            message: _query.isEmpty &&
                                    _kind == null &&
                                    _accountId == null
                                ? 'Registra tu primer movimiento con el botón +.'
                                : 'Prueba con otros filtros o cambia la búsqueda.',
                          ),
                        ],
                      )
                    : ListView.builder(
                        padding: const EdgeInsets.fromLTRB(16, 8, 16, 96),
                        itemCount: data.items.length + 1,
                        itemBuilder: (context, index) {
                          if (index == data.items.length) {
                            return Padding(
                              padding: const EdgeInsets.only(top: 10),
                              child: Center(
                                child: data.items.length >= data.count
                                    ? Text(
                                        '${data.count} movimiento(s)',
                                        style: TextStyle(
                                          fontSize: 11.5,
                                          color: colors.subtle,
                                        ),
                                      )
                                    : OutlinedButton(
                                        onPressed: () =>
                                            setState(() => _limit += 60),
                                        child: const Text('Cargar más'),
                                      ),
                              ),
                            );
                          }
                          final tx = data.items[index];
                          final previous =
                              index == 0 ? null : data.items[index - 1].date;
                          final showDate = previous != tx.date;
                          return Column(
                            children: [
                              if (showDate)
                                Padding(
                                  padding: EdgeInsets.only(
                                    top: index == 0 ? 2 : 14,
                                    bottom: 2,
                                  ),
                                  child: Row(
                                    children: [
                                      Text(
                                        fmtDate(tx.date),
                                        style: TextStyle(
                                          fontSize: 11,
                                          fontWeight: FontWeight.w700,
                                          color: colors.muted,
                                        ),
                                      ),
                                      const SizedBox(width: 8),
                                      Expanded(
                                          child: Divider(color: colors.border)),
                                    ],
                                  ),
                                ),
                              TransactionTile(
                                tx: tx,
                                onTap: () =>
                                    showTransactionEditor(context, tx: tx),
                              ),
                            ],
                          );
                        },
                      ),
              ),
            ],
          );
        },
      ),
    );
  }
}

class _FilterChip extends StatelessWidget {
  const _FilterChip({
    required this.label,
    required this.active,
    required this.onTap,
    this.color,
  });

  final String label;
  final bool active;
  final VoidCallback onTap;
  final Color? color;

  @override
  Widget build(BuildContext context) {
    final colors = FinColors.of(context);
    final accent = color ?? colors.primary;
    return Padding(
      padding: const EdgeInsets.only(right: 6),
      child: InkWell(
        borderRadius: BorderRadius.circular(999),
        onTap: onTap,
        child: Container(
          padding: const EdgeInsets.symmetric(horizontal: 12, vertical: 6),
          decoration: BoxDecoration(
            color: active ? accent.withValues(alpha: 0.13) : colors.card,
            borderRadius: BorderRadius.circular(999),
            border: Border.all(
              color: active ? accent.withValues(alpha: 0.4) : colors.border,
            ),
          ),
          child: Text(
            label,
            style: TextStyle(
              fontSize: 11.5,
              fontWeight: FontWeight.w600,
              color: active ? accent : colors.muted,
            ),
          ),
        ),
      ),
    );
  }
}

class _TotalCell extends StatelessWidget {
  const _TotalCell({
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
      children: [
        Text(
          label,
          style: TextStyle(fontSize: 10.5, color: colors.muted),
        ),
        const SizedBox(height: 2),
        FittedBox(
          fit: BoxFit.scaleDown,
          child: Text(
            value,
            style: TextStyle(
              fontSize: 13,
              fontWeight: FontWeight.w700,
              color: color,
            ),
          ),
        ),
      ],
    );
  }
}

// ---------------------------------------------------------------- formulario

class TransactionEditor extends StatefulWidget {
  const TransactionEditor({super.key, this.tx, this.initialKind});

  final Tx? tx;
  final String? initialKind;

  @override
  State<TransactionEditor> createState() => _TransactionEditorState();
}

class _TransactionEditorState extends State<TransactionEditor> {
  final _amount = TextEditingController();
  final _description = TextEditingController();
  final _notes = TextEditingController();
  late String _kind;
  String _date = todayIso();
  int? _accountId;
  int? _toAccountId;
  int? _categoryId;
  bool _loading = true;
  bool _started = false;
  bool _saving = false;
  String? _error;
  List<AccountBalance> _accounts = [];
  List<Category> _income = [];
  List<Category> _expense = [];

  bool get _editing => widget.tx != null;

  @override
  void initState() {
    super.initState();
    final tx = widget.tx;
    _kind = tx?.kind ?? widget.initialKind ?? 'egreso';
    _date = tx?.date ?? todayIso();
    _accountId = tx?.accountId;
    _toAccountId = tx?.transferAccountId;
    _categoryId = tx?.categoryId;
    if (tx != null) {
      _amount.text = moneyInput(tx.amount);
      _description.text = tx.description;
      _notes.text = tx.notes;
    }
  }

  @override
  void didChangeDependencies() {
    super.didChangeDependencies();
    if (_started) return;
    _started = true;
    _load();
  }

  @override
  void dispose() {
    _amount.dispose();
    _description.dispose();
    _notes.dispose();
    super.dispose();
  }

  Future<void> _load() async {
    final db = AppScope.of(context).db;
    final accounts = await db.accountBalances();
    final income = await db.categories('ingreso');
    final expense = await db.categories('egreso');
    if (!mounted) return;
    setState(() {
      _accounts = accounts;
      _income = income;
      _expense = expense;
      _accountId ??= accounts.isEmpty ? null : accounts.first.id;
      _toAccountId ??= accounts.length > 1 ? accounts[1].id : null;
      _loading = false;
    });
  }

  List<Category> get _categories => _kind == 'ingreso' ? _income : _expense;

  AccountBalance? get _account {
    for (final account in _accounts) {
      if (account.id == _accountId) return account;
    }
    return null;
  }

  String _currencyOf(AccountBalance? account) =>
      account == null || account.currency.isEmpty
          ? AppScope.of(context).db.baseCurrency
          : account.currency;

  Future<void> _pickDate() async {
    final initial = DateTime.tryParse(_date) ?? DateTime.now();
    final picked = await showDatePicker(
      context: context,
      initialDate: initial,
      firstDate: DateTime(2000),
      lastDate: DateTime(2100),
      helpText: 'Fecha del movimiento',
      cancelText: 'Cancelar',
      confirmText: 'Aceptar',
    );
    if (picked != null) setState(() => _date = isoDate(picked));
  }

  Future<void> _save() async {
    final state = AppScope.of(context);
    final db = state.db;
    final cents = parseAmount(_amount.text);
    if (cents == null) {
      setState(() => _error = 'Escribe un monto válido, por ejemplo 1250.50');
      return;
    }
    if (_accountId == null) {
      setState(() => _error = 'Elige la cuenta del movimiento.');
      return;
    }
    if (_kind == 'transferencia' &&
        (_toAccountId == null || _toAccountId == _accountId)) {
      setState(() => _error = 'Elige una cuenta de destino distinta.');
      return;
    }
    setState(() {
      _saving = true;
      _error = null;
    });
    try {
      final categoryId = _kind == 'transferencia' ? null : _categoryId;
      if (_editing) {
        await db.updateTransaction(
          widget.tx!.id,
          date: _date,
          kind: _kind,
          amount: cents,
          categoryId: categoryId,
          accountId: _accountId,
          transferAccountId: _kind == 'transferencia' ? _toAccountId : null,
          description: _description.text,
          notes: _notes.text,
          recurringId: widget.tx!.recurringId,
        );
      } else {
        await db.addTransaction(
          date: _date,
          kind: _kind,
          amount: cents,
          categoryId: categoryId,
          accountId: _accountId,
          transferAccountId: _kind == 'transferencia' ? _toAccountId : null,
          description: _description.text,
          notes: _notes.text,
        );
      }
      state.bump();
      if (mounted) Navigator.pop(context, true);
    } catch (error) {
      if (!mounted) return;
      setState(() {
        _saving = false;
        _error = '$error';
      });
    }
  }

  Future<void> _delete() async {
    final state = AppScope.of(context);
    final ok = await confirmAction(
      context,
      title: 'Eliminar movimiento',
      message:
          '¿Seguro que quieres eliminar este movimiento? No se puede deshacer.',
      confirmLabel: 'Eliminar',
      destructive: true,
    );
    if (!ok) return;
    await state.db.deleteTransaction(widget.tx!.id);
    state.bump();
    if (mounted) Navigator.pop(context, true);
  }

  @override
  Widget build(BuildContext context) {
    final colors = FinColors.of(context);
    final state = AppScope.of(context);
    final height = MediaQuery.sizeOf(context).height * 0.9;
    final account = _account;
    final cents = parseAmount(_amount.text, allowZero: true);
    return Padding(
      padding: EdgeInsets.only(bottom: MediaQuery.viewInsetsOf(context).bottom),
      child: ConstrainedBox(
        constraints: BoxConstraints(maxHeight: height),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            const SizedBox(height: 8),
            Container(
              width: 38,
              height: 4,
              decoration: BoxDecoration(
                color: colors.borderStrong,
                borderRadius: BorderRadius.circular(999),
              ),
            ),
            Padding(
              padding: const EdgeInsets.fromLTRB(18, 10, 8, 4),
              child: Row(
                children: [
                  Expanded(
                    child: Text(
                      _editing ? 'Editar movimiento' : 'Nuevo movimiento',
                      style: TextStyle(
                        fontSize: 17,
                        fontWeight: FontWeight.w800,
                        color: colors.text,
                      ),
                    ),
                  ),
                  if (_editing)
                    IconButton(
                      tooltip: 'Eliminar',
                      onPressed: _saving ? null : _delete,
                      icon: Icon(Icons.delete_outline, color: colors.red),
                    ),
                  IconButton(
                    tooltip: 'Cerrar',
                    onPressed: () => Navigator.pop(context),
                    icon: const Icon(Icons.close),
                  ),
                ],
              ),
            ),
            Flexible(
              child: _loading
                  ? const Padding(
                      padding: EdgeInsets.all(40),
                      child: CircularProgressIndicator(strokeWidth: 2.4),
                    )
                  : SingleChildScrollView(
                      padding: const EdgeInsets.fromLTRB(18, 8, 18, 16),
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          SegmentedButton<String>(
                            segments: const [
                              ButtonSegment(
                                value: 'ingreso',
                                label: Text('Ingreso'),
                                icon: Icon(Icons.south_west, size: 16),
                              ),
                              ButtonSegment(
                                value: 'egreso',
                                label: Text('Gasto'),
                                icon: Icon(Icons.north_east, size: 16),
                              ),
                              ButtonSegment(
                                value: 'transferencia',
                                label: Text('Transferir'),
                                icon: Icon(Icons.swap_horiz, size: 16),
                              ),
                            ],
                            selected: {_kind},
                            showSelectedIcon: false,
                            onSelectionChanged: (value) => setState(() {
                              _kind = value.first;
                              _categoryId = null;
                              _error = null;
                            }),
                          ),
                          const SizedBox(height: 16),
                          LabeledField(
                            label: 'Monto (${_currencyOf(account)})',
                            child: TextField(
                              controller: _amount,
                              keyboardType:
                                  const TextInputType.numberWithOptions(
                                decimal: true,
                              ),
                              autofocus: !_editing,
                              onChanged: (_) => setState(() {}),
                              style: const TextStyle(
                                fontSize: 22,
                                fontWeight: FontWeight.w700,
                              ),
                              decoration: InputDecoration(
                                prefixText:
                                    '${currencySymbol(_currencyOf(account), state.symbol)} ',
                                hintText: '0.00',
                                prefixStyle: TextStyle(
                                  fontSize: 20,
                                  fontWeight: FontWeight.w600,
                                  color: colors.muted,
                                ),
                              ),
                            ),
                          ),
                          if (cents != null &&
                              cents > 0 &&
                              state.isConverted &&
                              _kind != 'transferencia')
                            Padding(
                              padding: const EdgeInsets.only(top: 6),
                              child: Text(
                                '≈ ${state.fmtFrom(cents, _currencyOf(account), date: _date)}',
                                style: TextStyle(
                                  fontSize: 11.5,
                                  color: colors.muted,
                                ),
                              ),
                            ),
                          const SizedBox(height: 14),
                          LabeledField(
                            label: 'Fecha',
                            child: InkWell(
                              borderRadius: BorderRadius.circular(12),
                              onTap: _pickDate,
                              child: Container(
                                padding: const EdgeInsets.symmetric(
                                  horizontal: 14,
                                  vertical: 13,
                                ),
                                decoration: BoxDecoration(
                                  color: colors.cardSoft,
                                  borderRadius: BorderRadius.circular(12),
                                  border: Border.all(color: colors.border),
                                ),
                                child: Row(
                                  children: [
                                    Icon(Icons.event,
                                        size: 18, color: colors.muted),
                                    const SizedBox(width: 8),
                                    Text(
                                      fmtDate(_date),
                                      style: TextStyle(
                                        fontSize: 14,
                                        color: colors.text,
                                      ),
                                    ),
                                    const Spacer(),
                                    Icon(Icons.expand_more,
                                        size: 18, color: colors.subtle),
                                  ],
                                ),
                              ),
                            ),
                          ),
                          const SizedBox(height: 14),
                          LabeledField(
                            label: _kind == 'transferencia'
                                ? 'Cuenta de origen'
                                : 'Cuenta',
                            child: DropdownButtonFormField<int>(
                              initialValue: _accountId,
                              isExpanded: true,
                              hint: const Text('Elige una cuenta'),
                              items: [
                                for (final item in _accounts)
                                  DropdownMenuItem<int>(
                                    value: item.id,
                                    child: Text(
                                      item.currency.isEmpty
                                          ? item.name
                                          : '${item.name} · ${item.currency}',
                                      overflow: TextOverflow.ellipsis,
                                    ),
                                  ),
                              ],
                              onChanged: (value) =>
                                  setState(() => _accountId = value),
                            ),
                          ),
                          if (_kind == 'transferencia') ...[
                            const SizedBox(height: 14),
                            LabeledField(
                              label: 'Cuenta de destino',
                              child: DropdownButtonFormField<int>(
                                initialValue: _toAccountId,
                                isExpanded: true,
                                hint: const Text('Elige la cuenta destino'),
                                items: [
                                  for (final item in _accounts)
                                    DropdownMenuItem<int>(
                                      value: item.id,
                                      child: Text(
                                        item.currency.isEmpty
                                            ? item.name
                                            : '${item.name} · ${item.currency}',
                                        overflow: TextOverflow.ellipsis,
                                      ),
                                    ),
                                ],
                                onChanged: (value) =>
                                    setState(() => _toAccountId = value),
                              ),
                            ),
                            if (cents != null && cents > 0)
                              Padding(
                                padding: const EdgeInsets.only(top: 6),
                                child: Text(
                                  'Se acreditarán '
                                  '${state.fmtFrom(
                                    cents,
                                    _currencyOf(account),
                                    date: _date,
                                  )} en la cuenta destino.',
                                  style: TextStyle(
                                    fontSize: 11.5,
                                    color: colors.muted,
                                  ),
                                ),
                              ),
                          ] else ...[
                            const SizedBox(height: 14),
                            LabeledField(
                              label: 'Categoría (opcional)',
                              child: DropdownButtonFormField<int?>(
                                key: ValueKey('category-$_kind'),
                                initialValue: _categoryId,
                                isExpanded: true,
                                hint: const Text('Sin categoría'),
                                items: [
                                  const DropdownMenuItem<int?>(
                                    value: null,
                                    child: Text('Sin categoría'),
                                  ),
                                  for (final item in _categories)
                                    DropdownMenuItem<int?>(
                                      value: item.id,
                                      child: Row(
                                        children: [
                                          ColorDot(hexColor(item.color),
                                              size: 8),
                                          const SizedBox(width: 7),
                                          Expanded(
                                            child: Text(
                                              item.name,
                                              overflow: TextOverflow.ellipsis,
                                            ),
                                          ),
                                        ],
                                      ),
                                    ),
                                ],
                                onChanged: (value) =>
                                    setState(() => _categoryId = value),
                              ),
                            ),
                          ],
                          const SizedBox(height: 14),
                          LabeledField(
                            label: 'Descripción',
                            child: TextField(
                              controller: _description,
                              textCapitalization: TextCapitalization.sentences,
                              decoration: const InputDecoration(
                                hintText: 'Ej. Supermercado, nómina…',
                              ),
                            ),
                          ),
                          const SizedBox(height: 14),
                          LabeledField(
                            label: 'Notas',
                            child: TextField(
                              controller: _notes,
                              minLines: 2,
                              maxLines: 4,
                              textCapitalization: TextCapitalization.sentences,
                              decoration: const InputDecoration(
                                hintText: 'Detalle opcional',
                              ),
                            ),
                          ),
                          if (_error != null)
                            Padding(
                              padding: const EdgeInsets.only(top: 12),
                              child: Text(
                                _error!,
                                style: TextStyle(
                                    fontSize: 12.5, color: colors.red),
                              ),
                            ),
                        ],
                      ),
                    ),
            ),
            Container(
              padding: EdgeInsets.fromLTRB(
                18,
                10,
                18,
                12 + MediaQuery.paddingOf(context).bottom,
              ),
              decoration: BoxDecoration(
                border: Border(top: BorderSide(color: colors.border)),
              ),
              child: Row(
                children: [
                  Expanded(
                    child: OutlinedButton(
                      onPressed: _saving ? null : () => Navigator.pop(context),
                      child: const Text('Cancelar'),
                    ),
                  ),
                  const SizedBox(width: 10),
                  Expanded(
                    flex: 2,
                    child: FilledButton.icon(
                      onPressed: _saving || _loading ? null : _save,
                      icon: _saving
                          ? const SizedBox(
                              width: 16,
                              height: 16,
                              child: CircularProgressIndicator(
                                strokeWidth: 2,
                                color: Colors.white,
                              ),
                            )
                          : const Icon(Icons.check, size: 18),
                      label: Text(_editing ? 'Guardar cambios' : 'Guardar'),
                    ),
                  ),
                ],
              ),
            ),
          ],
        ),
      ),
    );
  }
}
