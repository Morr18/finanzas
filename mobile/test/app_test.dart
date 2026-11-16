import 'dart:io';

import 'package:finanzas_mobile/app.dart';
import 'package:finanzas_mobile/data/database.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sqflite_common_ffi/sqflite_ffi.dart';

void main() {
  sqfliteFfiInit();
  databaseFactory = databaseFactoryFfiNoIsolate;

  late Directory tempDir;
  late AppDatabase db;

  setUp(() async {
    tempDir = await Directory.systemTemp.createTemp('finanzas_widget_test');
    db = await AppDatabase.open('${tempDir.path}/finanzas.db');
  });

  tearDown(() async {
    await db.close();
    await tempDir.delete(recursive: true);
  });

  Future<void> pumpApp(WidgetTester tester) async {
    tester.view.physicalSize = const Size(390 * 3, 844 * 3);
    tester.view.devicePixelRatio = 3;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);
    await tester.pumpWidget(FinanzasApp(db: db));
    await tester.pumpAndSettle();
  }

  testWidgets('la app abre en el resumen y navega entre secciones',
      (tester) async {
    await pumpApp(tester);

    expect(find.text('Resumen'), findsWidgets);
    expect(find.text('Balance total'), findsOneWidget);

    await tester.tap(find.text('Movimientos').last);
    await tester.pumpAndSettle();
    expect(find.text('Sin movimientos'), findsOneWidget);

    await tester.tap(find.text('Presupuestos').last);
    await tester.pumpAndSettle();
    expect(find.text('Presupuesto del mes'), findsOneWidget);

    await tester.tap(find.text('Reportes').last);
    await tester.pumpAndSettle();
    expect(find.text('Últimos 6 meses'), findsOneWidget);
  });

  testWidgets('abre el formulario de movimiento y valida el monto',
      (tester) async {
    await pumpApp(tester);

    await tester.tap(find.byType(FloatingActionButton));
    await tester.pumpAndSettle();
    expect(find.text('Nuevo movimiento'), findsOneWidget);

    await tester.tap(find.text('Guardar'));
    await tester.pumpAndSettle();
    expect(
      find.text('Escribe un monto válido, por ejemplo 1250.50'),
      findsOneWidget,
    );

    await tester.tap(find.byIcon(Icons.close));
    await tester.pumpAndSettle();
  });

  testWidgets('crea un movimiento desde la interfaz', (tester) async {
    await pumpApp(tester);
    await tester.tap(find.byType(FloatingActionButton));
    await tester.pumpAndSettle();

    await tester.enterText(find.byType(TextField).first, '1250.50');
    await tester.enterText(find.byType(TextField).at(1), 'Prueba de interfaz');
    await tester.tap(find.text('Guardar'));
    await tester.pumpAndSettle();

    expect(find.text('Nuevo movimiento'), findsNothing);
    expect(await db.transactions(), hasLength(1));
    await tester.scrollUntilVisible(
      find.text('Prueba de interfaz'),
      260,
      scrollable: find.byType(Scrollable).first,
    );
    expect(find.text('Prueba de interfaz'), findsOneWidget);
  });

  testWidgets('el menú lateral abre las demás secciones', (tester) async {
    await pumpApp(tester);

    await tester.tap(find.byIcon(Icons.menu));
    await tester.pumpAndSettle();
    expect(find.text('Cuentas'), findsWidgets);

    await tester.tap(find.text('Cuentas').last);
    await tester.pumpAndSettle();
    expect(find.text('Patrimonio'), findsOneWidget);

    await tester.tap(find.byType(BackButton));
    await tester.pumpAndSettle();

    await tester.tap(find.byIcon(Icons.menu));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Ajustes').last);
    await tester.pumpAndSettle();
    expect(find.text('Exportar respaldo'), findsOneWidget);
    expect(find.text('Tasas de cambio'), findsOneWidget);
  });

  testWidgets('recorre todas las secciones desde el menú', (tester) async {
    await pumpApp(tester);

    for (final section in [
      'Cuentas',
      'Categorías',
      'Recurrentes',
      'Reglas',
      'Ajustes',
    ]) {
      await tester.tap(find.byIcon(Icons.menu));
      await tester.pumpAndSettle();
      await tester.tap(find.text(section).last);
      await tester.pumpAndSettle();
      expect(find.text(section), findsWidgets);
      await tester.tap(find.byType(BackButton));
      await tester.pumpAndSettle();
    }
  });

  testWidgets('abre y cierra los editores de cada sección', (tester) async {
    await pumpApp(tester);

    for (final section in [
      'Cuentas',
      'Categorías',
      'Recurrentes',
      'Reglas',
    ]) {
      await tester.tap(find.byIcon(Icons.menu));
      await tester.pumpAndSettle();
      await tester.tap(find.text(section).last);
      await tester.pumpAndSettle();

      await tester.tap(find.byType(FloatingActionButton));
      await tester.pumpAndSettle();
      expect(find.byIcon(Icons.close), findsWidgets);

      await tester.tap(find.byIcon(Icons.close).last);
      await tester.pumpAndSettle();
      await tester.tap(find.byType(BackButton));
      await tester.pumpAndSettle();
    }
  });

  testWidgets('el selector de moneda abre las opciones', (tester) async {
    await db.setFxRate('USD', todayForTest(), 18);
    await pumpApp(tester);

    await tester.tap(find.byTooltip('Ver montos en otra moneda'));
    await tester.pump();
    await tester.pump(const Duration(milliseconds: 400));
    expect(find.text('Administrar monedas'), findsOneWidget);
    expect(find.text('USD'), findsOneWidget);

    await tester.tap(find.text('USD'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('Más').last);
    await tester.pumpAndSettle();
    expect(
      find.textContaining('Estás viendo los montos en USD'),
      findsOneWidget,
    );
  });

  testWidgets('se ve bien en un teléfono pequeño', (tester) async {
    tester.view.physicalSize = const Size(360 * 3, 640 * 3);
    tester.view.devicePixelRatio = 3;
    addTearDown(tester.view.resetPhysicalSize);
    addTearDown(tester.view.resetDevicePixelRatio);
    await tester.pumpWidget(FinanzasApp(db: db));
    await tester.pumpAndSettle();

    for (final tab in ['Movimientos', 'Presupuestos', 'Reportes', 'Más']) {
      await tester.tap(find.text(tab).last);
      await tester.pumpAndSettle();
    }
  });

  testWidgets('los datos de ejemplo se muestran en el resumen',
      (tester) async {
    await db.seedDemo();
    await pumpApp(tester);

    for (var i = 0; i < 6; i++) {
      if (find.text('Supermercado').evaluate().isNotEmpty) break;
      await tester.drag(
        find.byType(Scrollable).first,
        const Offset(0, -420),
      );
      await tester.pumpAndSettle();
    }
    expect(find.text('Supermercado'), findsWidgets);
    expect(find.text('Salario'), findsWidgets);
  });
}

String todayForTest() {
  final now = DateTime.now();
  return '${now.year.toString().padLeft(4, '0')}-'
      '${now.month.toString().padLeft(2, '0')}-'
      '${now.day.toString().padLeft(2, '0')}';
}
