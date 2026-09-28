"""任务链求值：前置条件、计数上限、奖励发放与循环依赖。

缺陷：不校验前置任务是否完成（能跳步）、进度超过需求还继续发奖、循环依赖检测还没实现。
"""


class Quest:
    """一个任务。"""

    def __init__(self, name, requires, need, reward):
        self.name = name
        self.requires = list(requires)
        self.need = need
        self.reward = reward


def detect_cycles(quests):
    """缺陷：还没实现，恒返回空列表。"""
    return []


def run(quests, events):
    """缺陷：不检查前置、进度不封顶。"""
    progress = {}
    completed = []
    rewards = 0
    for event in events:
        quest = quests[event["name"]]
        progress[quest.name] = progress.get(quest.name, 0) + event.get("count", 1)
        if progress[quest.name] >= quest.need:
            completed.append(quest.name)
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
