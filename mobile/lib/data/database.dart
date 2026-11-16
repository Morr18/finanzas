import 'dart:convert';

import 'package:path/path.dart' as p;
import 'package:sqflite/sqflite.dart';

import 'models.dart';
import 'utils.dart';

const List<Map<String, dynamic>> _defaultCategories = [
  {'name': 'Salario', 'kind': 'ingreso', 'color': '#10b981'},
  {'name': 'Freelance', 'kind': 'ingreso', 'color': '#0ea5e9'},
  {'name': 'Inversiones', 'kind': 'ingreso', 'color': '#8b5cf6'},
  {'name': 'Ventas', 'kind': 'ingreso', 'color': '#f59e0b'},
  {'name': 'Otros ingresos', 'kind': 'ingreso', 'color': '#64748b'},
  {'name': 'Alimentación', 'kind': 'egreso', 'color': '#ef4444'},
  {'name': 'Vivienda', 'kind': 'egreso', 'color': '#f97316'},
  {'name': 'Transporte', 'kind': 'egreso', 'color': '#eab308'},
  {'name': 'Servicios', 'kind': 'egreso', 'color': '#06b6d4'},
  {'name': 'Salud', 'kind': 'egreso', 'color': '#ec4899'},
  {'name': 'Educación', 'kind': 'egreso', 'color': '#6366f1'},
  {'name': 'Ocio', 'kind': 'egreso', 'color': '#a855f7'},
  {'name': 'Compras', 'kind': 'egreso', 'color': '#14b8a6'},
  {'name': 'Ahorro e inversión', 'kind': 'egreso', 'color': '#22c55e'},
  {'name': 'Impuestos', 'kind': 'egreso', 'color': '#64748b'},
  {'name': 'Otros gastos', 'kind': 'egreso', 'color': '#94a3b8'},
];

const List<Map<String, dynamic>> _defaultAccounts = [
  {'name': 'Efectivo', 'kind': 'efectivo', 'color': '#10b981'},
  {'name': 'Cuenta bancaria', 'kind': 'banco', 'color': '#6366f1'},
  {'name': 'Ahorros', 'kind': 'ahorro', 'color': '#0ea5e9'},
];

const List<String> _schema = [
  '''CREATE TABLE IF NOT EXISTS settings (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
  )''',
  '''CREATE TABLE IF NOT EXISTS accounts (
    id              INTEGER PRIMARY KEY,
    name            TEXT NOT NULL COLLATE NOCASE UNIQUE,
    kind            TEXT NOT NULL DEFAULT 'efectivo',
    initial_balance INTEGER NOT NULL DEFAULT 0,
    color           TEXT NOT NULL DEFAULT '#6366f1',
    currency        TEXT NOT NULL DEFAULT '',
    archived        INTEGER NOT NULL DEFAULT 0,
    created_at      TEXT NOT NULL
  )''',
  '''CREATE TABLE IF NOT EXISTS categories (
    id       INTEGER PRIMARY KEY,
    name     TEXT NOT NULL COLLATE NOCASE,
    kind     TEXT NOT NULL CHECK (kind IN ('ingreso', 'egreso')),
    color    TEXT NOT NULL DEFAULT '#6366f1',
    archived INTEGER NOT NULL DEFAULT 0,
    UNIQUE (name, kind)
  )''',
  '''CREATE TABLE IF NOT EXISTS recurring (
    id                  INTEGER PRIMARY KEY,
    description         TEXT NOT NULL DEFAULT '',
    kind                TEXT NOT NULL CHECK (kind IN ('ingreso', 'egreso', 'transferencia')),
    amount              INTEGER NOT NULL CHECK (amount > 0),
    category_id         INTEGER REFERENCES categories(id) ON DELETE SET NULL,
    account_id          INTEGER REFERENCES accounts(id) ON DELETE SET NULL,
    transfer_account_id INTEGER REFERENCES accounts(id) ON DELETE SET NULL,
    frequency           TEXT NOT NULL CHECK (frequency IN ('mensual', 'quincenal', 'semanal', 'anual')),
    day                 INTEGER NOT NULL DEFAULT 1,
    month               INTEGER,
    start_date          TEXT NOT NULL,
    last_run            TEXT,
    active              INTEGER NOT NULL DEFAULT 1,
    created_at          TEXT NOT NULL
  )''',
  '''CREATE TABLE IF NOT EXISTS rules (
    id          INTEGER PRIMARY KEY,
    match_text  TEXT NOT NULL,
    category_id INTEGER REFERENCES categories(id) ON DELETE SET NULL,
    account_id  INTEGER REFERENCES accounts(id) ON DELETE SET NULL,
    active      INTEGER NOT NULL DEFAULT 1,
    created_at  TEXT NOT NULL
  )''',
  '''CREATE TABLE IF NOT EXISTS fx_rates (
    currency    TEXT NOT NULL,
    date        TEXT NOT NULL,
    rate_micros INTEGER NOT NULL CHECK (rate_micros > 0),
    PRIMARY KEY (currency, date)
  )''',
  '''CREATE TABLE IF NOT EXISTS transactions (
    id                  INTEGER PRIMARY KEY,
    date                TEXT NOT NULL,
    kind                TEXT NOT NULL CHECK (kind IN ('ingreso', 'egreso', 'transferencia')),
    amount              INTEGER NOT NULL CHECK (amount > 0),
    transfer_amount     INTEGER,
    category_id         INTEGER REFERENCES categories(id) ON DELETE SET NULL,
    account_id          INTEGER REFERENCES accounts(id) ON DELETE SET NULL,
    transfer_account_id INTEGER REFERENCES accounts(id) ON DELETE SET NULL,
    recurring_id        INTEGER REFERENCES recurring(id) ON DELETE SET NULL,
    description         TEXT NOT NULL DEFAULT '',
    notes               TEXT NOT NULL DEFAULT '',
    created_at          TEXT NOT NULL
  )''',
  'CREATE INDEX IF NOT EXISTS idx_tx_date ON transactions (date)',
  'CREATE INDEX IF NOT EXISTS idx_tx_category ON transactions (category_id)',
  'CREATE INDEX IF NOT EXISTS idx_tx_account ON transactions (account_id)',
  '''CREATE TABLE IF NOT EXISTS budgets (
    category_id INTEGER PRIMARY KEY REFERENCES categories(id) ON DELETE CASCADE,
    amount      INTEGER NOT NULL DEFAULT 0
  )''',
  'CREATE INDEX IF NOT EXISTS idx_tx_recurring ON transactions (recurring_id)',
  '''CREATE UNIQUE INDEX IF NOT EXISTS idx_tx_recurring_date
    ON transactions (recurring_id, date) WHERE recurring_id IS NOT NULL''',
];

