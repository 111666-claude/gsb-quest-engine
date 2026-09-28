# quest-engine

任务链求值：前置条件、计数、奖励与循环依赖，只用 Python 标准库。

```
python3 -m quests.cli --quests sample
python3 -m unittest discover -s tests -v
```

## 口径（README 为准）

- **前置必须先完成**：事件到达时 `requires` 里的任务都要已完成，否则这次事件只记进度，
  不能完成、也不发奖。`--quests sample` 里 a 依赖 b、b 依赖 a，按口径 a 与 b 永远完不成。
- **进度封顶**：达到 `need` 后封顶在 `need`，多余事件不能再发一次奖励。
  `--quests sample`（c 需要 3 次、事件给了 4 次）按口径是 `completed=c`、`rewardss` 为 7、
  `completed_count=1`，现在超额又发一遍，给 `rewards=29`、`completed_count=4`。
- **循环依赖要报出来**：`detect_cycles` 要返回所有互相（或成环）依赖的任务名字，按名字排序。
  `--quests sample` 按口径是 `cycles=1`（a 与 b 成环），现在恒为 0。
- 不变量：同一批事件重复执行结果相同；`completed` 里每个任务最多出现一次；
  进度单调不减且 ≤ `need`；完成顺序满足依赖偏序。
- 规模：10 万任务、100 万事件 3 秒内跑完，内存 O(任务数)；不许每条事件都重扫整张依赖图。

## 现在的行为

- `run` 完全不看 `quest.requires`：事件到了就累计、够了就完成。
- 进度不封顶：`progress >= need` 之后每来一条同类事件都会再发一次奖励。
- `detect_cycles` 直接 `return []`，环检测没实现。

## 计划新增的能力

```
--quests sample
```

## 输出

```
completed=c
completed_count=1 rewards=7 cycles=1
```

## 目录

```
quests/engine.py   前置、计数与环检测
quests/cli.py      命令行入口
tests/             unittest 用例
```
