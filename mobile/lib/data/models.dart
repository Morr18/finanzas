int _i(dynamic value) =>
    value is int ? value : int.tryParse('${value ?? 0}') ?? 0;
int? _ni(dynamic value) => value == null ? null : _i(value);
String _s(dynamic value) => value == null ? '' : '$value';

class AccountBalance {
  const AccountBalance({
    required this.id,
    required this.name,
    required this.kind,
    required this.color,
    required this.initialBalance,
    required this.currency,
    required this.balance,
    required this.baseBalance,
  });

  final int id;
  final String name;
  final String kind;
  final String color;
  final int initialBalance;
  final String currency;
  final int balance;
  final int baseBalance;

  factory AccountBalance.fromMap(Map<String, dynamic> map) => AccountBalance(
        id: _i(map['id']),
        name: _s(map['name']),
        kind: _s(map['kind']),
        color: _s(map['color']),
        initialBalance: _i(map['initial_balance']),
        currency: _s(map['currency']),
        balance: _i(map['balance']),
        baseBalance: _i(map['base_balance']),
      );
}

class Category {
  const Category({
    required this.id,
    required this.name,
    required this.kind,
    required this.color,
    required this.archived,
    this.usage = 0,
  });

  final int id;
  final String name;
  final String kind;
  final String color;
  final bool archived;
  final int usage;

  factory Category.fromMap(Map<String, dynamic> map) => Category(
        id: _i(map['id']),
        name: _s(map['name']),
        kind: _s(map['kind']),
        color: _s(map['color']),
        archived: _i(map['archived']) == 1,
        usage: _i(map['usage']),
      );
}

class Tx {
  const Tx({
    required this.id,
    required this.date,
    required this.kind,
    required this.amount,
    required this.transferAmount,
    required this.categoryId,
    required this.categoryName,
    required this.categoryColor,
    required this.accountId,
    required this.accountName,
    required this.accountCurrency,
    required this.transferAccountId,
    required this.transferAccountName,
    required this.transferCurrency,
    required this.description,
    required this.notes,
    required this.recurringId,
  });

  final int id;
  final String date;
  final String kind;
  final int amount;
  final int? transferAmount;
  final int? categoryId;
  final String categoryName;
  final String categoryColor;
  final int? accountId;
  final String accountName;
  final String accountCurrency;
  final int? transferAccountId;
  final String transferAccountName;
  final String transferCurrency;
  final String description;
  final String notes;
  final int? recurringId;

  String get title {
    if (description.trim().isNotEmpty) return description.trim();
    if (kind == 'transferencia') return 'Entre cuentas';
    return categoryName.isEmpty ? 'Sin categoría' : categoryName;
  }

  factory Tx.fromMap(Map<String, dynamic> map) => Tx(
        id: _i(map['id']),
        date: _s(map['date']),
        kind: _s(map['kind']),
        amount: _i(map['amount']),
        transferAmount: _ni(map['transfer_amount']),
        categoryId: _ni(map['category_id']),
        categoryName: _s(map['category_name']),
        categoryColor: _s(map['category_color']),
        accountId: _ni(map['account_id']),
        accountName: _s(map['account_name']),
        accountCurrency: _s(map['account_currency']),
        transferAccountId: _ni(map['transfer_account_id']),
        transferAccountName: _s(map['transfer_account_name']),
        transferCurrency: _s(map['transfer_currency']),
        description: _s(map['description']),
        notes: _s(map['notes']),
        recurringId: _ni(map['recurring_id']),
      );
}

class BudgetRow {
  const BudgetRow({
    required this.categoryId,
    required this.name,
    required this.color,
    required this.budget,
    required this.spent,
  });

  final int categoryId;
  final String name;
  final String color;
  final int budget;
  final int spent;

  double get ratio => budget <= 0 ? 0 : spent / budget;

  factory BudgetRow.fromMap(Map<String, dynamic> map) => BudgetRow(
        categoryId: _i(map['id']),
        name: _s(map['name']),
        color: _s(map['color']),
        budget: _i(map['budget']),
        spent: _i(map['spent']),
      );
}

