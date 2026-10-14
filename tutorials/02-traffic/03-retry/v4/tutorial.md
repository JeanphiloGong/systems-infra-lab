# F03 v4：让多层重试真正执行，再共享预算

三层调用各允许三次尝试，最底层持续失败时，总请求数会乘到 27。只计算 3**3 或 min(27,10) 没有阻止任何调用。本章把三层递归调用实际组合起来，叶子操作每次进入都增加观测计数。

Budget 是整次上游请求共享的可消耗对象。只有叶子入口消费一次；剩余为零时抛 BudgetExhausted，各层只捕获 RetryableError，因此预算耗尽、永久失败、TimeoutError 都直接穿透，不会被外层当成一次新的重试机会。初次调用也消耗预算，早成功不消费尚未使用的额度。

## 一个总截止点、一份叶子预算

call_layers 在最外层计算一次 expires，所有层及叶子都检查同一 monotonic 时钟。失败操作时间和迟到成功都计入；不能在每一层重置时限。同步操作仍不能强制抢占；迟到结果被拒绝不代表外部副作用被撤销。预算只限制下游叶子次数，不限制所有中间函数进入次数；这是当前模型明确的计费边界。

amplification 中的 calls 来自 unavailable 真正被调用的次数。无预算运行得到 27，共享 Budget(10) 得到 10；从相同耗尽对象再次调用仍然不能执行叶子。它是单线程请求作用域的示范，不是线程安全的跨服务配额系统。

断路器抑制持续失败依赖的调用，速率限制控制单位时间到达量，背压约束在途工作；共享重试预算不能替代这些机制。这里为观察乘法效应故意不 sleep；生产调用链应同时有 v2 的退避/截止策略。

<!-- checkpoint: labs/traffic/resilience/budget.py -->

```python
from __future__ import annotations

from dataclasses import dataclass
import time
from typing import Callable, TypeVar


class RetryableError(Exception):
    pass


class PermanentError(Exception):
    pass


class BudgetExhausted(Exception):
    pass


@dataclass
class Budget:
    remaining: int

    def __post_init__(self) -> None:
        if self.remaining < 0:
            raise ValueError("negative budget")

    def consume(self) -> None:
        if self.remaining == 0:
            raise BudgetExhausted("leaf attempt budget exhausted")
        self.remaining -= 1


T = TypeVar("T")


def call_layers(
    operation: Callable[[], T], layers: int = 3, attempts: int = 3,
    budget: Budget | None = None, deadline: float = 1.0,
    clock: Callable[[], float] = time.monotonic,
) -> T:
    if layers < 1 or attempts < 1 or deadline < 0:
        raise ValueError("invalid retry policy")
    expires = clock() + deadline

    def check_time() -> None:
        if clock() >= expires:
            raise TimeoutError("shared deadline exceeded")

    def invoke(depth: int) -> T:
        check_time()
        if depth == 0:
            if budget is not None:
                budget.consume()
            check_time()
            try:
                result = operation()
            except RetryableError:
                check_time()
                raise
            check_time()
            return result
        for attempt in range(attempts):
            try:
                return invoke(depth - 1)
            except RetryableError:
                check_time()
                if attempt == attempts - 1:
                    raise
        raise AssertionError("unreachable")

    return invoke(layers)


def amplification(limit: int | None) -> int:
    calls = 0

    def unavailable() -> None:
        nonlocal calls
        calls += 1
        raise RetryableError("dependency unavailable")

    try:
        call_layers(unavailable, budget=None if limit is None else Budget(limit))
    except (RetryableError, BudgetExhausted):
        pass
    return calls


if __name__ == "__main__":
    print(amplification(None), amplification(10))
```

## 可执行检查

```bash
uv run python labs/traffic/resilience/budget.py
uv run python -m pytest tests/traffic/retry -q
```

下面的检查由测试从本文提取到空目录执行，依赖同样来自本文。27 与 10 必须来自真实叶子调用计数；另外检查早成功、永久错误和超时不会被外层重新尝试。

<!-- check: check_v4.py -->

```python
from budget import Budget, BudgetExhausted, RetryableError, PermanentError, call_layers, amplification

def expect(error, operation):
    try:
        operation()
    except error:
        return
    raise AssertionError(f"expected {error}")

assert amplification(None) == 27
assert amplification(10) == 10
calls = []
shared = Budget(10)
def fail():
    calls.append(1)
    raise RetryableError()
expect(BudgetExhausted, lambda: call_layers(fail, budget=shared))
assert len(calls) == 10 and shared.remaining == 0
expect(BudgetExhausted, lambda: call_layers(fail, budget=shared))
assert len(calls) == 10
expect(BudgetExhausted, lambda: call_layers(fail, budget=Budget(0)))
assert len(calls) == 10

calls = []
shared = Budget(10)
def succeed_second():
    calls.append(1)
    if len(calls) == 1:
        raise RetryableError()
    return "ok"
assert call_layers(succeed_second, budget=shared) == "ok"
assert len(calls) == 2 and shared.remaining == 8
def permanent():
    calls.append(1)
    raise PermanentError()
expect(PermanentError, lambda: call_layers(permanent, budget=shared))
assert len(calls) == 3 and shared.remaining == 7

now = [0.0]
calls = []
def slow():
    calls.append(1)
    now[0] += 0.06
    raise RetryableError()
expect(TimeoutError, lambda: call_layers(slow, budget=Budget(10), deadline=0.02, clock=lambda: now[0]))
assert len(calls) == 1
def late_success():
    calls.append(1)
    now[0] += 0.06
    return "late"
expect(TimeoutError, lambda: call_layers(late_success, deadline=0.02, clock=lambda: now[0]))
assert len(calls) == 2
expect(TimeoutError, lambda: call_layers(fail, deadline=0, clock=lambda: now[0]))
assert len(calls) == 2
print("executed 27 vs 10; terminal budget, success, permanent and deadline checks passed")
```

