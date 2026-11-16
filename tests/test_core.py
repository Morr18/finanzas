"""Pruebas básicas de la lógica de datos (sin interfaz gráfica).

Ejecutar con:  python3 -m unittest discover -s tests -v
"""
from __future__ import annotations

import os
import sqlite3
import tempfile
import unittest
from pathlib import Path

from finanzas import theme
from finanzas.db import Database
from finanzas.views.budgets import _budget_cents
from finanzas.utils import (
    iter_recurring_dates, money, month_bounds, month_key, parse_amount,
    parse_date, parse_search_query, shift_month,
)


class UtilsTest(unittest.TestCase):
    def test_parse_amount_formats(self):
        cases = {
            "1,234.56": 123456,
            "1.234,56": 123456,
            "1500": 150000,
            "1.500": 150000,
            "$ 1 200,50": 120050,
            "0,99": 99,
            "12.5": 1250,
        }
        for text, expected in cases.items():
            self.assertEqual(parse_amount(text), expected, text)

    def test_parse_amount_rejects_invalid(self):
        for text in ("", "abc", "0", "-5"):
            with self.assertRaises(ValueError, msg=text):
                parse_amount(text)

    def test_parse_date(self):
        self.assertEqual(parse_date("14/11/2026").isoformat(), "2026-11-14")
        self.assertEqual(parse_date("2026-11-14").isoformat(), "2026-11-14")
        self.assertEqual(parse_date("14-11-26").isoformat(), "2026-11-14")
        with self.assertRaises(ValueError):
            parse_date("31/02/2026")

    def test_month_helpers(self):
        self.assertEqual(month_bounds("2026-02"), ("2026-02-01", "2026-02-28"))
        self.assertEqual(shift_month("2026-01", -1), "2025-12")
        self.assertEqual(shift_month("2026-12", 1), "2027-01")
        self.assertEqual(month_key("2026-11-14"), "2026-11")

    def test_money(self):
        self.assertEqual(money(123456), "$1,234.56")
        self.assertEqual(money(-500), "-$5.00")
        self.assertEqual(money(0), "$0.00")

    def test_budget_zero_means_remove(self):
        self.assertEqual(_budget_cents(""), 0)
        self.assertEqual(_budget_cents("   "), 0)
        self.assertEqual(_budget_cents("0"), 0)
        self.assertEqual(_budget_cents("0.00"), 0)
        self.assertEqual(_budget_cents("0,00"), 0)
        self.assertEqual(_budget_cents("300,00"), 30000)
        self.assertEqual(_budget_cents("1.500,50"), 150050)
        with self.assertRaises(ValueError):
            _budget_cents("abc")

    def test_money_local_style(self):
        self.assertEqual(money(123456, style="es"), "$1.234,56")
        self.assertEqual(money(123456789, "€", style="es"), "€1.234.567,89")
        self.assertEqual(money(-500, "S/", style="es"), "-S/5,00")


class DatabaseTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.path = Path(self.tmp.name) / "test.db"
        self.db = Database(self.path)
        self.bank = self.db.accounts()[0]["id"]
        self.bank2 = self.db.accounts()[1]["id"]
        self.cat_expense = next(c for c in self.db.categories("egreso"))
        self.cat_income = next(c for c in self.db.categories("ingreso"))

    def tearDown(self):
        self.db.close()
        self.tmp.cleanup()

    def test_defaults(self):
        self.assertGreaterEqual(len(self.db.categories()), 5)
        self.assertGreaterEqual(len(self.db.accounts()), 1)
        self.assertFalse(self.db.has_transactions())

    def test_balance_and_summary(self):
        self.db.add_transaction("2026-11-01", "ingreso", 100000, self.cat_income["id"],
                                self.bank, description="Sueldo")
        self.db.add_transaction("2026-11-02", "egreso", 25000, self.cat_expense["id"],
                                self.bank, description="Súper")
        start, end = month_bounds("2026-11")
        summary = self.db.summary(start, end)
        self.assertEqual(summary["income"], 100000)
        self.assertEqual(summary["expense"], 25000)
        self.assertEqual(summary["net"], 75000)

        balances = {a["id"]: a["balance"] for a in self.db.account_balances()}
        self.assertEqual(balances[self.bank], 75000)
        self.assertEqual(self.db.total_balance(), 75000)

    def test_transfer_moves_money_between_accounts(self):
        self.db.add_transaction("2026-11-03", "transferencia", 30000, None,
                                self.bank, self.bank2, "Ahorro")
        balances = {a["id"]: a["balance"] for a in self.db.account_balances()}
        self.assertEqual(balances[self.bank], -30000)
        self.assertEqual(balances[self.bank2], 30000)
        self.assertEqual(self.db.total_balance(), 0)
        self.assertEqual(self.db.summary("2026-11-01", "2026-11-30")["expense"], 0)

    def test_filters_and_totals(self):
        self.db.add_transaction("2026-11-01", "ingreso", 100000, self.cat_income["id"],
                                self.bank, description="Sueldo")
        self.db.add_transaction("2026-11-02", "egreso", 25000, self.cat_expense["id"],
                                self.bank, description="Súper")
        self.db.add_transaction("2026-11-03", "egreso", 5000, None, self.bank, description="Sin categoría")
        self.assertEqual(self.db.transaction_count({"kind": "egreso"}), 2)
        self.assertEqual(self.db.transaction_count({"text": "Súper"}), 1)
        self.assertEqual(self.db.transaction_count({"category_id": 0}), 1)
        totals = self.db.transaction_totals({"kind": "egreso"})
        self.assertEqual(totals["expense"], 30000)
        self.assertEqual(totals["income"], 0)

    def test_budgets(self):
        self.db.add_transaction("2026-11-04", "egreso", 12000,
                                self.cat_expense["id"], self.bank, description="Compra")
        self.db.set_budget(self.cat_expense["id"], 20000)
        row = next(b for b in self.db.budgets_for_month("2026-11")
                   if b["id"] == self.cat_expense["id"])
        self.assertEqual(row["budget"], 20000)
        self.assertEqual(row["spent"], 12000)
        self.db.set_budget(self.cat_expense["id"], 0)
        row = next(b for b in self.db.budgets_for_month("2026-11")
                   if b["id"] == self.cat_expense["id"])
        self.assertEqual(row["budget"], 0)

    def test_backup_restore_roundtrip(self):
        self.db.add_transaction("2026-11-05", "ingreso", 50000, self.cat_income["id"],
                                self.bank, description="Extra")
        backup = Path(self.tmp.name) / "backup.json"
        self.db.backup_json(backup)
        self.db.wipe_data()
        self.assertFalse(self.db.has_transactions())
        self.db.restore_json(backup)
        self.assertEqual(self.db.transaction_count(), 1)
        self.assertEqual(self.db.transactions()[0]["description"], "Extra")

    def test_csv_export(self):
        self.db.add_transaction("2026-11-06", "egreso", 12345,
                                self.cat_expense["id"], self.bank, description="Café")
        out = Path(self.tmp.name) / "movimientos.csv"
        self.assertEqual(self.db.export_csv(out), 1)
        text = out.read_text(encoding="utf-8-sig")
        self.assertIn("Café", text)
        self.assertIn("123.45", text)

    def test_sort_and_pagination(self):
        self.db.add_transaction("2026-11-01", "ingreso", 300000,
                                self.cat_income["id"], self.bank, description="C")
        self.db.add_transaction("2026-11-02", "egreso", 10000,
                                self.cat_expense["id"], self.bank, description="A")
        self.db.add_transaction("2026-11-03", "egreso", 20000,
                                self.cat_expense["id"], self.bank, description="B")

        by_amount = self.db.transactions({"sort": "monto", "desc": False})
        self.assertEqual([t["amount"] for t in by_amount], [10000, 20000, 300000])
        by_text = self.db.transactions({"sort": "descripcion", "desc": False})
        self.assertEqual([t["description"] for t in by_text], ["A", "B", "C"])
        by_date = self.db.transactions({})
        self.assertEqual([t["description"] for t in by_date], ["B", "A", "C"])

        page = self.db.transactions({"sort": "monto", "desc": False,
                                     "limit": 2, "offset": 1})
        self.assertEqual([t["amount"] for t in page], [20000, 300000])

    def test_restore_transaction(self):
        tx_id = self.db.add_transaction(
            "2026-11-07", "egreso", 4500, self.cat_expense["id"],
            self.bank, description="Restaurable",
        )
        row = self.db.get_transaction(tx_id)
        self.db.delete_transaction(tx_id)
        self.assertIsNone(self.db.get_transaction(tx_id))
        self.db.restore_transaction(row)
        restored = self.db.get_transaction(tx_id)
        self.assertEqual(restored["description"], "Restaurable")
        self.assertEqual(restored["amount"], 4500)

    def test_restore_transaction_with_deleted_account(self):
        tx_id = self.db.add_transaction(
            "2026-11-07", "egreso", 4500, self.cat_expense["id"],
            self.bank, description="Sin cuenta",
        )
        row = self.db.get_transaction(tx_id)
        self.db.delete_transaction(tx_id)
        self.db.delete_account(self.bank)
        self.db.restore_transaction(row)
        restored = self.db.get_transaction(tx_id)
        self.assertEqual(restored["description"], "Sin cuenta")
        self.assertIsNone(restored["account_id"])

    def test_restore_category_and_budget(self):
        self.db.set_budget(self.cat_expense["id"], 30000)
        self.assertEqual(self.db.get_budget(self.cat_expense["id"]), 30000)
        self.db.delete_category(self.cat_expense["id"])
        self.assertEqual(self.db.get_budget(self.cat_expense["id"]), 0)
        self.db.restore_category(self.cat_expense, 30000)
        self.assertEqual(self.db.get_budget(self.cat_expense["id"]), 30000)

    def test_restore_account(self):
        account = self.db.accounts()[0]
        self.db.delete_account(account["id"])
        self.assertNotIn(account["id"], [a["id"] for a in self.db.accounts()])
        self.db.restore_account(account)
        self.assertIn(account["id"], [a["id"] for a in self.db.accounts()])

    def test_csv_localized_numbers(self):
        self.db.set_setting("number_format", "es")
        self.db.add_transaction("2026-11-08", "egreso", 12345,
                                self.cat_expense["id"], self.bank, description="Café")
        out = Path(self.tmp.name) / "movimientos_es.csv"
        self.db.export_csv(out)
        text = out.read_text(encoding="utf-8-sig")
        self.assertIn("123,45", text)
        self.db.set_setting("number_format", "en")

    def test_demo_data(self):
        self.db.seed_demo(2)
        self.assertTrue(self.db.has_transactions())
        self.assertGreater(self.db.total_balance(), 0)
        # hay presupuestos de ejemplo
        self.assertTrue(any(b["budget"] > 0 for b in self.db.budgets_for_month(month_key())))


