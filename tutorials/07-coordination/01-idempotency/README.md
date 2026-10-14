# D01: idempotency and the exactly-once boundary

This tutorial follows an order request whose response can be lost after the server acts.

- v0 reproduces duplicate orders.
- v1 adds a request key and serialized deduplication.
- v2 stores the business record and deduplication result in one modeled transaction.
- v3 binds a key to a payload fingerprint, exposes processing state, replays completed responses, and expires records.
- v4 adds an external mail receiver to show the scope of local exactly-once behavior.

Exactly-once is scoped to a durable key, payload, effect store, and retention window. It never means the network delivers a request only once.

