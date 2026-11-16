import 'package:flutter/material.dart';

import '../../data/models.dart';
import '../../data/utils.dart';
import '../theme.dart';
import '../widgets.dart';
import 'transactions.dart';

const Map<String, (String, IconData)> accountKinds = {
  'efectivo': ('Efectivo', Icons.payments_outlined),
  'banco': ('Banco', Icons.account_balance_outlined),
  'tarjeta': ('Tarjeta', Icons.credit_card),
  'ahorro': ('Ahorro', Icons.savings_outlined),
  'inversion': ('Inversión', Icons.trending_up),
};

class AccountsScreen extends StatelessWidget {
  const AccountsScreen({super.key});

  Future<List<AccountBalance>> _load(BuildContext context) =>
      AppScope.of(context).db.accountBalances();

  @override
  Widget build(BuildContext context) {
    final state = AppScope.of(context);
    return ScreenBody(
      fab: FloatingActionButton(
        heroTag: 'accounts_add',
        onPressed: () => showAccountEditor(context),
        child: const Icon(Icons.add),
      ),
      child: DbFutureBuilder<List<AccountBalance>>(
        load: () => _load(context),
        builder: (context, accounts) {
          final total = accounts.fold<int>(
            0,
            (sum, account) => sum + account.baseBalance,
          );
          return ListView(
            padding: const EdgeInsets.fromLTRB(16, 8, 16, 96),
            children: [
              Container(
                padding: const EdgeInsets.all(16),
                decoration: BoxDecoration(
                  color: FinColors.of(context).card,
                  borderRadius: BorderRadius.circular(16),
                  border: Border.all(color: FinColors.of(context).border),
                ),
                child: Row(
                  children: [
                    Expanded(
                      child: Column(
                        crossAxisAlignment: CrossAxisAlignment.start,
                        children: [
                          Text(
                            'Patrimonio',
                            style: TextStyle(
                              fontSize: 12,
                              color: FinColors.of(context).muted,
                            ),
                          ),
                          const SizedBox(height: 4),
                          FittedBox(
                            fit: BoxFit.scaleDown,
                            alignment: Alignment.centerLeft,
                            child: Text(
                              state.fmtBase(total),
                              style: TextStyle(
                                fontSize: 24,
                                fontWeight: FontWeight.w800,
                                color: FinColors.of(context).text,
                              ),
                            ),
                          ),
                          const SizedBox(height: 2),
                          Text(
                            '${accounts.length} cuenta(s) · ${state.shownCurrency}',
                            style: TextStyle(
                              fontSize: 11.5,
                              color: FinColors.of(context).subtle,
                            ),
                          ),
                        ],
                      ),
                    ),
                    OutlinedButton.icon(
                      onPressed: () => showTransferEditor(context),
                      icon: const Icon(Icons.swap_horiz, size: 17),
                      label: const Text('Transferir'),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 14),
              if (accounts.isEmpty)
                const EmptyState(
                  icon: Icons.account_balance_wallet_outlined,
                  title: 'Sin cuentas',
                  message: 'Añade una cuenta con el botón +.',
                )
              else
                for (final account in accounts) ...[
                  _AccountCard(
                    account: account,
                    onTap: () => showAccountEditor(context, account: account),
                    onTransfer: () => showTransferEditor(context),
                  ),
                  const SizedBox(height: 10),
                ],
              const SizedBox(height: 4),
              Container(
                padding: const EdgeInsets.all(13),
                decoration: BoxDecoration(
                  color: FinColors.of(context).cardSoft,
                  borderRadius: BorderRadius.circular(12),
                  border: Border.all(color: FinColors.of(context).border),
                ),
                child: Text(
                  'Las cuentas en otra moneda se convierten a '
                  '${state.shownCurrency} con la tasa más reciente. '
                  'Registra las tasas en Ajustes.',
                  style: TextStyle(
                    fontSize: 11.5,
                    color: FinColors.of(context).muted,
                  ),
                ),
              ),
            ],
          );
        },
      ),
    );
  }
}

class _AccountCard extends StatelessWidget {
  const _AccountCard({
    required this.account,
    required this.onTap,
    required this.onTransfer,
  });

  final AccountBalance account;
  final VoidCallback onTap;
  final VoidCallback onTransfer;

  @override
  Widget build(BuildContext context) {
    final colors = FinColors.of(context);
    final state = AppScope.of(context);
    final accent = hexColor(account.color);
    final kind = accountKinds[account.kind] ?? accountKinds['efectivo']!;
    final isForeign = account.currency.isNotEmpty &&
        account.currency.toUpperCase() != state.db.baseCurrency;
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(16),
      child: Container(
        padding: const EdgeInsets.all(14),
        decoration: BoxDecoration(
          color: colors.card,
          borderRadius: BorderRadius.circular(16),
          border: Border.all(color: colors.border),
        ),
        child: Column(
          children: [
            Row(
              children: [
                Container(
                  width: 40,
                  height: 40,
                  decoration: BoxDecoration(
                    color: accent.withValues(alpha: 0.13),
                    borderRadius: BorderRadius.circular(12),
                  ),
                  child: Icon(kind.$2, size: 20, color: accent),
                ),
                const SizedBox(width: 11),
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Row(
                        children: [
                          Flexible(
                            child: Text(
                              account.name,
                              maxLines: 1,
                              overflow: TextOverflow.ellipsis,
                              style: TextStyle(
                                fontSize: 14.5,
                                fontWeight: FontWeight.w700,
                                color: colors.text,
                              ),
                            ),
                          ),
                          if (isForeign) ...[
                            const SizedBox(width: 6),
                            Container(
                              padding: const EdgeInsets.symmetric(
                                horizontal: 6,
                                vertical: 1,
                              ),
                              decoration: BoxDecoration(
                                color: colors.purpleSoft,
                                borderRadius: BorderRadius.circular(5),
                              ),
                              child: Text(
                                account.currency,
                                style: TextStyle(
                                  fontSize: 9.5,
                                  fontWeight: FontWeight.w800,
                                  color: colors.purple,
                                ),
                              ),
                            ),
                          ],
                        ],
                      ),
                      const SizedBox(height: 2),
                      Text(
                        kind.$1,
                        style: TextStyle(fontSize: 11, color: colors.muted),
                      ),
                    ],
                  ),
                ),
                Column(
                  crossAxisAlignment: CrossAxisAlignment.end,
                  children: [
                    AccountMoneyText(
                      account.balance,
                      currency: account.currency,
                      size: 15.5,
                      color: account.balance < 0 ? colors.red : colors.text,
                    ),
                    if (isForeign)
                      Padding(
                        padding: const EdgeInsets.only(top: 2),
                        child: Text(
                          money(
                            account.balance,
                            symbol: currencySymbol(
                              account.currency,
                              state.symbol,
                            ),
                          ),
                          style:
                              TextStyle(fontSize: 10.5, color: colors.subtle),
                        ),
                      ),
                  ],
                ),
              ],
            ),
            const SizedBox(height: 10),
            Row(
              children: [
                Expanded(
                  child: _AccountAction(
                    icon: Icons.edit_outlined,
                    label: 'Editar',
                    onTap: onTap,
                  ),
                ),
                Container(width: 1, height: 18, color: colors.border),
                Expanded(
                  child: _AccountAction(
                    icon: Icons.swap_horiz,
                    label: 'Transferir',
                    onTap: onTransfer,
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

class _AccountAction extends StatelessWidget {
  const _AccountAction({
    required this.icon,
    required this.label,
    required this.onTap,
  });

  final IconData icon;
  final String label;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final colors = FinColors.of(context);
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(8),
      child: Padding(
        padding: const EdgeInsets.symmetric(vertical: 5),
        child: Row(
          mainAxisAlignment: MainAxisAlignment.center,
          children: [
            Icon(icon, size: 14, color: colors.muted),
            const SizedBox(width: 5),
            Text(
              label,
              style: TextStyle(fontSize: 11.5, color: colors.muted),
            ),
          ],
        ),
      ),
    );
  }
}

Future<void> showAccountEditor(
  BuildContext context, {
  AccountBalance? account,
}) {
  return showModalBottomSheet<void>(
    context: context,
    isScrollControlled: true,
    useSafeArea: true,
    builder: (_) => AccountEditor(account: account),
  );
}

class AccountEditor extends StatefulWidget {
  const AccountEditor({super.key, this.account});

  final AccountBalance? account;

  @override
  State<AccountEditor> createState() => _AccountEditorState();
}

class _AccountEditorState extends State<AccountEditor> {
  final _name = TextEditingController();
  final _initial = TextEditingController();
  final _currency = TextEditingController();
  String _kind = 'efectivo';
  String _color = '#6366f1';
  bool _saving = false;
  String? _error;

  @override
  void initState() {
    super.initState();
    final account = widget.account;
    if (account != null) {
      _name.text = account.name;
      _initial.text = moneyInput(account.initialBalance);
      _currency.text = account.currency;
      _kind = account.kind;
      _color = account.color.isEmpty ? '#6366f1' : account.color;
    }
  }

  @override
  void dispose() {
    _name.dispose();
    _initial.dispose();
    _currency.dispose();
    super.dispose();
  }

  Future<void> _save() async {
    final state = AppScope.of(context);
    final db = state.db;
    if (_name.text.trim().isEmpty) {
      setState(() => _error = 'Escribe el nombre de la cuenta.');
      return;
    }
    final initial = _initial.text.trim().isEmpty
        ? 0
        : parseAmount(_initial.text, allowZero: true);
    if (initial == null) {
      setState(() => _error = 'El saldo inicial no es válido.');
      return;
    }
    String currency;
    try {
      currency = normalizeCurrency(_currency.text);
    } on FormatException catch (error) {
      setState(() => _error = error.message);
      return;
    }
    setState(() {
      _saving = true;
      _error = null;
    });
    try {
      if (widget.account == null) {
        await db.addAccount(
          name: _name.text,
          kind: _kind,
          initialBalance: initial,
          color: _color,
          currency: currency,
        );
      } else {
        await db.updateAccount(
          widget.account!.id,
          name: _name.text,
          kind: _kind,
          initialBalance: initial,
          color: _color,
          currency: currency,
        );
      }
      state.bump();
      if (mounted) Navigator.pop(context);
    } catch (error) {
      if (!mounted) return;
      setState(() {
        _saving = false;
        _error = 'No se pudo guardar: $error';
      });
    }
  }

  Future<void> _delete() async {
    final state = AppScope.of(context);
    final db = state.db;
    final usage = await db.accountUsage(widget.account!.id);
    if (usage > 0) {
      if (!mounted) return;
      setState(() =>
          _error = 'No puedes eliminar una cuenta con $usage movimiento(s).');
      return;
    }
    if (!mounted) return;
    final ok = await confirmAction(
      context,
      title: 'Eliminar cuenta',
      message: '¿Eliminar «${widget.account!.name}»?',
      confirmLabel: 'Eliminar',
      destructive: true,
    );
    if (!ok) return;
    await db.deleteAccount(widget.account!.id);
    state.bump();
    if (mounted) Navigator.pop(context);
  }

  @override
  Widget build(BuildContext context) {
    final colors = FinColors.of(context);
    final state = AppScope.of(context);
    return Padding(
      padding: EdgeInsets.only(bottom: MediaQuery.viewInsetsOf(context).bottom),
      child: ConstrainedBox(
        constraints: BoxConstraints(
          maxHeight: MediaQuery.sizeOf(context).height * 0.9,
        ),
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
                      widget.account == null ? 'Nueva cuenta' : 'Editar cuenta',
                      style: TextStyle(
                        fontSize: 17,
                        fontWeight: FontWeight.w800,
                        color: colors.text,
                      ),
                    ),
                  ),
                  if (widget.account != null)
                    IconButton(
                      onPressed: _delete,
                      icon: Icon(Icons.delete_outline, color: colors.red),
                    ),
                  IconButton(
                    onPressed: () => Navigator.pop(context),
                    icon: const Icon(Icons.close),
                  ),
                ],
              ),
            ),
            Flexible(
              child: SingleChildScrollView(
                padding: const EdgeInsets.fromLTRB(18, 8, 18, 16),
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    LabeledField(
                      label: 'Nombre',
                      child: TextField(
                        controller: _name,
                        textCapitalization: TextCapitalization.sentences,
                        decoration: const InputDecoration(
                          hintText: 'Ej. Cuenta bancaria',
                        ),
                      ),
                    ),
                    const SizedBox(height: 14),
                    LabeledField(
                      label: 'Tipo',
                      child: DropdownButtonFormField<String>(
                        initialValue: _kind,
                        isExpanded: true,
                        items: [
                          for (final entry in accountKinds.entries)
                            DropdownMenuItem(
                              value: entry.key,
                              child: Text(entry.value.$1),
                            ),
                        ],
                        onChanged: (value) =>
                            setState(() => _kind = value ?? 'efectivo'),
                      ),
                    ),
                    const SizedBox(height: 14),
                    LabeledField(
                      label: 'Saldo inicial',
                      help:
                          'Puede ser negativo, por ejemplo la deuda de una tarjeta.',
                      child: TextField(
                        controller: _initial,
                        keyboardType: const TextInputType.numberWithOptions(
                          decimal: true,
                        ),
                        decoration: InputDecoration(
                          hintText: '0.00',
                          prefixText: '${currencySymbol(
                            normalizeOrBase(
                                _currency.text, state.db.baseCurrency),
                            state.symbol,
                          )} ',
                        ),
                      ),
                    ),
                    const SizedBox(height: 14),
                    LabeledField(
                      label: 'Moneda de la cuenta (opcional)',
                      help: 'Deja vacío para usar la moneda base '
                          '(${state.db.baseCurrency}). Usa el código ISO, por ejemplo USD.',
                      child: TextField(
                        controller: _currency,
                        textCapitalization: TextCapitalization.characters,
                        maxLength: 3,
                        onChanged: (_) => setState(() {}),
                        decoration: const InputDecoration(
                          hintText: 'MXN',
                          counterText: '',
                        ),
                      ),
                    ),
                    const SizedBox(height: 8),
                    LabeledField(
                      label: 'Color',
                      child: ColorPickerRow(
                        selected: _color,
                        onChanged: (value) => setState(() => _color = value),
                      ),
                    ),
                    if (_error != null)
                      Padding(
                        padding: const EdgeInsets.only(top: 12),
                        child: Text(
                          _error!,
                          style: TextStyle(fontSize: 12.5, color: colors.red),
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
                    child: FilledButton(
                      onPressed: _saving ? null : _save,
                      child: Text(
                          widget.account == null ? 'Crear cuenta' : 'Guardar'),
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

String normalizeOrBase(String raw, String base) {
  final value = raw.trim().toUpperCase();
  return value.isEmpty ? base : value;
}
