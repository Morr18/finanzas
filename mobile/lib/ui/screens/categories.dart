import 'package:flutter/material.dart';

import '../../data/models.dart';
import '../theme.dart';
import '../widgets.dart';

class CategoriesScreen extends StatefulWidget {
  const CategoriesScreen({super.key});

  @override
  State<CategoriesScreen> createState() => _CategoriesScreenState();
}

class _CategoriesScreenState extends State<CategoriesScreen> {
  String _kind = 'egreso';
  bool _showArchived = false;

  Future<List<Category>> _load() =>
      AppScope.of(context).db.categories(_kind, includeArchived: _showArchived);

  @override
  Widget build(BuildContext context) {
    final colors = FinColors.of(context);
    return ScreenBody(
      fab: FloatingActionButton(
        heroTag: 'categories_add',
        onPressed: () => showCategoryEditor(context, kind: _kind),
        child: const Icon(Icons.add),
      ),
      child: Column(
        children: [
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 8, 16, 4),
            child: Row(
              children: [
                Expanded(
                  child: SegmentedButton<String>(
                    segments: const [
                      ButtonSegment(value: 'egreso', label: Text('Gastos')),
                      ButtonSegment(value: 'ingreso', label: Text('Ingresos')),
                    ],
                    selected: {_kind},
                    showSelectedIcon: false,
                    onSelectionChanged: (value) =>
                        setState(() => _kind = value.first),
                  ),
                ),
                const SizedBox(width: 10),
                IconButton(
                  tooltip:
                      _showArchived ? 'Ocultar archivadas' : 'Ver archivadas',
                  onPressed: () =>
                      setState(() => _showArchived = !_showArchived),
                  icon: Icon(
                    _showArchived
                        ? Icons.visibility_off_outlined
                        : Icons.visibility_outlined,
                    color: _showArchived ? colors.primary : colors.muted,
                  ),
                ),
              ],
            ),
          ),
          Expanded(
            child: DbFutureBuilder<List<Category>>(
              key: ValueKey('$_kind|$_showArchived'),
              load: _load,
              builder: (context, categories) {
                if (categories.isEmpty) {
                  return ListView(
                    padding: const EdgeInsets.fromLTRB(16, 8, 16, 96),
                    children: [
                      EmptyState(
                        icon: Icons.local_offer_outlined,
                        title:
                            'Sin categorías de ${_kind == 'egreso' ? 'gasto' : 'ingreso'}',
                        message:
                            'Añade categorías para clasificar tus movimientos.',
                        action: FilledButton.icon(
                          onPressed: () =>
                              showCategoryEditor(context, kind: _kind),
                          icon: const Icon(Icons.add, size: 18),
                          label: const Text('Crear categoría'),
                        ),
                      ),
                    ],
                  );
                }
                return ListView.separated(
                  padding: const EdgeInsets.fromLTRB(16, 8, 16, 96),
                  itemCount: categories.length,
                  separatorBuilder: (_, __) => const SizedBox(height: 8),
                  itemBuilder: (context, index) {
                    final category = categories[index];
                    return InkWell(
                      borderRadius: BorderRadius.circular(13),
                      onTap: () => showCategoryEditor(
                        context,
                        kind: _kind,
                        category: category,
                      ),
                      child: Container(
                        padding: const EdgeInsets.symmetric(
                          horizontal: 14,
                          vertical: 12,
                        ),
                        decoration: BoxDecoration(
                          color: colors.card,
                          borderRadius: BorderRadius.circular(13),
                          border: Border.all(color: colors.border),
                        ),
                        child: Row(
                          children: [
                            Container(
                              width: 34,
                              height: 34,
                              decoration: BoxDecoration(
                                color: hexColor(category.color)
                                    .withValues(alpha: 0.14),
                                borderRadius: BorderRadius.circular(10),
                              ),
                              child: Icon(
                                _kind == 'egreso'
                                    ? Icons.north_east
                                    : Icons.south_west,
                                size: 17,
                                color: hexColor(category.color),
                              ),
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
                                          category.name,
                                          maxLines: 1,
                                          overflow: TextOverflow.ellipsis,
                                          style: TextStyle(
                                            fontSize: 13.5,
                                            fontWeight: FontWeight.w600,
                                            color: category.archived
                                                ? colors.muted
                                                : colors.text,
                                          ),
                                        ),
                                      ),
                                      if (category.archived) ...[
                                        const SizedBox(width: 6),
                                        Container(
                                          padding: const EdgeInsets.symmetric(
                                            horizontal: 6,
                                            vertical: 1,
                                          ),
                                          decoration: BoxDecoration(
                                            color: colors.cardSoft,
                                            borderRadius:
                                                BorderRadius.circular(5),
                                            border: Border.all(
                                                color: colors.border),
                                          ),
                                          child: Text(
                                            'Archivada',
                                            style: TextStyle(
                                              fontSize: 9,
                                              color: colors.muted,
                                            ),
                                          ),
                                        ),
                                      ],
                                    ],
                                  ),
                                  const SizedBox(height: 2),
                                  Text(
                                    '${category.usage} movimiento(s)',
                                    style: TextStyle(
                                      fontSize: 11,
                                      color: colors.subtle,
                                    ),
                                  ),
                                ],
                              ),
                            ),
                            Icon(Icons.chevron_right,
                                size: 19, color: colors.subtle),
                          ],
                        ),
                      ),
                    );
                  },
                );
              },
            ),
          ),
        ],
      ),
    );
  }
}

