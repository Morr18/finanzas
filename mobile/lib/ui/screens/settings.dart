import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../../data/models.dart';
import '../../data/utils.dart';
import '../theme.dart';
import '../widgets.dart';

class SettingsScreen extends StatelessWidget {
  const SettingsScreen({super.key});

  Future<_SettingsData> _load(BuildContext context) async {
    final db = AppScope.of(context).db;
    final missing = await db.missingRates();
    final hasForeign = await db.hasForeignAccountsAsync();
    return _SettingsData(
      rates: db.fxRates,
      missing: missing,
      hasForeignAccounts: hasForeign,
    );
  }

  @override
  Widget build(BuildContext context) {
    final state = AppScope.of(context);
    final db = state.db;
    final colors = FinColors.of(context);
    return DbFutureBuilder<_SettingsData>(
      load: () => _load(context),
      builder: (context, data) {
        return ListView(
          padding: const EdgeInsets.fromLTRB(16, 8, 16, 30),
          children: [
            _Card(
              title: 'Apariencia',
              icon: Icons.palette_outlined,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'Tema',
                    style: TextStyle(fontSize: 12, color: colors.muted),
                  ),
                  const SizedBox(height: 6),
                  SegmentedButton<String>(
                    segments: const [
                      ButtonSegment(value: 'light', label: Text('Claro')),
                      ButtonSegment(value: 'dark', label: Text('Oscuro')),
                      ButtonSegment(value: 'system', label: Text('Sistema')),
                    ],
                    selected: {state.themeSetting},
                    showSelectedIcon: false,
                    onSelectionChanged: (value) => state.setTheme(value.first),
                  ),
                  const SizedBox(height: 14),
                  Text(
                    'Formato de números',
                    style: TextStyle(fontSize: 12, color: colors.muted),
                  ),
                  const SizedBox(height: 6),
                  SegmentedButton<String>(
                    segments: const [
                      ButtonSegment(value: 'en', label: Text('1,234.56')),
                      ButtonSegment(value: 'es', label: Text('1.234,56')),
                    ],
                    selected: {db.numberFormat},
                    showSelectedIcon: false,
                    onSelectionChanged: (value) =>
                        state.setNumberFormat(value.first),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 12),
            _Card(
              title: 'Moneda',
              icon: Icons.currency_exchange,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  _SettingRow(
                    label: 'Moneda base',
                    value: db.baseCurrency,
                    onTap: () => _editBaseCurrency(context, state),
                  ),
                  Divider(color: colors.border),
                  _SettingRow(
                    label: 'Ver montos en',
                    value: state.shownCurrency,
                    caption: state.isConverted
                        ? 'Convertido desde ${db.baseCurrency}'
                        : 'Moneda base',
                    onTap: () => _pickDisplayCurrency(context, state),
                  ),
                  Divider(color: colors.border),
                  Padding(
                    padding: const EdgeInsets.only(top: 4, bottom: 6),
                    child: Text(
                      'La moneda de visualización solo cambia cómo ves los '
                      'montos: no crea cuentas ni modifica los datos guardados.',
                      style: TextStyle(fontSize: 11.5, color: colors.muted),
                    ),
                  ),
                  Row(
                    children: [
                      Expanded(
                        child: Text(
                          'Tasas de cambio',
                          style: TextStyle(
                            fontSize: 13,
                            fontWeight: FontWeight.w700,
                            color: colors.text,
                          ),
                        ),
                      ),
                      TextButton.icon(
                        onPressed: () => _addRate(context, state),
                        icon: const Icon(Icons.add, size: 16),
                        label: const Text('Añadir'),
                      ),
                    ],
                  ),
                  if (data.missing.isNotEmpty)
                    Container(
                      margin: const EdgeInsets.only(bottom: 8),
                      padding: const EdgeInsets.all(10),
                      decoration: BoxDecoration(
                        color: colors.amberSoft,
                        borderRadius: BorderRadius.circular(10),
                        border: Border.all(
                          color: colors.amber.withValues(alpha: 0.35),
                        ),
                      ),
                      child: Row(
                        children: [
                          Icon(Icons.warning_amber_outlined,
                              size: 16, color: colors.amber),
                          const SizedBox(width: 7),
                          Expanded(
                            child: Text(
                              'Falta la tasa de ${data.missing.join(', ')}. '
                              'Mientras tanto se usa 1:1.',
                              style: TextStyle(
                                  fontSize: 11.5, color: colors.amber),
                            ),
                          ),
                        ],
                      ),
                    ),
                  if (data.rates.isEmpty)
                    Padding(
                      padding: const EdgeInsets.symmetric(vertical: 8),
                      child: Text(
                        'Sin tasas registradas. Añade una para convertir '
                        'cuentas o ver montos en otra moneda.',
                        style: TextStyle(fontSize: 11.5, color: colors.muted),
                      ),
                    )
                  else
                    for (final rate in data.rates)
                      _RateRow(
                        rate: rate,
                        base: db.baseCurrency,
                        onDelete: () => _deleteRate(context, state, rate),
                      ),
                  if (!data.hasForeignAccounts)
                    Padding(
                      padding: const EdgeInsets.only(top: 6),
                      child: Text(
                        'No tienes cuentas en otra moneda. Aun así puedes '
                        'registrar tasas para ver todos los montos convertidos.',
                        style: TextStyle(fontSize: 11, color: colors.subtle),
                      ),
                    ),
                ],
              ),
            ),
            const SizedBox(height: 12),
            _Card(
              title: 'Datos y respaldo',
              icon: Icons.inventory_2_outlined,
              child: Column(
                children: [
                  _ActionRow(
                    icon: Icons.upload_file_outlined,
                    label: 'Exportar respaldo',
                    caption:
                        'Copia un JSON con todos tus datos al portapapeles.',
                    onTap: () => _export(context, state),
                  ),
                  Divider(color: colors.border),
                  _ActionRow(
                    icon: Icons.download_outlined,
                    label: 'Restaurar respaldo',
                    caption:
                        'Pega un respaldo exportado y reemplaza los datos.',
                    onTap: () => _restore(context, state),
                  ),
                  Divider(color: colors.border),
                  _ActionRow(
                    icon: Icons.auto_awesome_outlined,
                    label: 'Cargar datos de ejemplo',
                    caption: 'Añade seis meses de movimientos de prueba.',
                    onTap: () => _demo(context, state),
                  ),
                  Divider(color: colors.border),
                  _ActionRow(
                    icon: Icons.delete_forever_outlined,
                    label: 'Borrar todos los datos',
                    caption: 'Deja la app como recién instalada.',
                    danger: true,
                    onTap: () => _wipe(context, state),
                  ),
                ],
              ),
            ),
            const SizedBox(height: 12),
            _Card(
              title: 'Acerca de',
              icon: Icons.info_outline,
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    'Finanzas móvil 1.0.0',
                    style: TextStyle(
                      fontSize: 13,
                      fontWeight: FontWeight.w700,
                      color: colors.text,
                    ),
                  ),
                  const SizedBox(height: 4),
                  Text(
                    'Funciona 100% sin conexión. La base SQLite vive en este '
                    'teléfono y usa el mismo esquema que la versión de '
                    'escritorio: puedes mover un respaldo entre ambas.',
                    style: TextStyle(fontSize: 11.5, color: colors.muted),
                  ),
                ],
              ),
            ),
          ],
        );
      },
    );
  }

  Future<void> _editBaseCurrency(BuildContext context, AppState state) async {
    final result = await showDialog<String>(
      context: context,
      builder: (_) => _BaseCurrencyDialog(current: state.db.baseCurrency),
    );
    if (result == null) return;
    try {
      await state.db.setBaseCurrency(result);
      await state.reload();
      if (context.mounted) {
        showMessage(context, 'Moneda base: ${state.db.baseCurrency}');
      }
    } catch (error) {
      if (context.mounted) {
        showMessage(context, '$error', error: true);
      }
    }
  }

  Future<void> _pickDisplayCurrency(
    BuildContext context,
    AppState state,
  ) async {
    final db = state.db;
    final options = db.availableDisplayCurrencies;
    final selected = await showModalBottomSheet<String>(
      context: context,
      useSafeArea: true,
      builder: (context) => SafeArea(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            Padding(
              padding: const EdgeInsets.fromLTRB(20, 18, 20, 6),
              child: Row(
                children: [
                  Text(
                    'Ver montos en',
                    style: TextStyle(
                      fontSize: 16,
                      fontWeight: FontWeight.w800,
                      color: FinColors.of(context).text,
                    ),
                  ),
                ],
              ),
            ),
            ListTile(
              leading: Icon(
                state.displayCurrency.isEmpty
                    ? Icons.radio_button_checked
                    : Icons.radio_button_unchecked,
                color: FinColors.of(context).primary,
              ),
              title: Text('${db.baseCurrency} (moneda base)'),
              onTap: () => Navigator.pop(context, ''),
            ),
            for (final code in options.where((code) => code != db.baseCurrency))
              ListTile(
                leading: Icon(
                  state.displayCurrency == code
                      ? Icons.radio_button_checked
                      : Icons.radio_button_unchecked,
                  color: FinColors.of(context).primary,
                ),
                title: Text(code),
                subtitle: Text(
                  '1 $code = ${formatRate(
                    db.fxRateMicros(code) / 1000000,
                    es: state.isSpanish,
                  )} ${db.baseCurrency}',
                ),
                onTap: () => Navigator.pop(context, code),
              ),
            if (options.length <= 1)
              Padding(
                padding: const EdgeInsets.fromLTRB(20, 8, 20, 20),
                child: Text(
                  'Registra una tasa de cambio para habilitar otras monedas.',
                  style: TextStyle(
                    fontSize: 12,
                    color: FinColors.of(context).muted,
                  ),
                ),
              ),
            const SizedBox(height: 8),
          ],
        ),
      ),
    );
    if (selected == null) return;
    await state.setDisplayCurrency(selected);
  }

  Future<void> _addRate(BuildContext context, AppState state) async {
    final added = await showDialog<bool>(
      context: context,
      builder: (_) => _RateDialog(
        base: state.db.baseCurrency,
        existing: state.db.currenciesWithRates,
      ),
    );
    if (added != true) return;
    await state.reload();
    if (context.mounted) showMessage(context, 'Tipo de cambio guardado.');
  }

  Future<void> _deleteRate(
    BuildContext context,
    AppState state,
    FxRate rate,
  ) async {
    final ok = await confirmAction(
      context,
      title: 'Eliminar tasa',
      message: '¿Eliminar 1 ${rate.currency} = '
          '${formatRate(rate.rate, es: state.isSpanish)} '
          '${state.db.baseCurrency} del ${fmtDate(rate.date)}?',
      confirmLabel: 'Eliminar',
      destructive: true,
    );
    if (!ok) return;
    await state.db.deleteFxRate(rate.currency, rate.date);
    await state.reload();
  }

  Future<void> _export(BuildContext context, AppState state) async {
    try {
      final json = await state.db.exportBackup();
      await Clipboard.setData(ClipboardData(text: json));
      if (context.mounted) {
        showMessage(
          context,
          'Respaldo copiado al portapapeles (${(json.length / 1024).toStringAsFixed(1)} KB).',
        );
      }
    } catch (error) {
      if (context.mounted) {
        showMessage(context, 'No se pudo exportar: $error', error: true);
      }
    }
  }

  Future<void> _restore(BuildContext context, AppState state) async {
    final data = await Clipboard.getData('text/plain');
    final text = data?.text?.trim() ?? '';
    if (text.isEmpty) {
      if (context.mounted) {
        showMessage(
          context,
          'El portapapeles está vacío. Copia primero un respaldo JSON.',
          error: true,
        );
      }
      return;
    }
    if (!text.contains('"tables"')) {
      if (context.mounted) {
        showMessage(
          context,
          'El texto del portapapeles no parece un respaldo de Finanzas.',
          error: true,
        );
      }
      return;
    }
    if (!context.mounted) return;
    final ok = await confirmAction(
      context,
      title: 'Restaurar respaldo',
      message: 'Se reemplazarán todos los datos actuales por los del '
          'respaldo (${(text.length / 1024).toStringAsFixed(1)} KB). '
          'Esta acción no se puede deshacer.',
      confirmLabel: 'Restaurar',
      destructive: true,
    );
    if (!ok) return;
    try {
      await state.db.restoreBackup(text);
      await state.reload();
      if (context.mounted) showMessage(context, 'Respaldo restaurado.');
    } catch (error) {
      if (context.mounted) {
        showMessage(context, 'No se pudo restaurar: $error', error: true);
      }
    }
  }

  Future<void> _demo(BuildContext context, AppState state) async {
    if (await state.db.hasTransactions()) {
      if (!context.mounted) return;
      final ok = await confirmAction(
        context,
        title: 'Añadir datos de ejemplo',
        message: 'Ya tienes movimientos. Se añadirán los de ejemplo junto a '
            'los existentes. ¿Continuar?',
        confirmLabel: 'Añadir',
      );
      if (!ok) return;
    }
    await state.db.seedDemo();
    state.bump();
    if (context.mounted) showMessage(context, 'Datos de ejemplo añadidos.');
  }

  Future<void> _wipe(BuildContext context, AppState state) async {
    final ok = await confirmAction(
      context,
      title: 'Borrar todos los datos',
      message: 'Se eliminarán movimientos, cuentas, categorías, presupuestos, '
          'recurrentes, reglas y tasas. Exporta un respaldo antes si quieres '
          'conservarlos.',
      confirmLabel: 'Borrar todo',
      destructive: true,
    );
    if (!ok) return;
    await state.db.wipeAll();
    await state.setDisplayCurrency('');
    await state.reload();
    if (context.mounted) showMessage(context, 'Datos borrados.');
  }
}

