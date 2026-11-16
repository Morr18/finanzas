import 'dart:io';

import 'package:finanzas_mobile/data/database.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:sqflite_common_ffi/sqflite_ffi.dart';

void main() {
  sqfliteFfiInit();
  databaseFactory = databaseFactoryFfi;

  late Directory tempDir;
  late AppDatabase db;

  setUp(() async {
    tempDir = await Directory.systemTemp.createTemp('finanzas_mobile_test');
    db = await AppDatabase.open('${tempDir.path}/finanzas.db');
  });

  tearDown(() async {
    await db.close();
    await tempDir.delete(recursive: true);
  });

  group('inicialización', () {
    test('crea cuentas, categorías y ajustes por defecto', () async {
      final accounts = await db.accountBalances();
      expect(accounts.map((account) => account.name),
          containsAll(['Efectivo', 'Cuenta bancaria', 'Ahorros']));
      expect(await db.categories('ingreso'), isNotEmpty);
      expect(await db.categories('egreso'), hasLength(11));
      expect(db.baseCurrency, 'MXN');
      expect(db.numberFormat, 'en');
      expect(db.availableDisplayCurrencies, ['MXN']);
    });

    test('reabrir la base no duplica datos ni pierde ajustes', () async {
      await db.setSetting('theme', 'dark');
      await db.close();
      db = await AppDatabase.open('${tempDir.path}/finanzas.db');
      expect(await db.accountBalances(), hasLength(3));
      expect(db.setting('theme'), 'dark');
    });
  });

  group('movimientos y resumen', () {
    test('registra ingresos y gastos y calcula totales', () async {
      final accounts = await db.accountBalances();
      final cash = accounts.firstWhere((account) => account.name == 'Efectivo');
      final salary = (await db.categories('ingreso'))
          .firstWhere((category) => category.name == 'Salario');
      final food = (await db.categories('egreso'))
          .firstWhere((category) => category.name == 'Alimentación');

      await db.addTransaction(
        date: '2026-05-01',
        kind: 'ingreso',
        amount: 100000,
        categoryId: salary.id,
        accountId: cash.id,
        description: 'Nómina',
      );
      await db.addTransaction(
        date: '2026-05-03',
        kind: 'egreso',
        amount: 40000,
        categoryId: food.id,
        accountId: cash.id,
        description: 'Súper',
      );

      final summary = await db.summary('2026-05-01', '2026-05-31');
      expect(summary.income, 100000);
      expect(summary.expense, 40000);
      expect(summary.net, 60000);

      final balanced = (await db.accountBalances())
          .firstWhere((account) => account.id == cash.id);
      expect(balanced.balance, 60000);

      final list = await db.transactions(text: 'súper');
      expect(list, hasLength(1));
      expect(list.first.categoryName, 'Alimentación');
      expect(await db.transactionCount(), 2);
    });

    test('las reglas se aplican al registrar y a los existentes', () async {
      final accounts = await db.accountBalances();
      final cash = accounts.firstWhere((account) => account.name == 'Efectivo');
      final food = (await db.categories('egreso'))
          .firstWhere((category) => category.name == 'Alimentación');

      await db.addRule(matchText: 'super', categoryId: food.id);
      await db.addTransaction(
        date: '2026-06-01',
        kind: 'egreso',
        amount: 15000,
        accountId: cash.id,
        description: 'Compra en Super Central',
      );
      var list = await db.transactions();
      expect(list.first.categoryId, food.id);

      await db.addTransaction(
        date: '2026-06-02',
        kind: 'egreso',
        amount: 8000,
        accountId: cash.id,
        description: 'SUPER express',
        applyRules: false,
      );
      expect((await db.transactions()).first.categoryId, isNull);
      expect(await db.applyRulesToExisting(), 1);
      list = await db.transactions();
      expect(list.first.categoryId, food.id);
    });
  });

  group('monedas', () {
    test('convierte desde la moneda de la cuenta a la base', () async {
      await db.setFxRate('USD', '2026-05-10', 18);
      final usdId = await db.addAccount(
        name: 'Cuenta USD',
        kind: 'banco',
        initialBalance: 0,
        currency: 'USD',
      );
      await db.addTransaction(
        date: '2026-05-10',
        kind: 'ingreso',
        amount: 10000,
        accountId: usdId,
        description: 'Depósito en dólares',
      );
      final usd = (await db.accountBalances())
          .firstWhere((account) => account.id == usdId);
      expect(usd.balance, 10000);
      expect(usd.baseBalance, 180000);
      expect(await db.totalBalance(), 180000);
    });

    test('transferencias entre monedas calculan el monto destino', () async {
      await db.setFxRate('USD', '2026-05-10', 18);
      final usdId = await db.addAccount(
        name: 'Cuenta USD',
        kind: 'banco',
        initialBalance: 0,
        currency: 'USD',
      );
      final accounts = await db.accountBalances();
      final cash = accounts.firstWhere((account) => account.name == 'Efectivo');
      await db.addTransaction(
        date: '2026-05-10',
        kind: 'transferencia',
        amount: 180000,
        accountId: cash.id,
        transferAccountId: usdId,
        description: 'Compra de dólares',
      );
      final tx = (await db.transactions()).first;
      expect(tx.kind, 'transferencia');
      expect(tx.transferAmount, 10000);
      final usd = (await db.accountBalances())
          .firstWhere((account) => account.id == usdId);
      expect(usd.balance, 10000);
    });

    test('setBaseCurrency limpia las tasas de la nueva base', () async {
      await db.setFxRate('USD', '2026-05-10', 18);
      await db.setFxRate('EUR', '2026-05-10', 20);
      await db.setBaseCurrency('USD');
      expect(db.baseCurrency, 'USD');
      expect(db.currenciesWithRates, ['EUR']);
    });

    test('las tasas usan la más reciente anterior a la fecha', () async {
      await db.setFxRate('USD', '2026-01-01', 17);
      await db.setFxRate('USD', '2026-06-01', 19);
      expect(db.fxRateMicros('USD', '2026-03-01'), 17000000);
      expect(db.fxRateMicros('USD', '2026-07-01'), 19000000);
      expect(db.fxRateMicros('USD', '2025-01-01'), 19000000);
      expect(db.convertBetween(100000, '', 'USD', '2026-03-01'), 5882);
    });
  });

  group('presupuestos y recurrentes', () {
    test('calcula gastado y guarda límites', () async {
      final accounts = await db.accountBalances();
      final cash = accounts.firstWhere((account) => account.name == 'Efectivo');
      final food = (await db.categories('egreso'))
          .firstWhere((category) => category.name == 'Alimentación');
      await db.setBudget(food.id, 50000);
      await db.addTransaction(
        date: '2026-05-04',
        kind: 'egreso',
        amount: 30000,
        categoryId: food.id,
        accountId: cash.id,
      );
      final rows = await db.budgetsForMonth('2026-05');
      final row = rows.firstWhere((row) => row.categoryId == food.id);
      expect(row.budget, 50000);
      expect(row.spent, 30000);
      expect(row.ratio, closeTo(0.6, 0.0001));

      await db.setBudget(food.id, 0);
      expect(await db.budgetFor(food.id), 0);
    });

    test('genera recurrentes sin duplicar', () async {
      final accounts = await db.accountBalances();
      final cash = accounts.firstWhere((account) => account.name == 'Efectivo');
      await db.addRecurring(
        description: 'Renta',
        kind: 'egreso',
        amount: 500000,
        categoryId: null,
        accountId: cash.id,
        transferAccountId: null,
        frequency: 'mensual',
        day: 15,
        month: 1,
        startDate: '2026-01-15',
      );
      expect(await db.processRecurring(today: '2026-03-20'), 3);
      expect(await db.transactions(), hasLength(3));
      expect(await db.processRecurring(today: '2026-03-20'), 0);
      expect(await db.transactions(), hasLength(3));
      final rule = (await db.recurring()).first;
      expect(rule.lastRun, '2026-03-15');
    });
  });

  group('categorías y respaldo', () {
    test('archiva categorías con movimientos', () async {
      final accounts = await db.accountBalances();
      final cash = accounts.firstWhere((account) => account.name == 'Efectivo');
      final food = (await db.categories('egreso'))
          .firstWhere((category) => category.name == 'Alimentación');
      await db.addTransaction(
        date: '2026-05-05',
        kind: 'egreso',
        amount: 1000,
        categoryId: food.id,
        accountId: cash.id,
      );
      await db.deleteOrArchiveCategory(food.id);
      expect(
        (await db.categories('egreso')).map((category) => category.id),
        isNot(contains(food.id)),
      );
      final all = await db.categories('egreso', includeArchived: true);
      expect(all.firstWhere((category) => category.id == food.id).archived, isTrue);
      await db.setCategoryArchived(food.id, false);
      expect(
        (await db.categories('egreso')).map((category) => category.id),
        contains(food.id),
      );
    });

    test('exporta y restaura un respaldo completo', () async {
      final accounts = await db.accountBalances();
      final cash = accounts.firstWhere((account) => account.name == 'Efectivo');
      await db.addTransaction(
        date: '2026-05-06',
        kind: 'egreso',
        amount: 2500,
        accountId: cash.id,
        description: 'Café',
      );
      await db.setFxRate('USD', '2026-05-06', 18);
      final backup = await db.exportBackup();
      expect(backup, contains('"data"'));

      // También acepta respaldos del escritorio con la clave «data».
      await db.wipeAll();
      await db.restoreBackup(backup);
      expect(await db.transactions(), hasLength(1));

      await db.wipeAll();
      expect(await db.transactions(), isEmpty);

      await db.restoreBackup(backup);
      expect(await db.transactions(), hasLength(1));
      expect(db.fxRates, hasLength(1));
      expect(await db.accountBalances(), hasLength(3));
    });

    test('los datos de ejemplo crean seis meses de movimientos', () async {
      await db.seedDemo();
      expect(await db.transactions(), hasLength(18));
      expect(await db.transactions(limit: 100), isNotEmpty);
    });
  });
}