Future<void> showCategoryEditor(
  BuildContext context, {
  String kind = 'egreso',
  Category? category,
}) {
  return showModalBottomSheet<void>(
    context: context,
    isScrollControlled: true,
    useSafeArea: true,
    builder: (_) => CategoryEditor(kind: kind, category: category),
  );
}

class CategoryEditor extends StatefulWidget {
  const CategoryEditor({super.key, required this.kind, this.category});

  final String kind;
  final Category? category;

  @override
  State<CategoryEditor> createState() => _CategoryEditorState();
}

class _CategoryEditorState extends State<CategoryEditor> {
  final _name = TextEditingController();
  late String _kind = widget.category?.kind ?? widget.kind;
  String _color = '#6366f1';
  bool _saving = false;
  String? _error;

  @override
  void initState() {
    super.initState();
    final category = widget.category;
    if (category != null) {
      _name.text = category.name;
      _color = category.color.isEmpty ? '#6366f1' : category.color;
    }
  }

  @override
  void dispose() {
    _name.dispose();
    super.dispose();
  }

  Future<void> _save() async {
    final state = AppScope.of(context);
    final db = state.db;
    if (_name.text.trim().isEmpty) {
      setState(() => _error = 'Escribe el nombre de la categoría.');
      return;
    }
    setState(() {
      _saving = true;
      _error = null;
    });
    try {
      if (widget.category == null) {
        await db.addCategory(_name.text, _kind, _color);
      } else {
        await db.updateCategory(
          widget.category!.id,
          _name.text,
          _kind,
          _color,
        );
      }
      state.bump();
      if (mounted) Navigator.pop(context);
    } catch (error) {
      if (!mounted) return;
      setState(() {
        _saving = false;
        _error = 'No se pudo guardar. ¿Ya existe esa categoría?';
      });
    }
  }

  Future<void> _delete() async {
    final state = AppScope.of(context);
    final db = state.db;
    final category = widget.category!;
    if (category.archived) {
      await db.setCategoryArchived(category.id, false);
      state.bump();
      if (mounted) Navigator.pop(context);
      return;
    }
    final usage = category.usage;
    final ok = await confirmAction(
      context,
      title: usage > 0 ? 'Archivar categoría' : 'Eliminar categoría',
      message: usage > 0
          ? '«${category.name}» tiene $usage movimiento(s). Se archivará para '
              'no perder el historial y dejará de aparecer al registrar.'
          : '¿Eliminar «${category.name}»?',
      confirmLabel: usage > 0 ? 'Archivar' : 'Eliminar',
      destructive: true,
    );
    if (!ok) return;
    await db.deleteOrArchiveCategory(category.id);
    state.bump();
    if (mounted) Navigator.pop(context);
  }

  @override
  Widget build(BuildContext context) {
    final colors = FinColors.of(context);
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
            const SizedBox(height: 12),
            Row(
              children: [
                Expanded(
                  child: Text(
                    widget.category == null
                        ? 'Nueva categoría'
                        : 'Editar categoría',
                    style: TextStyle(
                      fontSize: 17,
                      fontWeight: FontWeight.w800,
                      color: colors.text,
                    ),
                  ),
                ),
                if (widget.category != null)
                  IconButton(
                    onPressed: _delete,
                    tooltip:
                        widget.category!.archived ? 'Restaurar' : 'Eliminar',
                    icon: Icon(
                      widget.category!.archived
                          ? Icons.unarchive_outlined
                          : Icons.delete_outline,
                      color: widget.category!.archived
                          ? colors.primary
                          : colors.red,
                    ),
                  ),
                IconButton(
                  onPressed: () => Navigator.pop(context),
                  icon: const Icon(Icons.close),
                ),
              ],
            ),
            const SizedBox(height: 6),
            SegmentedButton<String>(
              segments: const [
                ButtonSegment(value: 'egreso', label: Text('Gasto')),
                ButtonSegment(value: 'ingreso', label: Text('Ingreso')),
              ],
              selected: {_kind},
              showSelectedIcon: false,
              onSelectionChanged: widget.category == null
                  ? (value) => setState(() => _kind = value.first)
                  : null,
            ),
            const SizedBox(height: 16),
            LabeledField(
              label: 'Nombre',
              child: TextField(
                controller: _name,
                autofocus: true,
                textCapitalization: TextCapitalization.sentences,
                decoration: const InputDecoration(hintText: 'Ej. Mascotas'),
              ),
            ),
            const SizedBox(height: 14),
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
            const SizedBox(height: 16),
            Row(
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
                    child: Text(widget.category == null ? 'Crear' : 'Guardar'),
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