class _SettingsData {
  const _SettingsData({
    required this.rates,
    required this.missing,
    required this.hasForeignAccounts,
  });

  final List<FxRate> rates;
  final List<String> missing;
  final bool hasForeignAccounts;
}

class _Card extends StatelessWidget {
  const _Card({
    required this.title,
    required this.icon,
    required this.child,
  });

  final String title;
  final IconData icon;
  final Widget child;

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
              Icon(icon, size: 17, color: colors.primary),
              const SizedBox(width: 7),
              Text(
                title,
                style: TextStyle(
                  fontSize: 14,
                  fontWeight: FontWeight.w800,
                  color: colors.text,
                ),
              ),
            ],
          ),
          const SizedBox(height: 12),
          child,
        ],
      ),
    );
  }
}

class _SettingRow extends StatelessWidget {
  const _SettingRow({
    required this.label,
    required this.value,
    required this.onTap,
    this.caption,
  });

  final String label;
  final String value;
  final String? caption;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final colors = FinColors.of(context);
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(10),
      child: Padding(
        padding: const EdgeInsets.symmetric(vertical: 10),
        child: Row(
          children: [
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    label,
                    style: TextStyle(
                      fontSize: 13,
                      fontWeight: FontWeight.w600,
                      color: colors.text,
                    ),
                  ),
                  if (caption != null)
                    Text(
                      caption!,
                      style: TextStyle(fontSize: 10.5, color: colors.subtle),
                    ),
                ],
              ),
            ),
            Text(
              value,
              style: TextStyle(
                fontSize: 12.5,
                fontWeight: FontWeight.w700,
                color: colors.primary,
              ),
            ),
            const SizedBox(width: 2),
            Icon(Icons.chevron_right, size: 18, color: colors.subtle),
          ],
        ),
      ),
    );
  }
}

