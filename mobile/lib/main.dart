import 'package:flutter/material.dart';

import 'app.dart';
import 'data/database.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  final db = await AppDatabase.open();
  var created = 0;
  try {
    created = await db.processRecurring();
  } catch (_) {
    created = 0;
  }
  runApp(FinanzasApp(db: db, recurringCreated: created));
}
