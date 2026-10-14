# D01 tutorial plan

1. v0: replay after a lost response creates two orders.
2. v1: request keys return the original order and reject missing keys.
3. v2: transaction boundaries distinguish a crash before commit from a response loss after commit.
4. v3: payload conflicts, processing records, response replay, and retention expiry are explicit.
5. v4: local order deduplication cannot deduplicate an external mail side effect unless the receiver also honors the idempotency key.

The replay tests extract one complete source fence per version and execute it independently.