class SearchQueryTest(unittest.TestCase):
    def test_parse_operators(self):
        query = parse_search_query('categoria:"Ahorro e inversión" cuenta:Efectivo '
                                   "monto>100 tipo:ingreso")
        self.assertEqual(query["category"], "Ahorro e inversión")
        self.assertEqual(query["account"], "Efectivo")
        self.assertEqual(query["kind"], "ingreso")
        self.assertEqual(query["amount_ops"], [(">", 10000)])
        self.assertEqual(query["text"], "")

    def test_parse_free_text_and_dates(self):
        query = parse_search_query("fecha:2026-05 Mercado")
        self.assertEqual(query["text"], "Mercado")
        self.assertEqual(query["date_ops"], [(">=", "2026-05-01"), ("<=", "2026-05-31")])

    def test_invalid_operator_becomes_text(self):
        query = parse_search_query("tipo:desconocido")
        self.assertIsNone(query["kind"])
        self.assertIn("tipo:desconocido", query["text"])

    def test_database_filters_with_query(self):
        with tempfile.TemporaryDirectory() as tmp:
            db = Database(Path(tmp) / "q.db")
            try:
                bank = next(a for a in db.accounts() if a["name"] == "Cuenta bancaria")
                cash = next(a for a in db.accounts() if a["name"] == "Efectivo")
                ocio = next(c for c in db.categories("egreso") if c["name"] == "Ocio")
                comida = next(c for c in db.categories("egreso")
                              if c["name"] == "Alimentación")
                db.add_transaction("2026-05-02", "egreso", 15000, ocio["id"], bank["id"],
                                   description="Concierto")
                db.add_transaction("2026-05-03", "egreso", 5000, comida["id"], cash["id"],
                                   description="Mercado")
                db.add_transaction("2026-05-04", "ingreso", 90000, None, bank["id"],
                                   description="Salario")

                self.assertEqual(len(db.transactions({"text": "categoria:Ocio"})), 1)
                rows = db.transactions({"text": "cuenta:Efectivo"})
                self.assertEqual([r["description"] for r in rows], ["Mercado"])
                rows = db.transactions({"text": "monto>500"})
                self.assertEqual([r["description"] for r in rows], ["Salario"])
                self.assertEqual(db.transaction_totals(
                    {"text": "categoria:Ocio"})["expense"], 15000)
            finally:
                db.close()


class MultiCurrencyTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = Database(Path(self.tmp.name) / "fx.db")
        self.eur = self.db.add_account("Cuenta EUR", "banco", 10000, "#6366f1",
                                       currency="EUR")
        self.bank = next(a for a in self.db.accounts() if a["name"] == "Cuenta bancaria")
        self.ocio = next(c for c in self.db.categories("egreso") if c["name"] == "Ocio")

    def tearDown(self):
        self.db.close()
        self.tmp.cleanup()

    def test_default_base_currency(self):
        self.assertEqual(self.db.base_currency(), "USD")

    def test_currency_is_saved(self):
        self.assertEqual(self.db.get_account(self.eur)["currency"], "EUR")

    def test_rate_by_date_and_conversion(self):
        self.db.set_fx_rate("EUR", "2026-01-01", "1.10")
        self.db.set_fx_rate("EUR", "2026-06-01", "1.20")
        self.assertEqual(self.db.fx_rate_micros("EUR", "2026-07-01"), 1_200_000)
        self.assertEqual(self.db.fx_rate_micros("EUR", "2026-03-01"), 1_100_000)
        self.assertEqual(self.db.to_base(10000, "EUR", "2026-07-01"), 12000)
        self.assertEqual(
            self.db.convert_between(11000, "EUR", "USD", "2026-07-01"), 13200)

    def test_base_currency_has_no_rate(self):
        with self.assertRaises(ValueError):
            self.db.set_fx_rate("USD", "2026-07-01", "1")
        with self.assertRaises(ValueError):
            self.db.set_fx_rate("EUR", "2026-07-01", "0")

    def test_base_balances_and_summary(self):
        self.db.set_fx_rate("EUR", "2026-01-01", "1.20")
        balances = {a["id"]: a for a in self.db.account_balances()}
        self.assertEqual(balances[self.eur]["base_balance"], 12000)
        self.assertEqual(self.db.total_balance(), 12000)

        self.db.add_transaction("2026-07-10", "egreso", 5000, self.ocio["id"],
                                self.eur, description="Cena")
        self.assertEqual(self.db.summary("2026-07-01", "2026-07-31")["expense"], 6000)

    def test_transfer_calculates_destination_amount(self):
        self.db.set_fx_rate("EUR", "2026-01-01", "1.20")
        tx = self.db.add_transaction(
            "2026-07-11", "transferencia", 12000, account_id=self.bank["id"],
            transfer_account_id=self.eur, description="Cambio",
        )
        self.assertEqual(self.db.get_transaction(tx)["transfer_amount"], 10000)

    def test_change_base_currency(self):
        self.db.set_fx_rate("EUR", "2026-01-01", "1.10")
        self.db.set_base_currency("eur")
        self.assertEqual(self.db.base_currency(), "EUR")
        self.assertEqual(self.db.fx_rates(), [])
        with self.assertRaises(ValueError):
            self.db.set_base_currency("   ")

    def test_missing_rates(self):
        self.assertEqual(self.db.missing_rates(), ["EUR"])
        self.db.set_fx_rate("EUR", "2026-01-01", "1.10")
        self.assertEqual(self.db.missing_rates(), [])


class RulesTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = Database(Path(self.tmp.name) / "rules.db")
        self.ocio = next(c for c in self.db.categories("egreso") if c["name"] == "Ocio")
        self.bank = next(a for a in self.db.accounts() if a["name"] == "Cuenta bancaria")
        self.card = self.db.add_account("Tarjeta", "tarjeta", 0, "#6366f1")
        self.rule = self.db.add_rule("netflix", self.ocio["id"], self.card)

    def tearDown(self):
        self.db.close()
        self.tmp.cleanup()

    def test_match_ignores_case(self):
        match = self.db.match_rule("Pago NETFLIX Premium", "", "egreso")
        self.assertIsNotNone(match)
        self.assertEqual(match["id"], self.rule)

    def test_rule_not_applied_to_wrong_kind(self):
        self.assertIsNone(self.db.match_rule("NETFLIX", "", "ingreso"))

    def test_applied_on_create(self):
        tx = self.db.add_transaction("2026-07-12", "egreso", 1500, self.ocio["id"],
                                     self.bank["id"], description="NETFLIX mensual")
        self.assertEqual(self.db.get_transaction(tx)["account_id"], self.card)

    def test_can_skip_on_create(self):
        tx = self.db.add_transaction("2026-07-12", "egreso", 1500, self.ocio["id"],
                                     self.bank["id"], description="NETFLIX mensual",
                                     apply_rules=False)
        self.assertEqual(self.db.get_transaction(tx)["account_id"], self.bank["id"])

    def test_apply_to_existing(self):
        tx = self.db.add_transaction("2026-07-13", "egreso", 2000, self.ocio["id"],
                                     self.bank["id"], description="netflix otro",
                                     apply_rules=False)
        self.assertGreaterEqual(self.db.apply_rules_to_existing(), 1)
        self.assertEqual(self.db.get_transaction(tx)["account_id"], self.card)

    def test_rules_listed(self):
        self.assertTrue(any(r["id"] == self.rule for r in self.db.rules()))


class RecurringTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.db = Database(Path(self.tmp.name) / "rec.db")
        self.cat = next(c for c in self.db.categories("egreso") if c["name"] == "Vivienda")
        self.bank = next(a for a in self.db.accounts() if a["name"] == "Cuenta bancaria")

    def tearDown(self):
        self.db.close()
        self.tmp.cleanup()

    def test_monthly_generates_once(self):
        rule = self.db.add_recurring("Renta", "egreso", 50000, self.cat["id"],
                                     self.bank["id"], None, "mensual", 15, "2026-01-15")
        self.assertEqual(self.db.process_recurring("2026-01-20"), 1)
        self.assertEqual(self.db.process_recurring("2026-01-20"), 0)
        self.assertEqual(self.db.get_recurring(rule)["last_run"], "2026-01-15")
        rows = self.db.transactions({"text": "Renta"})
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["recurring_id"], rule)

    def test_catches_up_missed_periods(self):
        self.db.add_recurring("Renta", "egreso", 50000, self.cat["id"],
                              self.bank["id"], None, "mensual", 15, "2026-01-15")
        self.assertEqual(self.db.process_recurring("2026-03-20"), 3)
        self.assertEqual(len(self.db.transactions({"text": "Renta"})), 3)

    def test_next_occurrence(self):
        rule = self.db.add_recurring("Renta", "egreso", 50000, self.cat["id"],
                                     self.bank["id"], None, "mensual", 15, "2026-01-15")
        row = self.db.get_recurring(rule)
        self.assertEqual(self.db.next_occurrence(row, "2026-01-16"), "2026-02-15")

    def test_inactive_rule_does_not_generate(self):
        rule = self.db.add_recurring("Renta", "egreso", 50000, self.cat["id"],
                                     self.bank["id"], None, "mensual", 15,
                                     "2026-01-15", active=False)
        self.assertEqual(self.db.process_recurring("2026-03-20"), 0)
        self.assertFalse(self.db.get_recurring(rule)["active"])

    def test_weekly_and_yearly_dates(self):
        rule = {
            "start_date": "2026-01-01", "frequency": "semanal", "day": 0,
        }
        dates = list(iter_recurring_dates(
            rule, parse_date("2026-01-01"), parse_date("2026-01-31")))
        self.assertEqual(len(dates), 4)
        annual = {
            "start_date": "2024-03-10", "frequency": "anual", "day": 10, "month": 3,
        }
        dates = list(iter_recurring_dates(
            annual, parse_date("2025-01-01"), parse_date("2026-12-31")))
        self.assertEqual([d.isoformat() for d in dates], ["2025-03-10", "2026-03-10"])