class MonthlyPoint {
  const MonthlyPoint(
      {required this.key, required this.income, required this.expense});

  final String key;
  final int income;
  final int expense;

  int get net => income - expense;
}

class YearRow {
  const YearRow({
    required this.month,
    required this.key,
    required this.income,
    required this.expense,
  });

  final int month;
  final String key;
  final int income;
  final int expense;

  int get net => income - expense;
}

class CategoryTotal {
  const CategoryTotal({
    required this.id,
    required this.name,
    required this.color,
    required this.total,
    required this.count,
  });

  final int id;
  final String name;
  final String color;
  final int total;
  final int count;
}

class FxRate {
  const FxRate(
      {required this.currency, required this.date, required this.rateMicros});

  final String currency;
  final String date;
  final int rateMicros;

  double get rate => rateMicros / 1000000;

  factory FxRate.fromMap(Map<String, dynamic> map) => FxRate(
        currency: _s(map['currency']),
        date: _s(map['date']),
        rateMicros: _i(map['rate_micros']),
      );
}

class RecurringRule {
  const RecurringRule({
    required this.id,
    required this.description,
    required this.kind,
    required this.amount,
    required this.categoryId,
    required this.categoryName,
    required this.accountId,
    required this.accountName,
    required this.accountCurrency,
    required this.transferAccountId,
    required this.transferAccountName,
    required this.frequency,
    required this.day,
    required this.month,
    required this.startDate,
    required this.lastRun,
    required this.active,
  });

  final int id;
  final String description;
  final String kind;
  final int amount;
  final int? categoryId;
  final String categoryName;
  final int? accountId;
  final String accountName;
  final String accountCurrency;
  final int? transferAccountId;
  final String transferAccountName;
  final String frequency;
  final int day;
  final int month;
  final String startDate;
  final String? lastRun;
  final bool active;

  Map<String, dynamic> toRuleMap() => {
        'id': id,
        'description': description,
        'kind': kind,
        'amount': amount,
        'category_id': categoryId,
        'account_id': accountId,
        'transfer_account_id': transferAccountId,
        'frequency': frequency,
        'day': day,
        'month': month,
        'start_date': startDate,
        'last_run': lastRun,
        'active': active ? 1 : 0,
      };

  factory RecurringRule.fromMap(Map<String, dynamic> map) => RecurringRule(
        id: _i(map['id']),
        description: _s(map['description']),
        kind: _s(map['kind']),
        amount: _i(map['amount']),
        categoryId: _ni(map['category_id']),
        categoryName: _s(map['category_name']),
        accountId: _ni(map['account_id']),
        accountName: _s(map['account_name']),
        accountCurrency: _s(map['account_currency']),
        transferAccountId: _ni(map['transfer_account_id']),
        transferAccountName: _s(map['transfer_account_name']),
        frequency:
            _s(map['frequency']).isEmpty ? 'mensual' : _s(map['frequency']),
        day: _i(map['day']) == 0 ? 1 : _i(map['day']),
        month: _i(map['month']) == 0 ? 1 : _i(map['month']),
        startDate: _s(map['start_date']),
        lastRun: map['last_run'] == null ? null : _s(map['last_run']),
        active: _i(map['active']) == 1,
      );
}

class RuleRecord {
  const RuleRecord({
    required this.id,
    required this.matchText,
    required this.categoryId,
    required this.categoryName,
    required this.accountId,
    required this.accountName,
    required this.active,
  });

  final int id;
  final String matchText;
  final int? categoryId;
  final String categoryName;
  final int? accountId;
  final String accountName;
  final bool active;

  factory RuleRecord.fromMap(Map<String, dynamic> map) => RuleRecord(
        id: _i(map['id']),
        matchText: _s(map['match_text']),
        categoryId: _ni(map['category_id']),
        categoryName: _s(map['category_name']),
        accountId: _ni(map['account_id']),
        accountName: _s(map['account_name']),
        active: _i(map['active']) == 1,
      );
}

class CategorySummary {
  const CategorySummary({required this.income, required this.expense});

  final int income;
  final int expense;

  int get net => income - expense;
}
