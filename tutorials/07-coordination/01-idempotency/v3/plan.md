# D01 v3 计划

前版缺口是 key 可绑定不同 payload，且没有处理中状态。Pressure：dedup 必须绑定内容并有限保留。Naive：只按 key 返回结果。Break：同 key 不同 payload、processing、advance 超过 retention。Change：canonical JSON SHA-256 指纹、processing/completed、retention tick。Check：`uv run python labs/coordination/idempotency/v3.py` 和 replay 断言 ValueError、RuntimeError、完成响应重放。Freeze：v3 fence。Still-lacks：外部副作用。Next：v4。
