"""Risk-based contract tests; never connect to an installed service."""
import copy
from datetime import datetime, timedelta, timezone
import os
import unittest
from unittest.mock import patch
from edgeex_app.services.scada_service import shape_snapshot, display, freshness
from edgeex_app.scada_config import scada_enabled, scada_server_settings
from edgeex_app.queries.scada import read_snapshot, ScadaQueryError, VQT_COLUMNS

AT = datetime(2026, 10, 27, 14, tzinfo=timezone.utc)


def fixture(value=0.0, quality=2):
    sample = dict(site_id="A", tag_id="same-tag", ts=AT-timedelta(seconds=2),
                  ingested_at=AT, channel="modbus", unit="bar", raw_val=value,
                  cond_val=value, final_val=value, final_quality=quality, reasons=[])
    return dict(site_id="A", as_of=AT, served_at=AT, latest=[sample], selected_tag="same-tag",
                series=[sample.copy()], series_truncated=False, minutes=15,
                counts=dict(received=1, good=int(quality == 2), uncertain=int(quality == 1), bad=int(quality == 0)),
                sections=dict(health=dict(state="error", code="SCHEMA_MISSING", rows=[]),
                              alarms=dict(state="ok", code="", rows=[])))


class ValueContract(unittest.TestCase):
    def test_real_zero_is_not_missing(self):
        s = shape_snapshot(fixture(), 10)
        self.assertEqual(s["rows"][0]["final"], "0")
        self.assertEqual(s["series"][0]["final"], 0)
        self.assertEqual(s["rows"][0]["validity"], "값 계약 일치")

    def test_null_and_bad_are_not_zero(self):
        s = shape_snapshot(fixture(None, 0), 10)
        self.assertEqual(s["rows"][0]["final"], "—")
        self.assertIsNone(s["series"][0]["final"])
        self.assertEqual(s["bad_tags"], 1)

    def test_malformed_bad_final_is_not_plotted(self):
        s = shape_snapshot(fixture(9, 0), 10)
        self.assertIsNone(s["series"][0]["final"])
        self.assertEqual(s["rows"][0]["validity"], "값 계약 오류")

    def test_nonfinite_is_not_valid_numeric_sample(self):
        for value in [float('nan'), float('inf'), -float('inf')]:
            s = shape_snapshot(fixture(value), 10)
            self.assertIsNone(s["series"][0]["final"])
            self.assertEqual(s["rows"][0]["validity"], "값 계약 오류")

    def test_cross_site_same_tag_is_rejected(self):
        data = fixture(); data["latest"][0]["site_id"] = "B"
        with self.assertRaisesRegex(ValueError, "Cross-site"):
            shape_snapshot(data, 10)

    def test_backfill_does_not_make_old_source_fresh(self):
        data = fixture(); data["latest"][0]["ts"] = AT-timedelta(hours=2)
        self.assertEqual(shape_snapshot(data, 10)["stale_tags"], 1)

    def test_timestamp_preserves_database_microseconds(self):
        data = fixture()
        data["latest"][0]["ingested_at"] = AT.replace(microsecond=38037)
        value = shape_snapshot(data, 10)["rows"][0]["ingested_at"]
        self.assertEqual(datetime.fromisoformat(value), data["latest"][0]["ingested_at"])

    def test_unknown_and_future_clocks_are_visible(self):
        self.assertEqual(freshness(AT, AT, None), "현재성 기준 미설정")
        self.assertEqual(freshness(AT+timedelta(milliseconds=1), AT, 10), "시각 불일치")
        self.assertEqual(freshness(AT.replace(tzinfo=None), AT, 10), "시각 확인 불가")

    def test_health_failure_does_not_erase_vqt(self):
        s = shape_snapshot(fixture(), 10)
        self.assertEqual(s["observed_tags"], 1)
        self.assertIn("조회 실패", s["health_state"])

    def test_health_status_field_and_missing_status(self):
        data = fixture(); data["sections"]["health"] = dict(state="ok", code="", rows=[
            dict(ts=AT, payload={"channels":{"bad":{"status":"error"}, "unknown":{}}})])
        s = shape_snapshot(data, 10)
        self.assertEqual([r["state"] for r in s["health_rows"]], ["error", "—"])

    def test_malformed_health_stays_partial(self):
        data = fixture(); data["sections"]["health"] = dict(state="ok", code="", rows=[dict(ts=AT, payload='invalid')])
        s = shape_snapshot(data, 10)
        self.assertIn("PAYLOAD_INVALID", s["health_state"])
        self.assertEqual(s["observed_tags"], 1)

    def test_profile_has_no_implicit_fallback(self):
        with patch.dict(os.environ, {"SCADA_DATA_SOURCE":"edge_vqt"}):
            self.assertTrue(scada_enabled())
            self.assertEqual(scada_server_settings(), {"default_transaction_read_only":"on"})
        with patch.dict(os.environ, {"SCADA_DATA_SOURCE":"unknown"}):
            with self.assertRaises(ValueError): scada_enabled()


