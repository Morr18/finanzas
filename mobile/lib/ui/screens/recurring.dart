import 'package:flutter/material.dart';

import '../../data/models.dart';
import '../../data/utils.dart';
import '../theme.dart';
import '../widgets.dart';

class RecurringScreen extends StatelessWidget {
  const RecurringScreen({super.key});

  Future<List<RecurringRule>> _load(BuildContext context) =>
      AppScope.of(context).db.recurring();

  Future<void> _process(BuildContext context) async {
    final state = AppScope.of(context);
    final created = await state.db.processRecurring();
    state.bump();
    if (!context.mounted) return;
    showMessage(
      context,
      created == 0
          ? 'No había movimientos pendientes por generar.'
          : 'Se generaron $created movimientos.',
    );
  }

  @override
  Widget build(BuildContext context) {
    final colors = FinColors.of(context);
    return ScreenBody(
      fab: FloatingActionButton(
        heroTag: 'recurring_add',
        onPressed: () => showRecurringEditor(context),
        child: const Icon(Icons.add),
      ),
      child: DbFutureBuilder<List<RecurringRule>>(
        load: () => _load(context),
        builder: (context, rules) {
          final active = rules.where((rule) => rule.active).length;
          return ListView(
            padding: const EdgeInsets.fromLTRB(16, 8, 16, 96),
            children: [
              Container(
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
                        Icon(Icons.autorenew, size: 18, color: colors.primary),
                        const SizedBox(width: 8),
                        Expanded(
                          child: Text(
                            '$active activa(s) de ${rules.length}',
                            style: TextStyle(
                              fontSize: 13,
                              fontWeight: FontWeight.w700,
                              color: colors.text,
                            ),
                          ),
                        ),
                        FilledButton.tonalIcon(
                          onPressed: () => _process(context),
                          icon: const Icon(Icons.play_arrow, size: 17),
                          label: const Text('Generar'),
                        ),
                      ],
                    ),
                    const SizedBox(height: 6),
                    Text(
                      'Los movimientos recurrentes se crean al abrir la app o al '
                      'pulsar «Generar». No se duplican.',
                      style: TextStyle(fontSize: 11.5, color: colors.muted),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 14),
              if (rules.isEmpty)
                const EmptyState(
                  icon: Icons.autorenew,
                  title: 'Sin movimientos recurrentes',
                  message: 'Automatiza la renta, la nómina o las suscripciones '
                      'con el botón +.',
                )
              else
                for (final rule in rules) ...[
                  _RecurringCard(rule: rule),
                  const SizedBox(height: 9),
                ],
            ],
          );
        },
      ),
    );
  }
}

class _RecurringCard extends StatelessWidget {
  const _RecurringCard({required this.rule});

  final RecurringRule rule;