const String _txSelect = '''
SELECT t.*, c.name AS category_name, c.color AS category_color,
       a.name AS account_name, a.currency AS account_currency,
       d.name AS transfer_account_name, d.currency AS transfer_currency
FROM transactions t
LEFT JOIN categories c ON c.id = t.category_id
LEFT JOIN accounts a ON a.id = t.account_id
LEFT JOIN accounts d ON d.id = t.transfer_account_id
''';

class _Where {
  const _Where(this.clause, this.args);
  final String clause;
  final List<Object?> args;
}

class AppDatabase {
  AppDatabase._(this._db);

  final Database _db;
  final Map<String, String> _settings = {};
  List<FxRate> _rates = [];

  static const int _version = 1;

  static Future<AppDatabase> open([String? path]) async {
    final target = path ?? p.join(await getDatabasesPath(), 'finanzas.db');
    final db = await openDatabase(
      target,
      version: _version,
      onConfigure: (db) async {
        await db.execute('PRAGMA foreign_keys = ON');
      },
      onCreate: (db, version) => _createAll(db),
      onUpgrade: (db, oldVersion, newVersion) => _createAll(db),
    );
    final store = AppDatabase._(db);
    await store._ensureSchema();
    await store.loadCaches();
    return store;
  }

  static Future<void> _createAll(Database db) async {
    for (final statement in _schema) {
      await db.execute(statement);
    }
    await _ensureColumn(
      db,
      'accounts',
      'currency',
      "TEXT NOT NULL DEFAULT ''",
    );
    await _ensureColumn(
      db,
      'transactions',
      'recurring_id',
      'INTEGER REFERENCES recurring(id) ON DELETE SET NULL',
    );
    await _seedDefaults(db);
  }

  static Future<void> _ensureColumn(
    Database db,
    String table,
    String column,
    String definition,
  ) async {
    final rows = await db.rawQuery('PRAGMA table_info($table)');
    if (!rows.any((row) => row['name'] == column)) {
      await db.execute('ALTER TABLE $table ADD COLUMN $column $definition');
    }
  }

  static Future<void> _seedDefaults(Database db) async {
    final now = DateTime.now().toIso8601String();
    final accountCount = Sqflite.firstIntValue(
          await db.rawQuery('SELECT COUNT(*) FROM accounts'),
        ) ??
        0;
    if (accountCount == 0) {
      for (final account in _defaultAccounts) {
        await db.insert(
          'accounts',
          {
            'name': account['name'],
            'kind': account['kind'],
            'initial_balance': 0,
            'color': account['color'],
            'currency': '',
            'archived': 0,
            'created_at': now,
          },
          conflictAlgorithm: ConflictAlgorithm.ignore,
        );
      }
    }
    final categoryCount = Sqflite.firstIntValue(
          await db.rawQuery('SELECT COUNT(*) FROM categories'),
        ) ??
        0;
    if (categoryCount == 0) {
      for (final category in _defaultCategories) {
        await db.insert(
          'categories',
          {
            'name': category['name'],
            'kind': category['kind'],
            'color': category['color'],
            'archived': 0,
          },
          conflictAlgorithm: ConflictAlgorithm.ignore,
        );
      }
    }
    const defaults = {
      'base_currency': 'MXN',
      'display_currency': '',
      'theme': 'light',
      'number_format': 'en',
      'currency': '\$',
    };
    for (final entry in defaults.entries) {
      await db.insert(
        'settings',
        {'key': entry.key, 'value': entry.value},
        conflictAlgorithm: ConflictAlgorithm.ignore,
      );
    }
  }

  Future<void> _ensureSchema() async {
    await _createAll(_db);
  }

  Future<void> loadCaches() async {
    _settings
      ..clear()
      ..addEntries(
        (await _db.query('settings')).map(
          (row) => MapEntry('${row['key']}', '${row['value']}'),
        ),
      );
    _rates = (await _db.query('fx_rates', orderBy: 'currency, date DESC'))
        .map(FxRate.fromMap)
        .toList();
  }

  Future<void> close() => _db.close();

  Database get raw => _db;

  // ---------------------------------------------------------------- ajustes
  String setting(String key, [String fallback = '']) =>
      _settings[key] ?? fallback;

  Future<void> setSetting(String key, String value) async {
    _settings[key] = value;
    await _db.insert(
      'settings',
      {'key': key, 'value': value},
      conflictAlgorithm: ConflictAlgorithm.replace,
    );
  }

  String get baseCurrency => (setting('base_currency', 'MXN').trim().isEmpty
          ? 'MXN'
          : setting('base_currency', 'MXN'))
      .toUpperCase();

  String get numberFormat =>
      setting('number_format', 'en') == 'es' ? 'es' : 'en';

  bool get isSpanishNumbers => numberFormat == 'es';

  String get currencySymbolSetting => setting('currency', '\$');

  Future<void> setBaseCurrency(String code) async {
    final cleaned = normalizeCurrency(code);
    if (cleaned == baseCurrency) return;
    await _db.delete('fx_rates', where: 'currency = ?', whereArgs: [cleaned]);
    await setSetting('base_currency', cleaned);
    await loadRates();
  }

  Future<void> loadRates() async {
    _rates = (await _db.query('fx_rates', orderBy: 'currency, date DESC'))
        .map(FxRate.fromMap)
        .toList();
  }