class _RateRow extends StatelessWidget {
  const _RateRow({
    required this.rate,
    required this.base,
    required this.onDelete,
  });

  final FxRate rate;
  final String base;
  final VoidCallback onDelete;

  @override
  Widget build(BuildContext context) {
    final colors = FinColors.of(context);
    final state = AppScope.of(context);
    return Padding(
      padding: const EdgeInsets.symmetric(vertical: 5),
      child: Row(
        children: [
          Container(
            padding: const EdgeInsets.symmetric(horizontal: 7, vertical: 2),
            decoration: BoxDecoration(
              color: colors.primarySoft,
              borderRadius: BorderRadius.circular(6),
            ),
            child: Text(
              rate.currency,
              style: TextStyle(
                fontSize: 10.5,
                fontWeight: FontWeight.w800,
                color: colors.primary,
              ),
            ),
          ),
          const SizedBox(width: 8),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(
                  '1 ${rate.currency} = '
                  '${formatRate(rate.rate, es: state.isSpanish)} $base',
                  style: TextStyle(
                    fontSize: 12.5,
                    fontWeight: FontWeight.w600,
                    color: colors.text,
                  ),
                ),
                Text(
                  fmtDate(rate.date),
                  style: TextStyle(fontSize: 10.5, color: colors.subtle),
                ),
              ],
            ),
          ),
          IconButton(
            onPressed: onDelete,
            visualDensity: VisualDensity.compact,
            icon: Icon(Icons.close, size: 17, color: colors.subtle),
            tooltip: 'Eliminar tasa',
          ),
        ],
      ),
    );
  }
}