  @override
  Widget build(BuildContext context) {
    final colors = FinColors.of(context);
    final next = rule.active
        ? nextRecurringDate(rule.toRuleMap(), after: DateTime.now())
        : null;
    final color = rule.kind == 'ingreso'
        ? colors.green
        : rule.kind == 'egreso'
            ? colors.red
            : colors.blue;
    final title = rule.description.trim().isNotEmpty
        ? rule.description.trim()
        : rule.categoryName.isNotEmpty
            ? rule.categoryName
            : 'Movimiento recurrente';
    return InkWell(
      onTap: () => showRecurringEditor(context, rule: rule),
      borderRadius: BorderRadius.circular(14),
      child: Container(
        padding: const EdgeInsets.fromLTRB(13, 12, 6, 12),
        decoration: BoxDecoration(
          color: colors.card,
          borderRadius: BorderRadius.circular(14),
          border: Border.all(color: colors.border),
        ),
        child: Row(
          children: [
            Container(
              width: 36,
              height: 36,
              decoration: BoxDecoration(
                color: color.withValues(alpha: 0.12),
                borderRadius: BorderRadius.circular(10),
              ),
              child: Icon(
                rule.kind == 'ingreso'
                    ? Icons.south_west
                    : rule.kind == 'egreso'
                        ? Icons.north_east
                        : Icons.swap_horiz,
                size: 18,
                color: color,
              ),
            ),
            const SizedBox(width: 10),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    title,
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: TextStyle(
                      fontSize: 13.5,
                      fontWeight: FontWeight.w700,
                      color: rule.active ? colors.text : colors.muted,
                    ),
                  ),
                  const SizedBox(height: 2),
                  Text(
                    '${scheduleText(rule.toRuleMap())} · '
                    '${rule.accountName.isEmpty ? 'Sin cuenta' : rule.accountName}',
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: TextStyle(fontSize: 11, color: colors.muted),
                  ),
                  const SizedBox(height: 2),
                  Text(
                    rule.active
                        ? (next == null
                            ? 'Sin próximas fechas'
                            : 'Próximo: ${fmtDate(next)}')
                        : 'Pausada',
                    style: TextStyle(
                      fontSize: 10.5,
                      color: rule.active ? colors.subtle : colors.amber,
                    ),
                  ),
                ],
              ),
            ),
            Column(
              crossAxisAlignment: CrossAxisAlignment.end,
              children: [
                AccountMoneyText(
                  rule.amount,
                  currency: rule.accountCurrency,
                  plus: rule.kind == 'ingreso',
                  size: 13,
                  color: color,
                ),
                Switch(
                  value: rule.active,
                  materialTapTargetSize: MaterialTapTargetSize.shrinkWrap,
                  onChanged: (value) async {
                    final state = AppScope.of(context);
                    await state.db.setRecurringActive(rule.id, value);
                    state.bump();
                  },
                ),
              ],
            ),
          ],
        ),
      ),
    );
  }
}

Future<void> showRecurringEditor(
  BuildContext context, {
  RecurringRule? rule,
}) {
  return showModalBottomSheet<void>(
    context: context,
    isScrollControlled: true,
    useSafeArea: true,
    builder: (_) => RecurringEditor(rule: rule),
  );
}

class RecurringEditor extends StatefulWidget {
  const RecurringEditor({super.key, this.rule});

  final RecurringRule? rule;

  @override
  State<RecurringEditor> createState() => _RecurringEditorState();
}

class _RecurringEditorState extends State<RecurringEditor> {
  final _description = TextEditingController();
  final _amount = TextEditingController();
  late String _kind;
  String _frequency = 'mensual';
  int _day = 1;
  int _month = 1;
  String _startDate = todayIso();
  int? _accountId;
  int? _toAccountId;
  int? _categoryId;
  bool _active = true;
  bool _loading = true;
  bool _started = false;
  bool _saving = false;
  String? _error;
  List<AccountBalance> _accounts = [];
  List<Category> _income = [];
  List<Category> _expense = [];

  bool get _editing => widget.rule != null;