class Tx:
    def __init__(self, conn, options): self.conn, self.options = conn, options
    async def __aenter__(self):
        self.conn.transactions.append(self.options); return self
    async def __aexit__(self, *args): return False


class Conn:
    def __init__(self, missing=False, fail_health=False):
        self.transactions, self.calls = [], []
        self.missing, self.fail_health = missing, fail_health
    def transaction(self, **kwargs): return Tx(self, kwargs)
    async def execute(self, sql): self.calls.append((sql, ()))
    async def fetchval(self, sql, *args):
        self.calls.append((sql, args))
        return AT if 'timestamp' in sql else 'exists'
    async def fetch(self, sql, *args):
        self.calls.append((sql, args))
        if 'information_schema' in sql:
            return [] if self.missing else [dict(column_name=c) for c in VQT_COLUMNS]
        if 'edgeex_health_latest' in sql:
            if self.fail_health: raise RuntimeError('health failure')
            return []
        if 'alarm_history' in sql: return []
        if 'DISTINCT ON' in sql: return fixture()['latest']
        return fixture()['series']
    async def fetchrow(self, sql, *args):
        self.calls.append((sql, args)); return fixture()['counts']


class Acquire:
    def __init__(self, conn): self.conn=conn
    async def __aenter__(self): return self.conn
    async def __aexit__(self,*args): return False


class QueryContract(unittest.IsolatedAsyncioTestCase):
    async def execute(self, conn, **kwargs):
        class Pool:
            def acquire(self, timeout): return Acquire(conn)
        async def pool(): return Pool()
        with patch('edgeex_app.queries.scada.get_pool', pool):
            return await read_snapshot('A', 'same-tag', **kwargs)

    async def test_site_binding_and_readonly_snapshot(self):
        c=Conn(); result=await self.execute(c)
        self.assertEqual(c.transactions[0], dict(isolation='repeatable_read', readonly=True))
        for sql,args in c.calls:
            if 'FROM public.' in sql:
                self.assertIn('site_id', sql)
                self.assertEqual(args[0], 'A')
        self.assertEqual(result['selected_tag'], 'same-tag')

    async def test_missing_core_schema_is_not_empty_success(self):
        with self.assertRaises(ScadaQueryError) as error:
            await self.execute(Conn(missing=True))
        self.assertEqual(error.exception.code, 'VQT_SCHEMA_INCOMPATIBLE')

    async def test_optional_failure_has_savepoint_and_preserves_core(self):
        c=Conn(fail_health=True); result=await self.execute(c)
        self.assertEqual(len(c.transactions), 3)
        self.assertEqual(result['sections']['health']['state'], 'error')
        self.assertEqual(result['sections']['alarms']['state'], 'ok')
        self.assertEqual(len(result['latest']), 1)

    async def test_unbounded_window_is_refused_before_connection(self):
        with self.assertRaises(ValueError): await self.execute(Conn(), minutes=1440)


if __name__ == '__main__':
    unittest.main(verbosity=2)
