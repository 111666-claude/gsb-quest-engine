"""任务链求值：前置条件、计数上限、奖励发放与循环依赖。

口径（见 README）：
- 事件到达时 requires 里的任务必须都已完成，否则只记进度，不能完成也不发奖。
- 进度封顶在 need，多余事件不再发奖，也不会重复完成。
- detect_cycles 返回所有成环任务的名字分组，组内与组间均按名字排序。
"""


class Quest:
    """一个任务。"""

    def __init__(self, name, requires, need, reward):
        self.name = name
        self.requires = list(requires)
        self.need = need
        self.reward = reward


def detect_cycles(quests):
    """返回成环任务的分组列表：每组是一个强连通分量（含自环），组内名字排序，
    组与组之间也按名字排序。互相依赖的任务都在结果里。

    迭代版 Tarjan，O(任务数 + 依赖边数)，深链不会触发递归上限。
    """
    index_of = {}
    lowlink = {}
    on_stack = set()
    stack = []
    cycles = []
    counter = 0
    for root in quests:
        if root in index_of:
            continue
        index_of[root] = lowlink[root] = counter
        counter += 1
        stack.append(root)
        on_stack.add(root)
        work = [(root, iter(quests[root].requires))]
        while work:
            node, successors = work[-1]
            descended = False
            for nxt in successors:
                if nxt not in quests:
                    continue
                if nxt not in index_of:
                    index_of[nxt] = lowlink[nxt] = counter
                    counter += 1
                    stack.append(nxt)
                    on_stack.add(nxt)
                    work.append((nxt, iter(quests[nxt].requires)))
                    descended = True
                    break
                if nxt in on_stack and index_of[nxt] < lowlink[node]:
                    lowlink[node] = index_of[nxt]
            if descended:
                continue
            work.pop()
            if work:
                parent = work[-1][0]
                if lowlink[node] < lowlink[parent]:
                    lowlink[parent] = lowlink[node]
            if lowlink[node] == index_of[node]:
                scc = []
                while True:
                    member = stack.pop()
                    on_stack.discard(member)
                    scc.append(member)
                    if member == node:
                        break
                if len(scc) > 1 or node in quests[node].requires:
                    cycles.append(sorted(scc))
    cycles.sort()
    return cycles


def run(quests, events):
    """按口径求值：前置未齐只记进度；进度封顶 need；完成与发奖各只一次。"""
    progress = {}
    completed = []
    completed_set = set()
    rewards = 0
    for event in events:
        quest = quests[event["name"]]
        name = quest.name
        current = progress.get(name, 0)
        if current < quest.need:
            current += event.get("count", 1)
            if current > quest.need:
                current = quest.need
            progress[name] = current
        if name in completed_set or current < quest.need:
            continue
        for required in quest.requires:
            if required not in completed_set:
                break
        else:
            completed_set.add(name)
            completed.append(name)
            rewards += quest.reward
    return {
        "completed": completed,
        "rewards": rewards,
        "cycles": detect_cycles(quests),
        "progress": progress,
    }


def sample():
    """a 与 b 互相依赖（成环）；c 独立、需要 3 次，事件给了 4 次。"""
    quests = {
        "a": Quest("a", ["b"], 2, 10),
        "b": Quest("b", ["a"], 1, 5),
        "c": Quest("c", [], 3, 7),
    }
    events = [{"name": "c"} for _ in range(4)]
    events += [{"name": "a"}, {"name": "a"}, {"name": "b"}]
    return quests, events