  List<FxRate> get fxRates => List.unmodifiable(_rates);

  List<String> get currenciesWithRates =>
      _rates.map((rate) => rate.currency).toSet().toList()..sort();

  List<String> get availableDisplayCurrencies {
    final base = baseCurrency;
    final codes = currenciesWithRates.where((code) => code != base).toList();
    return [base, ...codes];
  }

  bool get hasForeignAccounts {
    // Se consulta en la vista que lo necesita mediante hasForeignAccountsAsync.
    return false;
  }

  Future<bool> hasForeignAccountsAsync() async {
    final rows = await _db.rawQuery(
      'SELECT EXISTS(SELECT 1 FROM accounts WHERE archived = 0'
      " AND currency <> '' AND currency <> ?) AS found",
      [baseCurrency],
    );
    return (rows.first['found'] as int? ?? 0) == 1;
  }

  Future<List<String>> missingRates() async {
    final rows = await _db.rawQuery(
      'SELECT DISTINCT currency FROM accounts WHERE archived = 0'
      " AND currency <> '' AND currency <> ?"
      ' AND currency NOT IN (SELECT currency FROM fx_rates)',
      [baseCurrency],
    );
    return rows.map((row) => '${row['currency']}').toList();
  }

  FxRate? _latestRate(String currency, String? date) {
    final code = currency.trim().toUpperCase();
    if (code.isEmpty) return null;
    final candidates = _rates.where((rate) => rate.currency == code).toList();
    if (candidates.isEmpty) return null;
    final target = date ?? todayIso();
    final eligible =
        candidates.where((rate) => rate.date.compareTo(target) <= 0).toList();
    if (eligible.isNotEmpty) {
      eligible.sort((a, b) => b.date.compareTo(a.date));
      return eligible.first;
    }
    candidates.sort((a, b) => b.date.compareTo(a.date));
    return candidates.first;
  }

  int fxRateMicros(String currency, [String? date]) =>
      _latestRate(currency, date)?.rateMicros ?? 1000000;

  int toBase(int cents, String currency, [String? date]) {
    if (currency.trim().isEmpty) return cents;
    return roundDiv(cents * fxRateMicros(currency, date), 1000000);
  }

  int fromBase(int cents, String currency, [String? date]) {
    if (currency.trim().isEmpty) return cents;
    final rate = fxRateMicros(currency, date);
    return rate == 0 ? cents : roundDiv(cents * 1000000, rate);
  }

  int convertBetween(int cents, String from, String to, [String? date]) {
    final source = from.trim().toUpperCase();
    final target = to.trim().toUpperCase();
    if (source == target) return cents;
    final base = toBase(cents, source, date);
    return fromBase(base, target, date);
  }

  Future<int> setFxRate(String currency, String date, double rate) async {
    final code = normalizeCurrency(currency);
    if (code == baseCurrency) {
      throw ArgumentError('Esa es la moneda base; no necesita tipo de cambio.');
    }
    if (rate <= 0) {
      throw ArgumentError('El tipo de cambio debe ser mayor que cero.');
    }
    final micros = (rate * 1000000).round();
    await _db.insert(
      'fx_rates',
      {'currency': code, 'date': date, 'rate_micros': micros},
      conflictAlgorithm: ConflictAlgorithm.replace,
    );
    await loadRates();
    return micros;
  }

  Future<void> deleteFxRate(String currency, String date) async {
    await _db.delete(
      'fx_rates',
      where: 'currency = ? AND date = ?',
      whereArgs: [currency, date],
    );
    await loadRates();
  }

  // ---------------------------------------------------------------- cuentas
  Future<List<AccountBalance>> accountBalances() async {
    final rows = await _db.rawQuery('''
      SELECT a.id, a.name, a.kind, a.color, a.initial_balance, a.archived, a.currency,
             a.initial_balance
             + COALESCE((SELECT SUM(amount) FROM transactions t
                         WHERE t.kind = 'ingreso' AND t.account_id = a.id), 0)
             - COALESCE((SELECT SUM(amount) FROM transactions t
                         WHERE t.kind = 'egreso' AND t.account_id = a.id), 0)
             - COALESCE((SELECT SUM(amount) FROM transactions t
                         WHERE t.kind = 'transferencia' AND t.account_id = a.id), 0)
             + COALESCE((SELECT SUM(COALESCE(t.transfer_amount, t.amount))
                         FROM transactions t
                         WHERE t.kind = 'transferencia'
                         AND t.transfer_account_id = a.id), 0)
             AS balance
      FROM accounts a
      WHERE a.archived = 0
      ORDER BY a.name COLLATE NOCASE
    ''');
    final today = todayIso();
    return rows.map((row) {
      final copy = Map<String, dynamic>.from(row);
      final balance = (row['balance'] as int?) ?? 0;
      copy['base_balance'] = toBase(balance, '${row['currency'] ?? ''}', today);
      return AccountBalance.fromMap(copy);
    }).toList();
  }

  Future<int> totalBalance() async {
    final accounts = await accountBalances();
    return accounts.fold<int>(0, (sum, account) => sum + account.baseBalance);
  }

  Future<int> accountUsage(int accountId) async {
    final rows = await _db.rawQuery(
      'SELECT COUNT(*) AS n FROM transactions'
      ' WHERE account_id = ? OR transfer_account_id = ?',
      [accountId, accountId],
    );
    return (rows.first['n'] as int?) ?? 0;
  }

  Future<int> addAccount({
    required String name,
    required String kind,
    required int initialBalance,
    String color = '#6366f1',
    String currency = '',
  }) async {
    final cleaned = normalizeCurrency(currency);
    final code = cleaned == baseCurrency ? '' : cleaned;
    final id = await _db.insert('accounts', {
      'name': name.trim(),
      'kind': kind,
      'initial_balance': initialBalance,
      'color': color,
      'currency': code,
      'archived': 0,
      'created_at': DateTime.now().toIso8601String(),
    });
    return id;
  }