class ThemeTest(unittest.TestCase):
    def tearDown(self):
        theme.set_mode("light")

    def test_switch_modes(self):
        theme.set_mode("dark")
        self.assertEqual(theme.MODE, "dark")
        self.assertEqual(theme.BG, "#0b1220")
        theme.set_mode("light")
        self.assertEqual(theme.MODE, "light")
        self.assertEqual(theme.BG, "#f3f4f6")


class ThemeWidgetsTest(unittest.TestCase):
    """Regresión: los widgets no deben capturar los colores del tema al importarse."""

    @classmethod
    def setUpClass(cls):
        try:
            import tkinter as tk
            cls.tk = tk
            cls.root = tk.Tk()
            cls.root.withdraw()
        except Exception:
            raise unittest.SkipTest("Tk no disponible en este entorno")

    @classmethod
    def tearDownClass(cls):
        if getattr(cls, "root", None) is not None:
            cls.root.destroy()
        theme.set_mode("light")

    def setUp(self):
        theme.set_mode("light")
        theme.apply_theme(self.root)

    def tearDown(self):
        theme.set_mode("light")

    def test_widgets_follow_dark_theme(self):
        from finanzas import widgets

        theme.set_mode("dark")
        card = widgets.Card(self.root)
        try:
            self.assertEqual(card.cget("bg"), theme.CARD)
            self.assertEqual(card.inner.cget("bg"), theme.CARD)
            title = widgets.card_title(card.inner, "Título")
            label = next(w for w in title.winfo_children()
                         if isinstance(w, self.tk.Label))
            self.assertEqual(label.cget("fg"), theme.TEXT)
            self.assertEqual(label.cget("bg"), theme.CARD)
        finally:
            card.destroy()


class DisplayCurrencyTest(unittest.TestCase):
    """La moneda de visualización convierte sin tocar los datos guardados."""

    @classmethod
    def setUpClass(cls):
        try:
            import tkinter as tk
            root = tk.Tk()
            root.withdraw()
            root.destroy()
        except Exception:
            raise unittest.SkipTest("Tk no disponible en este entorno")

    def _app(self):
        from finanzas.app import App

        path = tempfile.mktemp(suffix=".db")
        db = Database(path)
        db.set_base_currency("MXN")
        db.set_setting("currency", "$")
        db.set_fx_rate("USD", "2026-01-01", "18")
        bank = next(a for a in db.accounts() if a["name"] == "Cuenta bancaria")
        ocio = next(c for c in db.categories("egreso") if c["name"] == "Ocio")
        db.add_transaction("2026-11-10", "egreso", 180000, ocio["id"], bank["id"])
        db.close()

        app = App(path)
        app.withdraw()
        self.addCleanup(app.db.close)
        self.addCleanup(app.destroy)
        return app

    def test_conversion_between_base_and_display(self):
        app = self._app()
        self.assertEqual(app.display_currency, "")
        self.assertEqual(app.money(180000), "$1,800.00")

        app.set_display_currency("USD", notify=False)
        self.assertEqual(app.display_currency, "USD")
        self.assertEqual(app.display_currency_code(), "USD")
        self.assertEqual(app.money(180000), "US$100.00")
        self.assertEqual(app.money_native(180000, ""), "US$100.00")
        self.assertEqual(app.money_native(10000, "USD"), "US$100.00")
        self.assertEqual(app.money_original(180000, ""), "$1,800.00")
        self.assertEqual(app.convert_display(180000), 10000)
        self.assertEqual(app.to_base_display(10000), 180000)
        self.assertEqual(app.db.get_setting("display_currency"), "USD")
        self.assertIn("USD", app.available_display_currencies())

        app.set_display_currency("MXN", notify=False)
        self.assertEqual(app.display_currency, "")
        self.assertEqual(app.money(180000), "$1,800.00")

    def test_invalid_display_falls_back_to_base(self):
        app = self._app()
        app.set_display_currency("USD", notify=False)
        app.db.delete_fx_rate("USD", "2026-01-01")
        app.ensure_display_currency()
        self.assertEqual(app.display_currency, "")
        self.assertEqual(app.money(180000), "$1,800.00")

        # Aunque la preferencia siga guardada, sin tasa se usa la moneda base.
        app.db.set_setting("display_currency", "USD")
        app.reload_all()
        self.assertEqual(app.display_currency, "")
        self.assertEqual(app.display_currency_code(), "MXN")

    def test_unknown_currency_is_rejected(self):
        app = self._app()
        app.set_display_currency("EUR", notify=False)
        self.assertEqual(app.display_currency, "")
        self.assertEqual(app.money(180000), "$1,800.00")


