import 'package:flutter/material.dart';

import '../../data/models.dart';
import '../theme.dart';
import '../widgets.dart';

class RulesScreen extends StatelessWidget {
  const RulesScreen({super.key});

  Future<List<RuleRecord>> _load(BuildContext context) =>
      AppScope.of(context).db.rules();

  Future<void> _apply(BuildContext context) async {
    final state = AppScope.of(context);
    final changed = await state.db.applyRulesToExisting();
    state.bump();
    if (!context.mounted) return;
    showMessage(
      context,
      changed == 0
          ? 'Ningún movimiento necesitaba cambios.'
          : 'Se actualizaron $changed movimientos.',
    );
  }

  @override
  Widget build(BuildContext context) {
    final colors = FinColors.of(context);
    return ScreenBody(
      fab: FloatingActionButton(
        heroTag: 'rules_add',
        onPressed: () => showRuleEditor(context),
        child: const Icon(Icons.add),
      ),
      child: DbFutureBuilder<List<RuleRecord>>(
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
                        Icon(Icons.rule, size: 18, color: colors.primary),
                        const SizedBox(width: 8),
                        Expanded(
                          child: Text(
                            '$active regla(s) activa(s)',
                            style: TextStyle(
                              fontSize: 13,
                              fontWeight: FontWeight.w700,
                              color: colors.text,
                            ),
                          ),
                        ),
                        FilledButton.tonalIcon(
                          onPressed: () => _apply(context),
                          icon: const Icon(Icons.auto_awesome, size: 16),
                          label: const Text('Aplicar'),
                        ),
                      ],
                    ),
                    const SizedBox(height: 6),
                    Text(
                      'Cuando la descripción o las notas de un movimiento '
                      'contienen el texto de una regla, se asigna su categoría '
                      'o cuenta automáticamente.',
                      style: TextStyle(fontSize: 11.5, color: colors.muted),
                    ),
                  ],
                ),
              ),
              const SizedBox(height: 14),
              if (rules.isEmpty)
                const EmptyState(
                  icon: Icons.rule,
                  title: 'Sin reglas',
                  message: 'Crea una regla para categorizar automáticamente, '
                      'por ejemplo «super» → Alimentación.',
                )
              else
                for (final rule in rules) ...[
                  _RuleCard(rule: rule),
                  const SizedBox(height: 9),
                ],
            ],
          );
        },
      ),
    );
  }
}

class _RuleCard extends StatelessWidget {
  const _RuleCard({required this.rule});

  final RuleRecord rule;

  @override
  Widget build(BuildContext context) {
    final colors = FinColors.of(context);
    final targets = <String>[
      if (rule.categoryName.isNotEmpty) 'Categoría: ${rule.categoryName}',
      if (rule.accountName.isNotEmpty) 'Cuenta: ${rule.accountName}',
    ];
    return InkWell(
      borderRadius: BorderRadius.circular(14),
      onTap: () => showRuleEditor(context, rule: rule),
      child: Container(
        padding: const EdgeInsets.fromLTRB(13, 10, 6, 10),
        decoration: BoxDecoration(
          color: colors.card,
          borderRadius: BorderRadius.circular(14),
          border: Border.all(color: colors.border),
        ),
        child: Row(
          children: [
            Container(
              width: 34,
              height: 34,
              decoration: BoxDecoration(
                color: colors.primarySoft,
                borderRadius: BorderRadius.circular(10),
              ),
              child: Icon(Icons.search, size: 17, color: colors.primary),
            ),
            const SizedBox(width: 10),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    '«${rule.matchText}»',
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
                    targets.isEmpty ? 'Sin destino' : targets.join(' · '),
                    maxLines: 1,
                    overflow: TextOverflow.ellipsis,
                    style: TextStyle(fontSize: 11, color: colors.muted),
                  ),
                ],
              ),
            ),
            Switch(
              value: rule.active,
              materialTapTargetSize: MaterialTapTargetSize.shrinkWrap,
              onChanged: (value) async {
                final state = AppScope.of(context);
                await state.db.setRuleActive(rule.id, value);
                state.bump();
              },
            ),
          ],
        ),
      ),
    );
  }
}

Future<void> showRuleEditor(BuildContext context, {RuleRecord? rule}) {
  return showModalBottomSheet<void>(
    context: context,
    isScrollControlled: true,
    useSafeArea: true,
    builder: (_) => RuleEditor(rule: rule),
  );
}

class RuleEditor extends StatefulWidget {
  const RuleEditor({super.key, this.rule});

  final RuleRecord? rule;

  @override
  State<RuleEditor> createState() => _RuleEditorState();
}