  Future<void> updateAccount(
    int id, {
    required String name,
    required String kind,
    required int initialBalance,
    String color = '#6366f1',
    String currency = '',
  }) async {
    final cleaned = normalizeCurrency(currency);
    final code = cleaned == baseCurrency ? '' : cleaned;
    await _db.update(
      'accounts',
      {
        'name': name.trim(),
        'kind': kind,
        'initial_balance': initialBalance,
        'color': color,
        'currency': code,
      },
      where: 'id = ?',
      whereArgs: [id],
    );
  }

  Future<void> deleteAccount(int id) async {
    await _db.delete('accounts', where: 'id = ?', whereArgs: [id]);
  }

  // ---------------------------------------------------------------- categorías
  Future<List<Category>> categories(
    String kind, {
    bool includeArchived = false,
  }) async {
    final where =
        includeArchived ? 'c.kind = ?' : 'c.kind = ? AND c.archived = 0';
    final rows = await _db.rawQuery('''
      SELECT c.*, (SELECT COUNT(*) FROM transactions t WHERE t.category_id = c.id) AS usage
      FROM categories c WHERE $where ORDER BY c.name COLLATE NOCASE
    ''', [kind]);
    return rows.map(Category.fromMap).toList();
  }

  Future<Category?> getCategory(int id) async {
    final rows =
        await _db.query('categories', where: 'id = ?', whereArgs: [id]);
    return rows.isEmpty ? null : Category.fromMap(rows.first);
  }

  Future<int> addCategory(String name, String kind, String color) async {
    return _db.insert('categories', {
      'name': name.trim(),
      'kind': kind,
      'color': color,
      'archived': 0,
    });
  }

  Future<void> updateCategory(
      int id, String name, String kind, String color) async {
    await _db.update(
      'categories',
      {'name': name.trim(), 'kind': kind, 'color': color},
      where: 'id = ?',
      whereArgs: [id],
    );
  }

  Future<void> setCategoryArchived(int id, bool archived) async {
    await _db.update(
      'categories',
      {'archived': archived ? 1 : 0},
      where: 'id = ?',
      whereArgs: [id],
    );
  }

  Future<void> deleteOrArchiveCategory(int id) async {
    final usage = await _db.rawQuery(
      'SELECT COUNT(*) AS n FROM transactions WHERE category_id = ?',
      [id],
    );
    if (((usage.first['n'] as int?) ?? 0) > 0) {
      await _db.update(
        'categories',
        {'archived': 1},
        where: 'id = ?',
        whereArgs: [id],
      );
    } else {
      await _db.delete('categories', where: 'id = ?', whereArgs: [id]);
    }
  }

  // ---------------------------------------------------------------- movimientos
  _Where _txWhere({
    String? text,
    String? kind,
    int? categoryId,
    int? accountId,
    String? dateFrom,
    String? dateTo,
  }) {
    final clauses = <String>[];
    final args = <Object?>[];
    final needle = (text ?? '').trim();
    if (needle.isNotEmpty) {
      final like = '%$needle%';
      clauses.add('(t.description LIKE ? OR t.notes LIKE ? OR c.name LIKE ?'
          ' OR a.name LIKE ? OR d.name LIKE ?)');
      args.addAll([like, like, like, like, like]);
    }
    if (kind != null && kind.isNotEmpty) {
      clauses.add('t.kind = ?');
      args.add(kind);
    }
    if (categoryId != null) {
      clauses.add('t.category_id = ?');
      args.add(categoryId);
    }
    if (accountId != null) {
      clauses.add('(t.account_id = ? OR t.transfer_account_id = ?)');
      args.addAll([accountId, accountId]);
    }
    if ((dateFrom ?? '').isNotEmpty) {
      clauses.add('t.date >= ?');
      args.add(dateFrom);
    }
    if ((dateTo ?? '').isNotEmpty) {
      clauses.add('t.date <= ?');
      args.add(dateTo);
    }
    return _Where(
      clauses.isEmpty ? '' : 'WHERE ${clauses.join(' AND ')}',
      args,
    );
  }

  Future<List<Tx>> transactions({
    String? text,
    String? kind,
    int? categoryId,
    int? accountId,
    String? dateFrom,
    String? dateTo,
    int limit = 100,
    int offset = 0,
  }) async {
    final where = _txWhere(
      text: text,
      kind: kind,
      categoryId: categoryId,
      accountId: accountId,
      dateFrom: dateFrom,
      dateTo: dateTo,
    );
    final rows = await _db.rawQuery(
      '$_txSelect ${where.clause} ORDER BY t.date DESC, t.id DESC LIMIT ? OFFSET ?',
      [...where.args, limit, offset],
    );
    return rows.map(Tx.fromMap).toList();
  }

  Future<int> transactionCount({
    String? text,
    String? kind,
    int? categoryId,
    int? accountId,
    String? dateFrom,
    String? dateTo,
  }) async {
    final where = _txWhere(
      text: text,
      kind: kind,
      categoryId: categoryId,
      accountId: accountId,
      dateFrom: dateFrom,
      dateTo: dateTo,
    );
    final rows = await _db.rawQuery(
      '''SELECT COUNT(*) AS n FROM transactions t
         LEFT JOIN categories c ON c.id = t.category_id
         LEFT JOIN accounts a ON a.id = t.account_id
         LEFT JOIN accounts d ON d.id = t.transfer_account_id
         ${where.clause}''',
      where.args,
    );
    return (rows.first['n'] as int?) ?? 0;
  }