class _ActionRow extends StatelessWidget {
  const _ActionRow({
    required this.icon,
    required this.label,
    required this.caption,
    required this.onTap,
    this.danger = false,
  });

  final IconData icon;
  final String label;
  final String caption;
  final VoidCallback onTap;
  final bool danger;

  @override
  Widget build(BuildContext context) {
    final colors = FinColors.of(context);
    final accent = danger ? colors.red : colors.primary;
    return InkWell(
      onTap: onTap,
      borderRadius: BorderRadius.circular(10),
      child: Padding(
        padding: const EdgeInsets.symmetric(vertical: 9),
        child: Row(
          children: [
            Container(
              width: 32,
              height: 32,
              decoration: BoxDecoration(
                color: accent.withValues(alpha: 0.11),
                borderRadius: BorderRadius.circular(9),
              ),
              child: Icon(icon, size: 17, color: accent),
            ),
            const SizedBox(width: 10),
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                children: [
                  Text(
                    label,
                    style: TextStyle(
                      fontSize: 13,
                      fontWeight: FontWeight.w600,
                      color: danger ? colors.red : colors.text,
                    ),
                  ),
                  Text(
                    caption,
                    style: TextStyle(fontSize: 10.5, color: colors.muted),
                  ),
                ],
              ),
            ),
            Icon(Icons.chevron_right, size: 18, color: colors.subtle),
          ],
        ),
      ),
    );
  }
}