  @override
  void initState() {
    super.initState();
    final rule = widget.rule;
    _kind = rule?.kind ?? 'egreso';
    _frequency = rule?.frequency ?? 'mensual';
    _day = rule?.day ?? 1;
    _month = rule?.month ?? 1;
    _startDate = rule?.startDate ?? todayIso();
    _accountId = rule?.accountId;
    _toAccountId = rule?.transferAccountId;
    _categoryId = rule?.categoryId;
    _active = rule?.active ?? true;
    if (rule != null) {
      _description.text = rule.description;
      _amount.text = moneyInput(rule.amount);
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
    _description.dispose();
    _amount.dispose();
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

  Future<void> _pickDate() async {
    final initial = DateTime.tryParse(_startDate) ?? DateTime.now();
    final picked = await showDatePicker(
      context: context,
      initialDate: initial,
      firstDate: DateTime(2000),
      lastDate: DateTime(2100),
      helpText: 'Fecha de inicio',
      cancelText: 'Cancelar',
      confirmText: 'Aceptar',
    );
    if (picked != null) setState(() => _startDate = isoDate(picked));
  }

  Future<void> _save() async {
    final state = AppScope.of(context);
    final db = state.db;
    final cents = parseAmount(_amount.text);
    if (cents == null) {
      setState(() => _error = 'Escribe un monto válido.');
      return;
    }
    if (_accountId == null) {
      setState(() => _error = 'Elige la cuenta.');
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
      if (_editing) {
        await db.updateRecurring(
          widget.rule!.id,
          description: _description.text,
          kind: _kind,
          amount: cents,
          categoryId: _kind == 'transferencia' ? null : _categoryId,
          accountId: _accountId,
          transferAccountId: _kind == 'transferencia' ? _toAccountId : null,
          frequency: _frequency,
          day: _day,
          month: _month,
          startDate: _startDate,
          active: _active,
        );
      } else {
        await db.addRecurring(
          description: _description.text,
          kind: _kind,
          amount: cents,
          categoryId: _kind == 'transferencia' ? null : _categoryId,
          accountId: _accountId,
          transferAccountId: _kind == 'transferencia' ? _toAccountId : null,
          frequency: _frequency,
          day: _day,
          month: _month,
          startDate: _startDate,
          active: _active,
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
    final ok = await confirmAction(
      context,
      title: 'Eliminar recurrente',
      message:
          'Los movimientos ya generados se conservan. ¿Eliminar esta regla?',
      confirmLabel: 'Eliminar',
      destructive: true,
    );
    if (!ok) return;
    await state.db.deleteRecurring(widget.rule!.id);
    state.bump();
    if (mounted) Navigator.pop(context);
  }

  @override
  Widget build(BuildContext context) {
    final colors = FinColors.of(context);
    final state = AppScope.of(context);
    final account = _account;
    final currency = account == null || account.currency.isEmpty
        ? state.db.baseCurrency
        : account.currency;
    return Padding(
      padding: EdgeInsets.only(bottom: MediaQuery.viewInsetsOf(context).bottom),
      child: ConstrainedBox(
        constraints: BoxConstraints(
          maxHeight: MediaQuery.sizeOf(context).height * 0.92,
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
                      _editing ? 'Editar recurrente' : 'Nuevo recurrente',
                      style: TextStyle(
                        fontSize: 17,
                        fontWeight: FontWeight.w800,
                        color: colors.text,
                      ),
                    ),
                  ),
                  if (_editing)
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
                              ),
                              ButtonSegment(
                                value: 'egreso',
                                label: Text('Gasto'),
                              ),
                              ButtonSegment(
                                value: 'transferencia',
                                label: Text('Transferir'),
                              ),
                            ],
                            selected: {_kind},
                            showSelectedIcon: false,
                            onSelectionChanged: (value) => setState(() {
                              _kind = value.first;
                              _categoryId = null;
                            }),
                          ),
                          const SizedBox(height: 14),
                          LabeledField(
                            label: 'Descripción',
                            child: TextField(
                              controller: _description,
                              textCapitalization: TextCapitalization.sentences,
                              decoration: const InputDecoration(
                                hintText: 'Ej. Renta, nómina, Netflix…',
                              ),
                            ),
                          ),
                          const SizedBox(height: 14),
                          LabeledField(
                            label: 'Monto ($currency)',
                            child: TextField(
                              controller: _amount,
                              keyboardType:
                                  const TextInputType.numberWithOptions(
                                decimal: true,
                              ),
                              decoration: InputDecoration(
                                hintText: '0.00',
                                prefixText:
                                    '${currencySymbol(currency, state.symbol)} ',
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
                              items: [
                                for (final item in _accounts)
                                  DropdownMenuItem(
                                    value: item.id,
                                    child: Text(
                                      item.currency.isEmpty
                                          ? item.name
                                          : '${item.name} · ${item.currency}',
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
                                items: [
                                  for (final item in _accounts)
                                    DropdownMenuItem(
                                      value: item.id,
                                      child: Text(
                                        item.currency.isEmpty
                                            ? item.name
                                            : '${item.name} · ${item.currency}',
                                      ),
                                    ),
                                ],
                                onChanged: (value) =>
                                    setState(() => _toAccountId = value),
                              ),
                            ),
                          ] else ...[
                            const SizedBox(height: 14),
                            LabeledField(
                              label: 'Categoría (opcional)',
                              child: DropdownButtonFormField<int?>(
                                key: ValueKey('rec-cat-$_kind'),
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
                                      child: Text(item.name),
                                    ),
                                ],
                                onChanged: (value) =>
                                    setState(() => _categoryId = value),
                              ),
                            ),
                          ],
                          const SizedBox(height: 14),
                          LabeledField(
                            label: 'Frecuencia',
                            child: DropdownButtonFormField<String>(
                              initialValue: _frequency,
                              isExpanded: true,
                              items: [
                                for (final entry in frecuenciaLabels.entries)
                                  DropdownMenuItem(
                                    value: entry.key,
                                    child: Text(entry.value),
                                  ),
                              ],
                              onChanged: (value) => setState(() {
                                _frequency = value ?? 'mensual';
                                if (_frequency == 'quincenal') _day = 1;
                              }),
                            ),
                          ),
                          const SizedBox(height: 14),
                          if (_frequency == 'mensual' || _frequency == 'anual')
                            LabeledField(
                              label: 'Día del mes',
                              child: DropdownButtonFormField<int>(
                                initialValue: _day.clamp(1, 31),
                                isExpanded: true,
                                items: [
                                  for (var day = 1; day <= 31; day++)
                                    DropdownMenuItem(
                                      value: day,
                                      child: Text('Día $day'),
                                    ),
                                ],
                                onChanged: (value) =>
                                    setState(() => _day = value ?? 1),
                              ),
                            ),
                          if (_frequency == 'anual') ...[
                            const SizedBox(height: 14),
                            LabeledField(
                              label: 'Mes',
                              child: DropdownButtonFormField<int>(
                                initialValue: _month.clamp(1, 12),
                                isExpanded: true,
                                items: [
                                  for (var index = 0; index < 12; index++)
                                    DropdownMenuItem(
                                      value: index + 1,
                                      child: Text(meses[index]),
                                    ),
                                ],
                                onChanged: (value) =>
                                    setState(() => _month = value ?? 1),
                              ),
                            ),
                          ],
                          if (_frequency == 'semanal') ...[
                            const SizedBox(height: 14),
                            LabeledField(
                              label: 'Día de la semana',
                              child: DropdownButtonFormField<int>(
                                initialValue: _day.clamp(0, 6),
                                isExpanded: true,
                                items: [
                                  for (var index = 0; index < 7; index++)
                                    DropdownMenuItem(
                                      value: index,
                                      child: Text(diasSemana[index]),
                                    ),
                                ],
                                onChanged: (value) =>
                                    setState(() => _day = value ?? 0),
                              ),
                            ),
                          ],
                          if (_frequency == 'quincenal')
                            Padding(
                              padding: const EdgeInsets.only(top: 8),
                              child: Text(
                                'Se genera los días 1 y 16 de cada mes.',
                                style: TextStyle(
                                  fontSize: 11.5,
                                  color: colors.muted,
                                ),
                              ),
                            ),
                          const SizedBox(height: 14),
                          LabeledField(
                            label: 'Fecha de inicio',
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
                                      fmtDate(_startDate),
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
                          const SizedBox(height: 6),
                          SwitchListTile(
                            contentPadding: EdgeInsets.zero,
                            value: _active,
                            title: const Text(
                              'Activa',
                              style: TextStyle(fontSize: 13.5),
                            ),
                            subtitle: Text(
                              'Si está pausada no se generan movimientos.',
                              style:
                                  TextStyle(fontSize: 11, color: colors.muted),
                            ),
                            onChanged: (value) =>
                                setState(() => _active = value),
                          ),
                          if (_error != null)
                            Padding(
                              padding: const EdgeInsets.only(top: 8),
                              child: Text(
                                _error!,
                                style: TextStyle(
                                  fontSize: 12.5,
                                  color: colors.red,
                                ),
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
                      onPressed: _saving || _loading ? null : _save,
                      child: const Text('Guardar'),
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