  Future<CategorySummary> transactionTotals({
    String? text,
    String? kind,
    int? categoryId,
    int? accountId,
    String? dateFrom,
    String? dateTo,
  }) async {
    final where = _txWhere(
      text: text,
      kind: kind,
      categoryId: categoryId,
      accountId: accountId,
      dateFrom: dateFrom,
      dateTo: dateTo,
    );
    final rows = await _db.rawQuery(
      '''SELECT t.kind, t.amount, t.date, a.currency
         FROM transactions t
         LEFT JOIN categories c ON c.id = t.category_id
         LEFT JOIN accounts a ON a.id = t.account_id
         LEFT JOIN accounts d ON d.id = t.transfer_account_id
         ${where.clause}''',
      where.args,
    );
    var income = 0;
    var expense = 0;
    for (final row in rows) {
      final value = toBase(
        (row['amount'] as int?) ?? 0,
        '${row['currency'] ?? ''}',
        '${row['date'] ?? ''}',
      );
      if (row['kind'] == 'ingreso') income += value;
      if (row['kind'] == 'egreso') expense += value;
    }
    return CategorySummary(income: income, expense: expense);
  }

  Future<int> addTransaction({
    required String date,
    required String kind,
    required int amount,
    int? categoryId,
    int? accountId,
    int? transferAccountId,
    String description = '',
    String notes = '',
    int? transferAmount,
    int? recurringId,
    bool applyRules = true,
  }) async {
    if (amount <= 0) {
      throw ArgumentError('El monto debe ser mayor que cero.');
    }
    if (!const ['ingreso', 'egreso', 'transferencia'].contains(kind)) {
      throw ArgumentError('Tipo de movimiento inválido.');
    }
    if (kind == 'transferencia') {
      categoryId = null;
      transferAmount ??= await transferAmountFor(
        amount,
        accountId,
        transferAccountId,
        date,
      );
    } else if (applyRules) {
      final rule = await matchRule(description, notes, kind);
      if (rule != null) {
        categoryId = rule.categoryId ?? categoryId;
        accountId = rule.accountId ?? accountId;
      }
    }
    final id = await _db.insert('transactions', {
      'date': date,
      'kind': kind,
      'amount': amount,
      'transfer_amount': transferAmount,
      'category_id': categoryId,
      'account_id': accountId,
      'transfer_account_id': transferAccountId,
      'recurring_id': recurringId,
      'description': description.trim(),
      'notes': notes.trim(),
      'created_at': DateTime.now().toIso8601String(),
    });
    return id;
  }

  Future<void> updateTransaction(
    int id, {
    required String date,
    required String kind,
    required int amount,
    int? categoryId,
    int? accountId,
    int? transferAccountId,
    String description = '',
    String notes = '',
    int? transferAmount,
    int? recurringId,
  }) async {
    if (amount <= 0) {
      throw ArgumentError('El monto debe ser mayor que cero.');
    }
    if (kind == 'transferencia') {
      categoryId = null;
      transferAmount ??= await transferAmountFor(
        amount,
        accountId,
        transferAccountId,
        date,
      );
    }
    await _db.update(
      'transactions',
      {
        'date': date,
        'kind': kind,
        'amount': amount,
        'transfer_amount': transferAmount,
        'category_id': categoryId,
        'account_id': accountId,
        'transfer_account_id': transferAccountId,
        'recurring_id': recurringId,
        'description': description.trim(),
        'notes': notes.trim(),
      },
      where: 'id = ?',
      whereArgs: [id],
    );
  }

  Future<void> deleteTransaction(int id) async {
    await _db.delete('transactions', where: 'id = ?', whereArgs: [id]);
  }