class _BaseCurrencyDialog extends StatefulWidget {
  const _BaseCurrencyDialog({required this.current});

  final String current;

  @override
  State<_BaseCurrencyDialog> createState() => _BaseCurrencyDialogState();
}

class _BaseCurrencyDialogState extends State<_BaseCurrencyDialog> {
  late final TextEditingController _code =
      TextEditingController(text: widget.current);
  String? _error;

  @override
  void dispose() {
    _code.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    final colors = FinColors.of(context);
    return AlertDialog(
      title: const Text('Moneda base'),
      content: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          Text(
            'Todos los montos se guardan en esta moneda. Usa el código ISO de '
            '3 letras.',
            style: TextStyle(fontSize: 12.5, color: colors.muted),
          ),
          const SizedBox(height: 12),
          TextField(
            controller: _code,
            autofocus: true,
            maxLength: 3,
            textCapitalization: TextCapitalization.characters,
            decoration: InputDecoration(
              hintText: 'MXN',
              counterText: '',
              errorText: _error,
            ),
          ),
          if (_code.text.trim().toUpperCase() != widget.current)
            Padding(
              padding: const EdgeInsets.only(top: 8),
              child: Text(
                'Al cambiar la base se borran las tasas registradas para la '
                'nueva moneda y la vista vuelve a la moneda base.',
                style: TextStyle(fontSize: 11, color: colors.amber),
              ),
            ),
        ],
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.pop(context),
          child: const Text('Cancelar'),
        ),
        FilledButton(
          onPressed: () {
            try {
              final code = normalizeCurrency(_code.text);
              Navigator.pop(context, code);
            } on FormatException catch (error) {
              setState(() => _error = error.message);
            }
          },
          child: const Text('Guardar'),
        ),
      ],
    );
  }
}

class _RateDialog extends StatefulWidget {
  const _RateDialog({required this.base, required this.existing});

