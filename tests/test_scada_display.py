"""Screen-state tests: empty-value omission, numeric alignment, overflow width, wording."""
import ast
from pathlib import Path
import unittest
from edgeex_app.states import scada_display as D

ROOT = Path(__file__).resolve().parents[1]
SCREEN_FILES = ["edgeex_app/views/scada_view.py", "edgeex_app/components/scada.py",
                "edgeex_app/pages/scada.py", "edgeex_app/states/scada_display.py"]
# Every column whose cells are numbers, codes included (edge re-acceptance: priority '3' left-aligned).
NUMERIC_KEYS = {"count_d", "bad_d", "raw_d", "cond_d", "final_d", "level"}


class OverflowWidth(unittest.TestCase):
    def test_model_reproduces_edge_measurement(self):
        # Edge receipt 20261028T091746: 1366 aside clientWidth 427, table scrollWidth 500.
        self.assertEqual(D.track_width(1366, 4), 427)
        self.assertEqual(500 - D.track_width(1366, 4), 73)

    def test_no_table_scrolls_at_target_viewports(self):
        for viewport in (1366, 1920):
            for name in D.TABLES:
                with self.subTest(table=name, viewport=viewport):
                    self.assertEqual(D.overflow(name, viewport), 0)

    def test_every_table_has_a_placement(self):
        self.assertEqual(set(D.TABLES), set(D.PLACEMENT))


class NumericAlignment(unittest.TestCase):
    def test_numeric_columns_are_right_aligned(self):
        for name, spec in D.TABLES.items():
            for key, label, _, numeric in spec:
                with self.subTest(table=name, column=label):
                    self.assertEqual(numeric, key in NUMERIC_KEYS)

    def test_decimals_pad_and_never_round(self):
        self.assertEqual(D.align_decimals(["10.01", "8.633", "10.01"]), ["10.010", "8.633", "10.010"])
        self.assertEqual(D.align_decimals(["1", "2", "3"]), ["1", "2", "3"])
        self.assertEqual(D.align_decimals(["—", "1.5", "0"]), ["—", "1.5", "0.0"])

    def test_thousands_and_unparsed_text(self):
        self.assertEqual(D.group("12345.5"), "12,345.5")
        self.assertEqual(D.group("-1234"), "-1,234")
        self.assertEqual(D.group("1e-05"), "1e-05")
        self.assertEqual(D.align_decimals(["1e-05", "2.5"]), ["1e-05", "2.5"])


class EmptyOmission(unittest.TestCase):
    def test_unknown_values_are_omitted(self):
        row = {"a": "1.5", "b": "—", "c": "", "d": None, "e": "[]", "f": "0"}
        spec = [(k.upper(), k) for k in "abcdef"]
        self.assertEqual(D.facts(row, spec), [["A", "1.5"], ["F", "0"]])

    def test_reasons_and_times_are_readable(self):
        self.assertEqual(D.reasons_text('["EWMA_APPLIED"]'), "EWMA_APPLIED")
        self.assertEqual(D.reasons_text("[]"), "")
        self.assertEqual(D.kst_short("2026-10-28T09:27:02.000000+09:00"), "10-28 09:27:02")
        self.assertEqual(D.kst_short("—"), "—")

    def test_point_row_keeps_source_fields(self):
        src = dict(tag="T", channel="xgt_plc", unit=None, raw="10.01", cond="8.633", final="10.01",
                   quality="UNCERTAIN", observed_at="2026-10-28T09:27:02.000000+09:00",
                   ingested_at="—", reasons='["EWMA_APPLIED"]')
        row = D.point_row(src)
        self.assertEqual({k: row[k] for k in src}, src)
        self.assertEqual((row["final_d"], row["unit_d"], row["quality_d"], row["tone"]),
                         ("10.010", "—", "불확실", "uncertain"))

    def test_health_absence_states_cause_in_one_line(self):
        line = D.health_message("조회 실패 · SCHEMA_MISSING")
        self.assertIn("Health 표 없음", line)
        self.assertIn("DDL", line)
        self.assertLessEqual(len(line), 60)
        self.assertEqual(D.health_message("조회 성공 · 원천 시각 확인"), "")

    def test_alarm_text_uses_ds017_terms(self):
        row = D.alarm_row(dict(event="1", time="2026-10-28T09:27:02+09:00", message="품질 UNCERTAIN — 헌팅",
                               level="2", condition="발생", acknowledgement="미확인"))
        # Source level has no P1-P3 contract yet, so no alarm colour is asserted.
        self.assertEqual((row["message_d"], row["tone"]), ("품질 불확실 — 헌팅", "neutral"))

    def test_precise_time_keeps_every_digit(self):
        self.assertEqual(D.kst_precise("2026-10-28T09:27:02.038037+09:00"), "10-28 09:27:02.038037")
        self.assertEqual(D.kst_precise("2026-10-28T09:27:02+09:00"), "10-28 09:27:02")


class Wording(unittest.TestCase):
    BANNED = ("최첨단", "완벽", "무결성 보장", "전면", "무인 자동", "즉시", "쉽게", "간단히", "알람")

    def korean_literals(self):
        for path in SCREEN_FILES:
            tree = ast.parse((ROOT / path).read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                if isinstance(node, ast.Constant) and isinstance(node.value, str) \
                        and any("가" <= ch <= "힣" for ch in node.value) and not node.value.startswith('"""'):
                    yield path, node.value

    def test_screen_text_rules(self):
        for path, text in self.korean_literals():
            if "\n" in text:
                continue  # docstrings
            with self.subTest(path=path, text=text):
                self.assertLessEqual(len(text), 80)
                self.assertFalse(any(word in text for word in self.BANNED))


if __name__ == "__main__":
    unittest.main()