  Future<int?> transferAmountFor(
    int amount,
    int? accountId,
    int? transferAccountId,
    String date,
  ) async {
    if (accountId == null || transferAccountId == null) return null;
    final rows = await _db.query(
      'accounts',
      columns: ['id', 'currency'],
      where: 'id IN (?, ?)',
      whereArgs: [accountId, transferAccountId],
    );
    String currencyOf(int id) => '${rows.firstWhere(
          (row) => row['id'] == id,
          orElse: () => {'currency': ''},
        )['currency'] ?? ''}';
    final source = currencyOf(accountId);
    final target = currencyOf(transferAccountId);
    if (source.toUpperCase() == target.toUpperCase()) return null;
    return convertBetween(amount, source, target, date);
  }

  Future<bool> hasTransactions() async {
    final rows = await _db.rawQuery('SELECT COUNT(*) AS n FROM transactions');
    return ((rows.first['n'] as int?) ?? 0) > 0;
  }

  // ---------------------------------------------------------------- resumen
  Future<CategorySummary> summary(String dateFrom, String dateTo) async {
    final rows = await _db.rawQuery(
      '''SELECT t.kind, t.amount, t.date, a.currency
         FROM transactions t LEFT JOIN accounts a ON a.id = t.account_id
         WHERE t.date BETWEEN ? AND ?''',
      [dateFrom, dateTo],
    );
    var income = 0;
    var expense = 0;
    for (final row in rows) {
      final value = toBase(
        (row['amount'] as int?) ?? 0,
        '${row['currency'] ?? ''}',
        '${row['date'] ?? ''}',
      );
      if (row['kind'] == 'ingreso') income += value;
      if (row['kind'] == 'egreso') expense += value;
    }
    return CategorySummary(income: income, expense: expense);
  }

  Future<List<MonthlyPoint>> monthlySeries({int months = 6}) async {
    final keys = recentMonthKeys(months);
    final start = monthBounds(keys.first).$1;
    final end = monthBounds(keys.last).$2;
    final rows = await _db.rawQuery(
      '''SELECT t.kind, t.amount, t.date, a.currency
         FROM transactions t LEFT JOIN accounts a ON a.id = t.account_id
         WHERE t.date BETWEEN ? AND ?''',
      [start, end],
    );
    final income = <String, int>{};
    final expense = <String, int>{};
    for (final row in rows) {
      final key = '${row['date']}'.substring(0, 7);
      final value = toBase(
        (row['amount'] as int?) ?? 0,
        '${row['currency'] ?? ''}',
        '${row['date'] ?? ''}',
      );
      if (row['kind'] == 'ingreso') {
        income[key] = (income[key] ?? 0) + value;
      } else if (row['kind'] == 'egreso') {
        expense[key] = (expense[key] ?? 0) + value;
      }
    }
    return keys
        .map((key) => MonthlyPoint(
              key: key,
              income: income[key] ?? 0,
              expense: expense[key] ?? 0,
            ))
        .toList();
  }

  Future<List<CategoryTotal>> categoryTotals(
    String kind,
    String dateFrom,
    String dateTo,
  ) async {
    final rows = await _db.rawQuery(
      '''SELECT COALESCE(c.id, -1) AS id, COALESCE(c.name, 'Sin categoría') AS name,
                COALESCE(c.color, '#94a3b8') AS color,
                t.amount, t.date, a.currency
         FROM transactions t
         LEFT JOIN categories c ON c.id = t.category_id
         LEFT JOIN accounts a ON a.id = t.account_id
         WHERE t.kind = ? AND t.date BETWEEN ? AND ?''',
      [kind, dateFrom, dateTo],
    );
    final totals = <int, CategoryTotal>{};
    for (final row in rows) {
      final id = (row['id'] as int?) ?? -1;
      final value = toBase(
        (row['amount'] as int?) ?? 0,
        '${row['currency'] ?? ''}',
        '${row['date'] ?? ''}',
      );
      final current = totals[id];
      totals[id] = CategoryTotal(
        id: id,
        name: '${row['name'] ?? 'Sin categoría'}',
        color: '${row['color'] ?? '#94a3b8'}',
        total: (current?.total ?? 0) + value,
        count: (current?.count ?? 0) + 1,
      );
    }
    final list = totals.values.toList()
      ..sort((a, b) => b.total.compareTo(a.total));
    return list;
  }

  Future<List<YearRow>> yearTotals(int year) async {
    final rows = await _db.rawQuery(
      '''SELECT t.kind, t.amount, t.date, a.currency
         FROM transactions t LEFT JOIN accounts a ON a.id = t.account_id
         WHERE substr(t.date, 1, 4) = ?''',
      ['$year'],
    );
    final income = <int, int>{};
    final expense = <int, int>{};
    for (final row in rows) {
      final month = int.tryParse('${row['date']}'.substring(5, 7)) ?? 1;
      final value = toBase(
        (row['amount'] as int?) ?? 0,
        '${row['currency'] ?? ''}',
        '${row['date'] ?? ''}',
      );
      if (row['kind'] == 'ingreso') {
        income[month] = (income[month] ?? 0) + value;
      } else if (row['kind'] == 'egreso') {
        expense[month] = (expense[month] ?? 0) + value;
      }
    }
    return List.generate(12, (index) {
      final month = index + 1;
      return YearRow(
        month: month,
        key: '$year-${month.toString().padLeft(2, '0')}',
        income: income[month] ?? 0,
        expense: expense[month] ?? 0,
      );
    });
  }

  Future<List<int>> yearsWithData() async {
    final rows = await _db.rawQuery(
      'SELECT DISTINCT substr(date, 1, 4) AS y FROM transactions ORDER BY y DESC',
    );
    final years = rows
        .map((row) => int.tryParse('${row['y']}'))
        .whereType<int>()
        .toList();
    final current = DateTime.now().year;
    if (!years.contains(current)) years.insert(0, current);
    final unique = years.toSet().toList()..sort((a, b) => b.compareTo(a));
    return unique;
  }

  // ---------------------------------------------------------------- presupuestos
  Future<List<BudgetRow>> budgetsForMonth(String key) async {
    final bounds = monthBounds(key);
    final categories = await _db.rawQuery('''
      SELECT c.id, c.name, c.color, COALESCE(b.amount, 0) AS budget
      FROM categories c LEFT JOIN budgets b ON b.category_id = c.id
      WHERE c.kind = 'egreso' AND c.archived = 0
      ORDER BY CASE WHEN COALESCE(b.amount, 0) = 0 THEN 1 ELSE 0 END,
               c.name COLLATE NOCASE
    ''');
    final expenses = await _db.rawQuery(
      '''SELECT t.category_id, t.amount, t.date, a.currency
         FROM transactions t LEFT JOIN accounts a ON a.id = t.account_id
         WHERE t.kind = 'egreso' AND t.date BETWEEN ? AND ?''',
      [bounds.$1, bounds.$2],
    );
    final spent = <int, int>{};
    for (final row in expenses) {
      final id = (row['category_id'] as int?) ?? -1;
      spent[id] = (spent[id] ?? 0) +
          toBase(
            (row['amount'] as int?) ?? 0,
            '${row['currency'] ?? ''}',
            '${row['date'] ?? ''}',
          );
    }
    return categories.map((row) {
      final id = (row['id'] as int?) ?? 0;
      return BudgetRow(
        categoryId: id,
        name: '${row['name'] ?? ''}',
        color: '${row['color'] ?? '#6366f1'}',
        budget: (row['budget'] as int?) ?? 0,
        spent: spent[id] ?? 0,
      );
    }).toList();
  }

  Future<int> budgetFor(int categoryId) async {
    final rows = await _db.query(
      'budgets',
      where: 'category_id = ?',
      whereArgs: [categoryId],
    );
    return rows.isEmpty ? 0 : (rows.first['amount'] as int?) ?? 0;
  }

  Future<void> setBudget(int categoryId, int amount) async {
    if (amount <= 0) {
      await _db
          .delete('budgets', where: 'category_id = ?', whereArgs: [categoryId]);
      return;
    }
    await _db.insert(
      'budgets',
      {'category_id': categoryId, 'amount': amount},
      conflictAlgorithm: ConflictAlgorithm.replace,
    );
  }

  // ---------------------------------------------------------------- recurrentes
  Future<List<RecurringRule>> recurring() async {
    final rows = await _db.rawQuery('''
      SELECT r.*, c.name AS category_name, a.name AS account_name,
             a.currency AS account_currency, d.name AS transfer_account_name
      FROM recurring r
      LEFT JOIN categories c ON c.id = r.category_id
      LEFT JOIN accounts a ON a.id = r.account_id
      LEFT JOIN accounts d ON d.id = r.transfer_account_id
      ORDER BY r.active DESC, r.id DESC
    ''');
    return rows.map(RecurringRule.fromMap).toList();
  }

  Future<int> addRecurring({
    required String description,
    required String kind,
    required int amount,
    required int? categoryId,
    required int? accountId,
    required int? transferAccountId,
    required String frequency,
    required int day,
    required int month,
    required String startDate,
    bool active = true,
  }) async {
    if (amount <= 0) throw ArgumentError('El monto debe ser mayor que cero.');
    return _db.insert('recurring', {
      'description': description.trim(),
      'kind': kind,
      'amount': amount,
      'category_id': kind == 'transferencia' ? null : categoryId,
      'account_id': accountId,
      'transfer_account_id': kind == 'transferencia' ? transferAccountId : null,
      'frequency': frequency,
      'day': day,
      'month': month,
      'start_date': startDate,
      'last_run': null,
      'active': active ? 1 : 0,
      'created_at': DateTime.now().toIso8601String(),
    });
  }

  Future<void> updateRecurring(
    int id, {
    required String description,
    required String kind,
    required int amount,
    required int? categoryId,
    required int? accountId,
    required int? transferAccountId,
    required String frequency,
    required int day,
    required int month,
    required String startDate,
    required bool active,
  }) async {
    await _db.update(
      'recurring',
      {
        'description': description.trim(),
        'kind': kind,
        'amount': amount,
        'category_id': kind == 'transferencia' ? null : categoryId,
        'account_id': accountId,
        'transfer_account_id':
            kind == 'transferencia' ? transferAccountId : null,
        'frequency': frequency,
        'day': day,
        'month': month,
        'start_date': startDate,
        'active': active ? 1 : 0,
      },
      where: 'id = ?',
      whereArgs: [id],
    );
  }

  Future<void> deleteRecurring(int id) async {
    await _db.delete('recurring', where: 'id = ?', whereArgs: [id]);
  }

  Future<void> setRecurringActive(int id, bool active) async {
    await _db.update(
      'recurring',
      {'active': active ? 1 : 0},
      where: 'id = ?',
      whereArgs: [id],
    );
  }

  Future<String?> nextOccurrence(RecurringRule rule, {DateTime? after}) async =>
      nextRecurringDate(rule.toRuleMap(), after: after);

  Future<int> processRecurring({String? today}) async {
    final until = today == null
        ? DateTime.now()
        : (DateTime.tryParse(today) ?? DateTime.now());
    final rules = await recurring();
    var created = 0;
    for (final rule in rules.where((rule) => rule.active)) {
      if (rule.accountId == null || rule.startDate.isEmpty) continue;
      final start = DateTime.tryParse(rule.startDate);
      if (start == null) continue;
      final after = rule.lastRun != null
          ? (DateTime.tryParse(rule.lastRun!) ?? start)
              .add(const Duration(days: 1))
          : start;
      final dates = iterRecurringDates(rule.toRuleMap(), after, until).toList();
      if (dates.isEmpty) continue;
      var description = rule.description.trim();
      if (description.isEmpty) {
        if (rule.kind == 'transferencia') {
          description = 'Transferencia recurrente';
        } else {
          description = rule.categoryName.isEmpty
              ? 'Movimiento recurrente'
              : rule.categoryName;
        }
      }
      for (final occurrence in dates) {
        final occurrenceIso = isoDate(occurrence);
        final transferAmount = rule.kind == 'transferencia'
            ? await transferAmountFor(
                rule.amount,
                rule.accountId,
                rule.transferAccountId,
                occurrenceIso,
              )
            : null;
        try {
          final inserted = await _db.insert(
            'transactions',
            {
              'date': occurrenceIso,
              'kind': rule.kind,
              'amount': rule.amount,
              'transfer_amount': transferAmount,
              'category_id':
                  rule.kind == 'transferencia' ? null : rule.categoryId,
              'account_id': rule.accountId,
              'transfer_account_id':
                  rule.kind == 'transferencia' ? rule.transferAccountId : null,
              'recurring_id': rule.id,
              'description': description,
              'notes': '',
              'created_at': DateTime.now().toIso8601String(),
            },
            conflictAlgorithm: ConflictAlgorithm.ignore,
          );
          if (inserted != 0) created++;
        } on DatabaseException {
          // La ocurrencia ya existía.
        }
      }
      await _db.update(
        'recurring',
        {'last_run': isoDate(dates.last)},
        where: 'id = ?',
        whereArgs: [rule.id],
      );
    }
    return created;
  }

  // ---------------------------------------------------------------- reglas
  Future<List<RuleRecord>> rules() async {
    final rows = await _db.rawQuery('''
      SELECT r.*, c.name AS category_name, a.name AS account_name
      FROM rules r
      LEFT JOIN categories c ON c.id = r.category_id
      LEFT JOIN accounts a ON a.id = r.account_id
      ORDER BY r.id
    ''');
    return rows.map(RuleRecord.fromMap).toList();
  }

  Future<int> addRule({
    required String matchText,
    int? categoryId,
    int? accountId,
    bool active = true,
  }) async {
    if (matchText.trim().isEmpty) {
      throw ArgumentError('Escribe el texto que debe contener el movimiento.');
    }
    if (categoryId == null && accountId == null) {
      throw ArgumentError('Elige una categoría o una cuenta para la regla.');
    }
    return _db.insert('rules', {
      'match_text': matchText.trim(),
      'category_id': categoryId,
      'account_id': accountId,
      'active': active ? 1 : 0,
      'created_at': DateTime.now().toIso8601String(),
    });
  }

  Future<void> updateRule(
    int id, {
    required String matchText,
    int? categoryId,
    int? accountId,
    bool active = true,
  }) async {
    if (matchText.trim().isEmpty) {
      throw ArgumentError('Escribe el texto que debe contener el movimiento.');
    }
    if (categoryId == null && accountId == null) {
      throw ArgumentError('Elige una categoría o una cuenta para la regla.');
    }
    await _db.update(
      'rules',
      {
        'match_text': matchText.trim(),
        'category_id': categoryId,
        'account_id': accountId,
        'active': active ? 1 : 0,
      },
      where: 'id = ?',
      whereArgs: [id],
    );
  }

  Future<void> deleteRule(int id) async {
    await _db.delete('rules', where: 'id = ?', whereArgs: [id]);
  }

  Future<void> setRuleActive(int id, bool active) async {
    await _db.update(
      'rules',
      {'active': active ? 1 : 0},
      where: 'id = ?',
      whereArgs: [id],
    );
  }

  Future<RuleRecord?> matchRule(
      String description, String notes, String kind) async {
    final haystack = '$description $notes'.toLowerCase();
    if (haystack.trim().isEmpty) return null;
    for (final rule in await rules()) {
      if (!rule.active) continue;
      final needle = rule.matchText.toLowerCase();
      if (needle.isEmpty || !haystack.contains(needle)) continue;
      if (rule.categoryId != null && (kind == 'ingreso' || kind == 'egreso')) {
        final category = await getCategory(rule.categoryId!);
        if (category == null || category.kind != kind) continue;
      }
      if (rule.categoryId == null && rule.accountId == null) continue;
      return rule;
    }
    return null;
  }

  /// Aplica las reglas activas a los movimientos existentes.
  Future<int> applyRulesToExisting() async {
    final activeRules = (await rules()).where((rule) => rule.active).toList();
    if (activeRules.isEmpty) return 0;
    final rows = await _db.query(
      'transactions',
      where: "kind <> 'transferencia'",
    );
    var changed = 0;
    for (final row in rows) {
      final haystack =
          '${row['description'] ?? ''} ${row['notes'] ?? ''}'.toLowerCase();
      if (haystack.trim().isEmpty) continue;
      final kind = '${row['kind'] ?? ''}';
      for (final rule in activeRules) {
        final needle = rule.matchText.toLowerCase();
        if (needle.isEmpty || !haystack.contains(needle)) continue;
        if (rule.categoryId != null) {
          final category = await getCategory(rule.categoryId!);
          if (category == null || category.kind != kind) continue;
        }
        if (rule.categoryId == null && rule.accountId == null) continue;
        final categoryId = rule.categoryId ?? row['category_id'];
        final accountId = rule.accountId ?? row['account_id'];
        if (categoryId == row['category_id'] && accountId == row['account_id']) {
          break;
        }
        await _db.update(
          'transactions',
          {'category_id': categoryId, 'account_id': accountId},
          where: 'id = ?',
          whereArgs: [row['id']],
        );
        changed++;
        break;
      }
    }
    return changed;
  }

  // ---------------------------------------------------------------- respaldo
  Future<String> exportBackup() async {
    const tables = [
      'settings',
      'accounts',
      'categories',
      'recurring',
      'rules',
      'fx_rates',
      'transactions',
      'budgets',
    ];
    final data = <String, List<Map<String, dynamic>>>{};
    for (final table in tables) {
      data[table] = (await _db.query(table))
          .map((row) => Map<String, dynamic>.from(row))
          .toList();
    }
    return jsonEncode({
      'app': 'finanzas',
      'version': 2,
      'exported_at': DateTime.now().toIso8601String(),
      'data': data,
    });
  }

  Future<void> restoreBackup(String raw) async {
    final decoded = jsonDecode(raw);
    if (decoded is! Map<String, dynamic>) {
      throw const FormatException('El respaldo no tiene el formato esperado.');
    }
    // Acepta el formato del escritorio (`data`) y el de versiones móviles
    // anteriores (`tables`), para poder mover datos entre ambos.
    final tables = decoded['data'] ?? decoded['tables'];
    if (tables is! Map<String, dynamic>) {
      throw const FormatException('El respaldo no contiene datos.');
    }
    const order = [
      'settings',
      'accounts',
      'categories',
      'recurring',
      'rules',
      'fx_rates',
      'transactions',
      'budgets',
    ];
    await _db.transaction((txn) async {
      for (final table in order.reversed) {
        await txn.delete(table);
      }
      for (final table in order) {
        final rows = tables[table];
        if (rows is! List) continue;
        for (final row in rows) {
          if (row is Map) {
            await txn.insert(
              table,
              row.map((key, value) => MapEntry('$key', value)),
            );
          }
        }
      }
    });
    await loadCaches();
  }

  Future<void> wipeAll() async {
    await _db.transaction((txn) async {
      for (final table in const [
        'transactions',
        'budgets',
        'recurring',
        'rules',
        'fx_rates',
        'accounts',
        'categories',
        'settings',
      ]) {
        await txn.delete(table);
      }
    });
    await _seedDefaults(_db);
    await loadCaches();
  }

  Future<void> seedDemo() async {
    final accounts = await accountBalances();
    final cash = accounts.firstWhere(
      (account) => account.name == 'Efectivo',
      orElse: () => accounts.first,
    );
    final categories = await this.categories('egreso');
    final income = await this.categories('ingreso');
    if (cash.id == 0 || categories.isEmpty || income.isEmpty) return;
    final now = DateTime.now();
    final food = categories.firstWhere(
      (category) => category.name == 'Alimentación',
      orElse: () => categories.first,
    );
    final leisure = categories.firstWhere(
      (category) => category.name == 'Ocio',
      orElse: () => categories.first,
    );
    final salary = income.firstWhere(
      (category) => category.name == 'Salario',
      orElse: () => income.first,
    );
    for (var month = 5; month >= 0; month--) {
      final date = DateTime(now.year, now.month - month, 15);
      await addTransaction(
        date: isoDate(date),
        kind: 'ingreso',
        amount: 1500000,
        categoryId: salary.id,
        accountId: cash.id,
        description: 'Salario',
        applyRules: false,
      );
      await addTransaction(
        date: isoDate(date),
        kind: 'egreso',
        amount: 350000,
        categoryId: food.id,
        accountId: cash.id,
        description: 'Supermercado',
        applyRules: false,
      );
      await addTransaction(
        date: isoDate(date),
        kind: 'egreso',
        amount: 120000,
        categoryId: leisure.id,
        accountId: cash.id,
        description: 'Salida',
        applyRules: false,
      );
    }
  }
}
