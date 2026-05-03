"""Tests for reporter.py"""

import json
import unittest
from reporter import TestRecord, TestReport


class TestTestRecord(unittest.TestCase):
    def test_valid_success(self):
        r = TestRecord(endpoint="/api", status="success", response_time_ms=50.0)
        self.assertEqual(r.endpoint, "/api")
        self.assertIsNone(r.error_type)

    def test_valid_fail(self):
        r = TestRecord(endpoint="/api", status="fail", response_time_ms=100.0,
                        error_type="timeout")
        self.assertEqual(r.error_type, "timeout")

    def test_invalid_status(self):
        with self.assertRaises(ValueError):
            TestRecord(endpoint="/api", status="unknown", response_time_ms=50.0)

    def test_fail_without_error_type(self):
        with self.assertRaises(ValueError):
            TestRecord(endpoint="/api", status="fail", response_time_ms=50.0)


class TestTestReportSummary(unittest.TestCase):
    def setUp(self):
        self.report = TestReport()
        self.report.add_record(TestRecord("/users", "success", 30.0))
        self.report.add_record(TestRecord("/users", "success", 50.0))
        self.report.add_record(TestRecord("/users", "success", 70.0))
        self.report.add_record(TestRecord("/users", "fail", 200.0, error_type="timeout"))
        self.report.add_record(TestRecord("/orders", "success", 100.0))
        self.report.add_record(TestRecord("/orders", "fail", 300.0, error_type="500"))
        self.report.add_record(TestRecord("/orders", "fail", 400.0, error_type="timeout"))

    def test_summary_totals(self):
        s = self.report.get_summary()
        self.assertEqual(s["total"], 7)
        self.assertEqual(s["success"], 4)
        self.assertEqual(s["fail"], 3)
        self.assertAlmostEqual(s["success_rate"], 57.14, places=1)

    def test_summary_response_time(self):
        rt = self.report.get_summary()["response_time"]
        self.assertAlmostEqual(rt["avg"], 164.29, places=1)
        self.assertGreater(rt["p50"], 0)
        self.assertGreater(rt["p95"], 0)
        self.assertGreater(rt["p99"], 0)

    def test_error_breakdown(self):
        eb = self.report.get_summary()["error_breakdown"]
        self.assertEqual(eb["timeout"], 2)
        self.assertEqual(eb["500"], 1)

    def test_empty_report(self):
        r = TestReport()
        s = r.get_summary()
        self.assertEqual(s["total"], 0)
        self.assertEqual(s["success_rate"], 0.0)
        self.assertEqual(s["response_time"]["avg"], 0.0)


class TestPerEndpoint(unittest.TestCase):
    def setUp(self):
        self.report = TestReport()
        self.report.add_record(TestRecord("/a", "success", 10.0))
        self.report.add_record(TestRecord("/a", "fail", 100.0, error_type="timeout"))
        self.report.add_record(TestRecord("/b", "success", 50.0))

    def test_get_by_endpoint(self):
        stats = self.report.get_by_endpoint("/a")
        self.assertEqual(stats["total"], 2)
        self.assertEqual(stats["success"], 1)
        self.assertEqual(stats["fail"], 1)
        self.assertAlmostEqual(stats["success_rate"], 50.0)
        self.assertEqual(stats["endpoint"], "/a")

    def test_get_by_endpoint_empty(self):
        stats = self.report.get_by_endpoint("/nonexistent")
        self.assertEqual(stats["total"], 0)

    def test_get_all_endpoints(self):
        all_eps = self.report.get_all_endpoints()
        self.assertIn("/a", all_eps)
        self.assertIn("/b", all_eps)
        self.assertEqual(all_eps["/b"]["total"], 1)


class TestFormatters(unittest.TestCase):
    def setUp(self):
        self.report = TestReport()
        self.report.add_record(TestRecord("/ping", "success", 5.0))
        self.report.add_record(TestRecord("/ping", "fail", 500.0, error_type="timeout"))

    def test_format_text(self):
        text = self.report.format_text()
        self.assertIn("TEST REPORT", text)
        self.assertIn("/ping", text)
        self.assertIn("timeout", text)
        self.assertIn("50.0%", text)

    def test_format_json(self):
        raw = self.report.format_json()
        data = json.loads(raw)
        self.assertIn("summary", data)
        self.assertIn("by_endpoint", data)
        self.assertEqual(data["summary"]["total"], 2)
        self.assertIn("/ping", data["by_endpoint"])

    def test_json_roundtrip(self):
        raw = self.report.format_json()
        data = json.loads(raw)
        self.assertEqual(data["summary"]["success"], 1)
        self.assertEqual(data["by_endpoint"]["/ping"]["fail"], 1)


class TestTimingEdgeCases(unittest.TestCase):
    def test_single_record(self):
        report = TestReport()
        report.add_record(TestRecord("/x", "success", 42.0))
        rt = report.get_summary()["response_time"]
        self.assertEqual(rt["avg"], 42.0)
        self.assertEqual(rt["p50"], 42.0)
        self.assertEqual(rt["p95"], 42.0)
        self.assertEqual(rt["p99"], 42.0)

    def test_two_records(self):
        report = TestReport()
        report.add_record(TestRecord("/x", "success", 10.0))
        report.add_record(TestRecord("/x", "success", 20.0))
        rt = report.get_summary()["response_time"]
        self.assertEqual(rt["avg"], 15.0)
        self.assertEqual(rt["p50"], 15.0)


if __name__ == "__main__":
    unittest.main()