  final String base;
  final List<String> existing;

  @override
  State<_RateDialog> createState() => _RateDialogState();
}

class _RateDialogState extends State<_RateDialog> {
  late final TextEditingController _currency = TextEditingController(
    text: widget.existing.isEmpty ? 'USD' : '',
  );
  final _rate = TextEditingController();
  String _date = todayIso();
  String? _error;
  bool _saving = false;

  @override
  void dispose() {
    _currency.dispose();
    _rate.dispose();
    super.dispose();
  }

  Future<void> _save() async {
    final state = AppScope.of(context);
    String code;
    try {
      code = normalizeCurrency(_currency.text);
    } on FormatException catch (error) {
      setState(() => _error = error.message);
      return;
    }
    if (code == widget.base) {
      setState(() => _error = 'Esa ya es la moneda base.');
      return;
    }
    final raw = _rate.text.trim().replaceAll(' ', '').replaceAll(',', '.');
    final rate = double.tryParse(raw);
    if (rate == null || rate <= 0) {
      setState(() => _error = 'Escribe un tipo de cambio mayor que cero.');
      return;
    }
    setState(() {
      _saving = true;
      _error = null;
    });
    try {
      await state.db.setFxRate(code, _date, rate);
      if (mounted) Navigator.pop(context, true);
    } catch (error) {
      if (!mounted) return;
      setState(() {
        _saving = false;
        _error = '$error';
      });
    }
  }

  Future<void> _pickDate() async {
    final initial = DateTime.tryParse(_date) ?? DateTime.now();
    final picked = await showDatePicker(
      context: context,
      initialDate: initial,
      firstDate: DateTime(2000),
      lastDate: DateTime(2100),
      helpText: 'Fecha de la tasa',
      cancelText: 'Cancelar',
      confirmText: 'Aceptar',
    );
    if (picked != null) setState(() => _date = isoDate(picked));
  }

  @override
  Widget build(BuildContext context) {
    final colors = FinColors.of(context);
    return AlertDialog(
      title: const Text('Tipo de cambio'),
      content: SingleChildScrollView(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.start,
          children: [
            Text(
              'Cuántas unidades de ${widget.base} vale 1 unidad de la otra '
              'moneda.',
              style: TextStyle(fontSize: 12, color: colors.muted),
            ),
            const SizedBox(height: 12),
            TextField(
              controller: _currency,
              maxLength: 3,
              textCapitalization: TextCapitalization.characters,
              decoration: const InputDecoration(
                labelText: 'Moneda (ISO)',
                hintText: 'USD',
                counterText: '',
              ),
            ),
            const SizedBox(height: 10),
            TextField(
              controller: _rate,
              autofocus: true,
              keyboardType:
                  const TextInputType.numberWithOptions(decimal: true),
              decoration: InputDecoration(
                labelText: '1 unidad = ? ${widget.base}',
                hintText: '18.00',
              ),
            ),
            const SizedBox(height: 10),
            InkWell(
              onTap: _pickDate,
              borderRadius: BorderRadius.circular(10),
              child: Container(
                padding:
                    const EdgeInsets.symmetric(horizontal: 12, vertical: 11),
                decoration: BoxDecoration(
                  color: colors.cardSoft,
                  borderRadius: BorderRadius.circular(10),
                  border: Border.all(color: colors.border),
                ),
                child: Row(
                  children: [
                    Icon(Icons.event, size: 17, color: colors.muted),
                    const SizedBox(width: 8),
                    Text(
                      fmtDate(_date),
                      style: TextStyle(fontSize: 13, color: colors.text),
                    ),
                    const Spacer(),
                    Icon(Icons.expand_more, size: 17, color: colors.subtle),
                  ],
                ),
              ),
            ),
            if (_error != null)
              Padding(
                padding: const EdgeInsets.only(top: 10),
                child: Text(
                  _error!,
                  style: TextStyle(fontSize: 12, color: colors.red),
                ),
              ),
          ],
        ),
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.pop(context),
          child: const Text('Cancelar'),
        ),
        FilledButton(
          onPressed: _saving ? null : _save,
          child: const Text('Guardar'),
        ),
      ],
    );
  }
}