class MigrationTest(unittest.TestCase):
    def test_old_database_is_migrated(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "old.db"
            conn = sqlite3.connect(path)
            conn.executescript("""
            CREATE TABLE accounts (
             id INTEGER PRIMARY KEY, name TEXT NOT NULL COLLATE NOCASE UNIQUE,
             kind TEXT NOT NULL DEFAULT 'efectivo', initial_balance INTEGER NOT NULL DEFAULT 0,
             color TEXT NOT NULL DEFAULT '#6366f1', archived INTEGER NOT NULL DEFAULT 0,
             created_at TEXT NOT NULL);
            CREATE TABLE categories (
             id INTEGER PRIMARY KEY, name TEXT NOT NULL COLLATE NOCASE,
             kind TEXT NOT NULL, color TEXT NOT NULL DEFAULT '#6366f1',
             archived INTEGER NOT NULL DEFAULT 0, UNIQUE(name, kind));
            CREATE TABLE transactions (
             id INTEGER PRIMARY KEY, date TEXT NOT NULL, kind TEXT NOT NULL,
             amount INTEGER NOT NULL, category_id INTEGER, account_id INTEGER,
             transfer_account_id INTEGER, description TEXT NOT NULL DEFAULT '',
             notes TEXT NOT NULL DEFAULT '', created_at TEXT NOT NULL);
            CREATE TABLE budgets (
             category_id INTEGER PRIMARY KEY, amount INTEGER NOT NULL DEFAULT 0);
            CREATE TABLE settings (key TEXT PRIMARY KEY, value TEXT NOT NULL);
            """)
            conn.execute(
                "INSERT INTO accounts (name, kind, initial_balance, color, archived,"
                " created_at) VALUES ('Vieja','banco',0,'#6366f1',0,'2026-01-01T00:00:00')"
            )
            conn.commit()
            conn.close()

            db = Database(path)
            try:
                account_cols = {r["name"] for r in
                                db.conn.execute("PRAGMA table_info(accounts)")}
                tx_cols = {r["name"] for r in
                           db.conn.execute("PRAGMA table_info(transactions)")}
                tables = {r["name"] for r in db.conn.execute(
                    "SELECT name FROM sqlite_master WHERE type = 'table'")}
                self.assertIn("currency", account_cols)
                self.assertIn("transfer_amount", tx_cols)
                self.assertIn("recurring_id", tx_cols)
                self.assertIn("fx_rates", tables)
                self.assertIn("rules", tables)
                self.assertIn("recurring", tables)
                self.assertEqual(db.total_balance(), 0)
            finally:
                db.close()


if __name__ == "__main__":
    unittest.main()
