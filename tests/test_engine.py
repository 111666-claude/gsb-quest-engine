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


def reference_run(quests, events):
    """参考实现：按依赖偏序 + 封顶，逐事件后反复全图扫描直到没有新完成。"""
    progress = {name: 0 for name in quests}
    done = set()
    completed = []
    rewards = 0
    for event in events:
        name = event["name"]
        if name in done:
            continue
        quest = quests[name]
        progress[name] = min(quest.need, progress[name] + event.get("count", 1))
        while True:
            advanced = False
            for cand, cand_quest in quests.items():
                if cand in done or progress[cand] < cand_quest.need:
                    continue
                if all(req in done for req in cand_quest.requires):
                    done.add(cand)
                    completed.append(cand)
                    rewards += cand_quest.reward
                    advanced = True
            if not advanced:
                break
    return completed, rewards


def reference_cycle_names(quests):
    """参考实现：能沿 requires 走回自己的任务即为成环。"""
    result = []
    for name in quests:
        seen = set()
        stack = list(quests[name].requires)
        found = False
        while stack:
            current = stack.pop()
            if current == name:
                found = True
                break
            if current in seen or current not in quests:
                continue
            seen.add(current)
            stack.extend(quests[current].requires)
        if found:
            result.append(name)
    return sorted(result)


def reference_cycle_group_count(quests):
    """参考实现：成环任务按互相可达聚成组，返回组数。"""
    def reaches(src, dst):
        seen = set()
        stack = [src]
        while stack:
            current = stack.pop()
            for nxt in quests[current].requires:
                if nxt == dst:
                    return True
                if nxt in quests and nxt not in seen:
                    seen.add(nxt)
                    stack.append(nxt)
        return False

    groups = []
    for name in reference_cycle_names(quests):
        for group in groups:
            if reaches(name, group[0]) and reaches(group[0], name):
                group.append(name)
                break
        else:
            groups.append([name])
    return len(groups)


class PrerequisiteTest(unittest.TestCase):
    def test_prereq_not_done_blocks_completion_but_counts_progress(self):
        quests = {"a": Quest("a", [], 1, 5), "b": Quest("b", ["a"], 2, 7)}
        report = run(quests, [{"name": "b"}, {"name": "b"}])
        self.assertEqual(report["completed"], [])
        self.assertEqual(report["rewards"], 0)
        self.assertEqual(report["progress"]["b"], 2)

    def test_completion_cascades_once_prereq_done(self):
        quests = {"a": Quest("a", [], 1, 5), "b": Quest("b", ["a"], 2, 7)}
        report = run(quests, [{"name": "b"}, {"name": "b"}, {"name": "a"}])
        self.assertEqual(report["completed"], ["a", "b"])
        self.assertEqual(report["rewards"], 12)

    def test_mutual_dependency_never_completes(self):
        quests = {"a": Quest("a", ["b"], 1, 10), "b": Quest("b", ["a"], 1, 5)}
        report = run(quests, [{"name": "a"}, {"name": "b"}, {"name": "a"}])
        self.assertEqual(report["completed"], [])
        self.assertEqual(report["rewards"], 0)


class CapTest(unittest.TestCase):
    def test_extra_events_no_extra_reward(self):
        report = run({"c": Quest("c", [], 3, 7)}, [{"name": "c"} for _ in range(4)])
        self.assertEqual(report["completed"], ["c"])
        self.assertEqual(report["rewards"], 7)
        self.assertEqual(report["progress"]["c"], 3)

    def test_count_event_capped_at_need(self):
        report = run({"c": Quest("c", [], 3, 7)}, [{"name": "c", "count": 10}])
        self.assertEqual(report["progress"]["c"], 3)
        self.assertEqual(report["completed"], ["c"])
        self.assertEqual(report["rewards"], 7)


class CycleDetectTest(unittest.TestCase):
    def test_mutual_cycle_reports_both_names_sorted(self):
        quests = {
            "b": Quest("b", ["a"], 1, 1),
            "a": Quest("a", ["b"], 1, 1),
            "c": Quest("c", [], 1, 1),
        }
        self.assertEqual(detect_cycles(quests), ["a", "b"])

    def test_self_loop(self):
        self.assertEqual(detect_cycles({"a": Quest("a", ["a"], 1, 1)}), ["a"])

    def test_longer_cycle(self):
        quests = {
            "a": Quest("a", ["c"], 1, 1),
            "b": Quest("b", ["a"], 1, 1),
            "c": Quest("c", ["b"], 1, 1),
            "d": Quest("d", ["a"], 1, 1),
        }
        self.assertEqual(detect_cycles(quests), ["a", "b", "c"])

    def test_acyclic_graph(self):
        quests = {"a": Quest("a", [], 1, 1), "b": Quest("b", ["a"], 1, 1)}
        self.assertEqual(detect_cycles(quests), [])


class InvariantTest(unittest.TestCase):
    def test_replay_same_events_same_result(self):
        from quests.engine import sample
        quests, events = sample()
        first = run(quests, events)
        second = run(quests, events)
        self.assertEqual(first["completed"], second["completed"])
        self.assertEqual(first["rewards"], second["rewards"])
        self.assertEqual(first["progress"], second["progress"])

    def test_completed_unique_and_respects_partial_order(self):
        quests = {
            "a": Quest("a", [], 1, 1),
            "b": Quest("b", ["a"], 1, 1),
            "c": Quest("c", ["b"], 1, 1),
        }
        events = [{"name": "c"}, {"name": "b"}, {"name": "a"}]
        report = run(quests, events)
        self.assertEqual(len(set(report["completed"])), len(report["completed"]))
        position = {name: i for i, name in enumerate(report["completed"])}
        for name in report["completed"]:
            for req in quests[name].requires:
                self.assertLess(position[req], position[name])


class ReferenceCrossCheckTest(unittest.TestCase):
    def test_random_graphs_against_reference(self):
        import random
        for seed in range(200):
            rng = random.Random(seed)
            names = ["q%d" % i for i in range(rng.randint(1, 12))]
            quests = {}
            for name in names:
                requires = [rng.choice(names) for _ in range(rng.randint(0, 3))]
                quests[name] = Quest(name, requires, rng.randint(1, 4), rng.randint(1, 9))
            events = []
            for _ in range(rng.randint(0, 60)):
                event = {"name": rng.choice(names)}
                if rng.random() < 0.3:
                    event["count"] = rng.randint(1, 3)
                events.append(event)
            report = run(quests, events)
            ref_completed, ref_rewards = reference_run(quests, events)
            label = "seed=%d" % seed
            self.assertEqual(report["completed"], ref_completed, label)
            self.assertEqual(report["rewards"], ref_rewards, label)
            self.assertEqual(detect_cycles(quests), reference_cycle_names(quests), label)
            self.assertEqual(
                len(report["cycles"]), reference_cycle_group_count(quests), label)
            flat = sorted(name for group in report["cycles"] for name in group)
            self.assertEqual(flat, detect_cycles(quests), label)
            self.assertEqual(
                len(set(report["completed"])), len(report["completed"]), label)
            position = {name: i for i, name in enumerate(report["completed"])}
            for name in report["completed"]:
                for req in quests[name].requires:
                    self.assertIn(req, position, label)
                    self.assertLess(position[req], position[name], label)
            for name, prog in report["progress"].items():
                self.assertGreaterEqual(prog, 0, label)
                self.assertLessEqual(prog, quests[name].need, label)
