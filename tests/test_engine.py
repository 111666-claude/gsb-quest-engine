import unittest

from quests.engine import Quest, detect_cycles, run


class RunTest(unittest.TestCase):
    def test_simple_completion(self):
        report = run({"a": Quest("a", [], 1, 5)}, [{"name": "a"}])
        self.assertEqual(report["completed"], ["a"])
        self.assertEqual(report["rewards"], 5)

    def test_not_enough_events(self):
        report = run({"a": Quest("a", [], 3, 5)}, [{"name": "a"}, {"name": "a"}])
        self.assertEqual(report["completed"], [])
        self.assertEqual(report["rewards"], 0)

    def test_progress_counted(self):
        report = run({"a": Quest("a", [], 5, 1)}, [{"name": "a", "count": 2}])
        self.assertEqual(report["progress"]["a"], 2)

    def test_report_has_cycles_field(self):
        self.assertIn("cycles", run({}, []))


class CycleTest(unittest.TestCase):
    def test_detect_cycles_returns_list(self):
        self.assertEqual(detect_cycles({}), [])
