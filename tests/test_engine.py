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


class PrerequisiteTest(unittest.TestCase):
    def test_unmet_prerequisite_blocks_completion(self):
        quests = {
            "a": Quest("a", [], 1, 5),
            "b": Quest("b", ["a"], 1, 7),
        }
        report = run(quests, [{"name": "b"}])
        self.assertEqual(report["completed"], [])
        self.assertEqual(report["rewards"], 0)
        self.assertEqual(report["progress"]["b"], 1)

    def test_completion_after_prerequisite_met(self):
        quests = {
            "a": Quest("a", [], 1, 5),
            "b": Quest("b", ["a"], 1, 7),
        }
        report = run(quests, [{"name": "b"}, {"name": "a"}, {"name": "b"}])
        self.assertEqual(report["completed"], ["a", "b"])
        self.assertEqual(report["rewards"], 12)

    def test_completion_order_respects_dependencies(self):
        quests = {
            "a": Quest("a", [], 1, 1),
            "b": Quest("b", ["a"], 1, 1),
            "c": Quest("c", ["b"], 1, 1),
        }
        events = [{"name": "c"}, {"name": "b"}, {"name": "a"},
                  {"name": "b"}, {"name": "c"}]
        report = run(quests, events)
        self.assertEqual(report["completed"], ["a", "b", "c"])

    def test_cyclic_prerequisites_never_complete(self):
        quests = {
            "a": Quest("a", ["b"], 1, 10),
            "b": Quest("b", ["a"], 1, 5),
        }
        report = run(quests, [{"name": "a"}, {"name": "b"}, {"name": "a"}])
        self.assertEqual(report["completed"], [])
        self.assertEqual(report["rewards"], 0)


class CappingTest(unittest.TestCase):
    def test_progress_capped_at_need(self):
        report = run({"a": Quest("a", [], 3, 7)}, [{"name": "a"} for _ in range(4)])
        self.assertEqual(report["progress"]["a"], 3)
        self.assertEqual(report["completed"], ["a"])
        self.assertEqual(report["rewards"], 7)

    def test_extra_events_do_not_reward_again(self):
        report = run({"a": Quest("a", [], 1, 5)}, [{"name": "a"} for _ in range(10)])
        self.assertEqual(report["completed"], ["a"])
        self.assertEqual(report["rewards"], 5)

    def test_count_event_capped(self):
        report = run({"a": Quest("a", [], 2, 5)}, [{"name": "a", "count": 9}])
        self.assertEqual(report["progress"]["a"], 2)
        self.assertEqual(report["rewards"], 5)

    def test_sample_matches_readme(self):
        from quests.engine import sample
        quests, events = sample()
        report = run(quests, events)
        self.assertEqual(report["completed"], ["c"])
        self.assertEqual(report["rewards"], 7)
        self.assertEqual(len(report["cycles"]), 1)


class CycleDetectionTest(unittest.TestCase):
    def test_mutual_dependency_reported(self):
        quests = {"a": Quest("a", ["b"], 1, 1), "b": Quest("b", ["a"], 1, 1)}
        self.assertEqual(detect_cycles(quests), [["a", "b"]])

    def test_self_loop_reported(self):
        self.assertEqual(detect_cycles({"a": Quest("a", ["a"], 1, 1)}), [["a"]])

    def test_dag_has_no_cycles(self):
        quests = {
            "a": Quest("a", [], 1, 1),
            "b": Quest("b", ["a"], 1, 1),
            "c": Quest("c", ["a", "b"], 1, 1),
        }
        self.assertEqual(detect_cycles(quests), [])

    def test_multiple_cycles_sorted(self):
        quests = {
            "x": Quest("x", ["y"], 1, 1),
            "y": Quest("y", ["x"], 1, 1),
            "p": Quest("p", ["q"], 1, 1),
            "q": Quest("q", ["p"], 1, 1),
            "z": Quest("z", ["p"], 1, 1),
        }
        self.assertEqual(detect_cycles(quests), [["p", "q"], ["x", "y"]])

    def test_longer_cycle_all_members_reported(self):
        quests = {
            "a": Quest("a", ["c"], 1, 1),
            "b": Quest("b", ["a"], 1, 1),
            "c": Quest("c", ["b"], 1, 1),
            "d": Quest("d", ["a"], 1, 1),
        }
        self.assertEqual(detect_cycles(quests), [["a", "b", "c"]])


def _reference_run(quests, events):
    """参考实现：按依赖偏序 + 封顶，直白逐条模拟。"""
    progress = {name: 0 for name in quests}
    done = set()
    completed = []
    rewards = 0
    for event in events:
        name = event["name"]
        quest = quests[name]
        if name in done:
            continue
        progress[name] = min(quest.need, progress[name] + event.get("count", 1))
        if progress[name] >= quest.need and all(r in done for r in quest.requires):
            done.add(name)
            completed.append(name)
            rewards += quest.reward
    return completed, rewards


def _reference_cycle_names(quests):
    """参考实现：每个任务沿 requires 走，能回到自己就在环上。O(V*(V+E))。"""
    in_cycle = set()
    for name in quests:
        seen = set()
        stack = [name]
        while stack:
            node = stack.pop()
            for nxt in quests[node].requires:
                if nxt == name:
                    in_cycle.add(name)
                elif nxt in quests and nxt not in seen:
                    seen.add(nxt)
                    stack.append(nxt)
    return in_cycle


class FuzzTest(unittest.TestCase):
    def test_matches_reference_on_random_graphs(self):
        import random

        rng = random.Random(20260930)
        for trial in range(200):
            size = rng.randint(1, 30)
            names = ["q%d" % i for i in range(size)]
            quests = {}
            for name in names:
                requires = [n for n in names if rng.random() < 0.08]
                if rng.random() < 0.02:
                    requires.append("missing")  # 依赖不存在的任务
                quests[name] = Quest(name, requires, rng.randint(1, 5),
                                     rng.randint(1, 20))
            events = []
            for _ in range(rng.randint(0, 120)):
                event = {"name": rng.choice(names)}
                if rng.random() < 0.2:
                    event["count"] = rng.randint(1, 4)
                events.append(event)

            report = run(quests, events)
            expected_completed, expected_rewards = _reference_run(quests, events)
            expected_cycle_names = _reference_cycle_names(quests)

            self.assertEqual(report["completed"], expected_completed,
                             "trial %d completed" % trial)
            self.assertEqual(report["rewards"], expected_rewards,
                             "trial %d rewards" % trial)
            actual_cycle_names = {n for group in report["cycles"] for n in group}
            self.assertEqual(actual_cycle_names, expected_cycle_names,
                             "trial %d cycles" % trial)

            # 不变量
            self.assertEqual(len(report["completed"]),
                             len(set(report["completed"])))
            for group in report["cycles"]:
                self.assertEqual(group, sorted(group))
            self.assertEqual(report["cycles"], sorted(report["cycles"]))
            for name, value in report["progress"].items():
                self.assertGreaterEqual(value, 0)
                self.assertLessEqual(value, quests[name].need)
            position = {name: i for i, name in enumerate(report["completed"])}
            for name in report["completed"]:
                for required in quests[name].requires:
                    if required in position:
                        self.assertLess(position[required], position[name])
            # 同一批事件重复执行结果相同
            again = run(quests, events)
            self.assertEqual(again["completed"], report["completed"])
            self.assertEqual(again["rewards"], report["rewards"])
            self.assertEqual(again["cycles"], report["cycles"])
            self.assertEqual(again["progress"], report["progress"])
