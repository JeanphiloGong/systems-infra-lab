# F03 v1: classify failures and enforce a deadline

Immediate retry is wasteful when the dependency rejects the request permanently. This version retries only `RetryableError` and stops at a total deadline. The deadline is a budget for the retry loop, not an excuse to retry a permanent error.

将下面的完整代码保存为 `labs/traffic/resilience/v1.py`；文件已存在时，以本版内容替换该文件。

<!-- checkpoint: labs/traffic/resilience/v1.py -->

```python
from __future__ import annotations

import time
from typing import Callable, TypeVar


class RetryableError(Exception):
    """A failure that may succeed on a later attempt."""


class PermanentError(Exception):
    """A failure that must be returned without retrying."""


T = TypeVar("T")


def call(
    operation: Callable[[], T],
    max_attempts: int = 3,
    deadline: float = 1.0,
    clock: Callable[[], float] = time.monotonic,
) -> tuple[T, int]:
    if max_attempts < 1 or deadline < 0:
        raise ValueError("invalid retry policy")
    started = clock()
    for attempt in range(1, max_attempts + 1):
        try:
            return operation(), attempt
        except PermanentError:
            raise
        except RetryableError:
            if attempt == max_attempts or clock() - started >= deadline:
                raise TimeoutError("retry deadline exceeded")
    raise AssertionError("unreachable")


if __name__ == "__main__":
    print(call(lambda: "ok"))
```

## 运行当前检查点

按上面的路径保存完整文件后，从仓库根目录运行：

```bash
uv run python labs/traffic/resilience/v1.py
```

对照本页描述的状态、输出或断言；若没有出现预期结果，先停在当前版检查，不直接进入下一版。