class _RuleEditorState extends State<RuleEditor> {
  final _match = TextEditingController();
  int? _categoryId;
  int? _accountId;
  bool _active = true;
  bool _loading = true;
  bool _started = false;
  bool _saving = false;
  String? _error;
  List<Category> _categories = [];
  List<AccountBalance> _accounts = [];

  bool get _editing => widget.rule != null;

  @override
  void initState() {
    super.initState();
    final rule = widget.rule;
    _active = rule?.active ?? true;
    _categoryId = rule?.categoryId;
    _accountId = rule?.accountId;
    if (rule != null) _match.text = rule.matchText;
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
    _match.dispose();
    super.dispose();
  }

  Future<void> _load() async {
    final db = AppScope.of(context).db;
    final expense = await db.categories('egreso');
    final income = await db.categories('ingreso');
    final accounts = await db.accountBalances();
    if (!mounted) return;
    setState(() {
      _categories = [...expense, ...income];
      _accounts = accounts;
      _loading = false;
    });
  }

  Future<void> _save() async {
    final state = AppScope.of(context);
    final db = state.db;
    if (_match.text.trim().isEmpty) {
      setState(
          () => _error = 'Escribe el texto que debe contener el movimiento.');
      return;
    }
    if (_categoryId == null && _accountId == null) {
      setState(() => _error = 'Elige una categoría o una cuenta.');
      return;
    }
    setState(() {
      _saving = true;
      _error = null;
    });
    try {
      if (_editing) {
        await db.updateRule(
          widget.rule!.id,
          matchText: _match.text,
          categoryId: _categoryId,
          accountId: _accountId,
          active: _active,
        );
      } else {
        await db.addRule(
          matchText: _match.text,
          categoryId: _categoryId,
          accountId: _accountId,
          active: _active,
        );
      }
      state.bump();
      if (mounted) Navigator.pop(context);
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
      title: 'Eliminar regla',
      message: '¿Eliminar la regla «${widget.rule!.matchText}»?',
      confirmLabel: 'Eliminar',
      destructive: true,
    );
    if (!ok) return;
    await state.db.deleteRule(widget.rule!.id);
    state.bump();
    if (mounted) Navigator.pop(context);
  }

  @override
  Widget build(BuildContext context) {
    final colors = FinColors.of(context);
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
                      _editing ? 'Editar regla' : 'Nueva regla',
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
                          LabeledField(
                            label: 'Texto a buscar',
                            help: 'No distingue mayúsculas. Se busca en la '
                                'descripción y en las notas.',
                            child: TextField(
                              controller: _match,
                              autofocus: !_editing,
                              decoration: const InputDecoration(
                                hintText: 'Ej. super, nómina, netflix',
                              ),
                            ),
                          ),
                          const SizedBox(height: 14),
                          LabeledField(
                            label: 'Asignar categoría',
                            child: DropdownButtonFormField<int?>(
                              initialValue: _categoryId,
                              isExpanded: true,
                              hint: const Text('Sin categoría'),
                              items: [
                                const DropdownMenuItem<int?>(
                                  value: null,
                                  child: Text('Sin categoría'),
                                ),
                                for (final category in _categories)
                                  DropdownMenuItem<int?>(
                                    value: category.id,
                                    child: Row(
                                      children: [
                                        ColorDot(hexColor(category.color),
                                            size: 8),
                                        const SizedBox(width: 7),
                                        Expanded(
                                          child: Text(
                                            '${category.name} · '
                                            '${category.kind == 'ingreso' ? 'ingreso' : 'gasto'}',
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
                          const SizedBox(height: 14),
                          LabeledField(
                            label: 'Asignar cuenta',
                            child: DropdownButtonFormField<int?>(
                              initialValue: _accountId,
                              isExpanded: true,
                              hint: const Text('Sin cuenta'),
                              items: [
                                const DropdownMenuItem<int?>(
                                  value: null,
                                  child: Text('Sin cuenta'),
                                ),
                                for (final account in _accounts)
                                  DropdownMenuItem<int?>(
                                    value: account.id,
                                    child: Text(account.name),
                                  ),
                              ],
                              onChanged: (value) =>
                                  setState(() => _accountId = value),
                            ),
                          ),
                          SwitchListTile(
                            contentPadding: EdgeInsets.zero,
                            value: _active,
                            title: const Text(
                              'Activa',
                              style: TextStyle(fontSize: 13.5),
                            ),
                            onChanged: (value) =>
                                setState(() => _active = value),
                          ),
                          if (_error != null)
                            Text(
                              _error!,
                              style:
                                  TextStyle(fontSize: 12.5, color: colors.red),
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
