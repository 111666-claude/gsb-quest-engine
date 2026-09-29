"""任务链求值：前置条件、计数上限、奖励发放与循环依赖。

口径（README 为准）：
- 前置必须先完成：requires 里的任务全部完成之前，事件只记进度，不能完成也不发奖。
- 进度封顶在 need：多余事件不再发奖，也不能重复完成。
- detect_cycles 返回所有成环（含互相依赖与自环）的任务名字，按名字排序。
- run 报告的 cycles 为成环分组列表（每组内按名字排序），len 即环的个数。
"""

import heapq


class Quest:
    """一个任务。"""

    def __init__(self, name, requires, need, reward):
        self.name = name
        self.requires = list(requires)
        self.need = need
        self.reward = reward


def detect_cycles(quests):
    """返回所有处在依赖环上的任务名字（含互相依赖与自环），按名字排序。"""
    members = []
    for group in _cycle_groups(quests):
        members.extend(group)
    members.sort()
    return members


def _cycle_groups(quests):
    """按强连通分量找出所有依赖环，返回分组列表（组内按名字排序）。

    迭代式 Tarjan：大小大于 1 的分量、或带自环的单点分量即为环。
    """
    index_of = {}
    lowlink = {}
    on_stack = set()
    stack = []
    groups = []
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
            node, edges = work[-1]
            descended = False
            for nxt in edges:
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
            if work and lowlink[node] < lowlink[work[-1][0]]:
                lowlink[work[-1][0]] = lowlink[node]
            if lowlink[node] == index_of[node]:
                scc = []
                while True:
                    member = stack.pop()
                    on_stack.discard(member)
                    scc.append(member)
                    if member == node:
                        break
                if len(scc) > 1:
                    scc.sort()
                    groups.append(scc)
                elif node in quests[node].requires:
                    groups.append([node])
    groups.sort()
    return groups


def run(quests, events):
    """按口径求值事件流：前置校验、进度封顶、完成级联。

    完成顺序与「每条事件后按字典序反复扫描直到没有新完成」的参考实现一致：
    每个完成的任务带名次 (扫描轮次, 字典序位置)，用堆按名次弹出。
    任务的轮次 = 使其前置清零的那个前置任务的轮次（若自身位置在其之后）
    否则再加一。均摊 O(1) 处理每条事件，内存 O(任务数)。
    """
    progress = {}
    completed = []
    completed_set = set()
    rewards = 0

    position = {name: i for i, name in enumerate(quests)}
    # 每个任务还差多少个前置未完成； dependents 为反向邻接表。
    pending = {}
    dependents = {}
    for name, quest in quests.items():
        pending[name] = len(quest.requires)
        for req in quest.requires:
            dependents.setdefault(req, []).append(name)

    ready = []  # (轮次, 位置, 任务名) 小顶堆
    seeded = False
    for event in events:
        if not seeded:
            # need <= 0 且无前置的任务在首次扫描即完成，与参考实现一致。
            seeded = True
            for name, quest in quests.items():
                if quest.need <= 0 and pending[name] == 0:
                    heapq.heappush(ready, (1, position[name], name))
        quest = quests[event["name"]]
        name = quest.name
        if name not in completed_set:
            prog = progress.get(name, 0)
            if prog < quest.need:
                prog += event.get("count", 1)
                if prog > quest.need:
                    prog = quest.need
                progress[name] = prog
            if pending[name] == 0 and progress.get(name, 0) >= quest.need:
                heapq.heappush(ready, (1, position[name], name))
        # 级联：前置刚完成的任务可能使依赖它的任务满足完成条件。
        while ready:
            rank_pass, rank_pos, current = heapq.heappop(ready)
            if current in completed_set:
                continue
            cur_quest = quests[current]
            if pending[current] != 0 or progress.get(current, 0) < cur_quest.need:
                continue
            completed.append(current)
            completed_set.add(current)
            rewards += cur_quest.reward
            for dependent in dependents.get(current, ()):
                pending[dependent] -= 1
                if (pending[dependent] == 0
                        and dependent not in completed_set
                        and progress.get(dependent, 0) >= quests[dependent].need):
                    dep_pos = position[dependent]
                    dep_pass = rank_pass if dep_pos > rank_pos else rank_pass + 1
                    heapq.heappush(ready, (dep_pass, dep_pos, dependent))

    return {
        "completed": completed,
        "rewards": rewards,
        "cycles": _cycle_groups(quests),
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
