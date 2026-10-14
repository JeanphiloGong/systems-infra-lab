# P03 plan

The scenario is moving integer-keyed records from one owner set to another while callers continue reading and writing. Versions add pause-and-copy, background copy, delta replay, a write barrier and route cutover, then restart/fencing. The examples are deterministic local dictionaries; they do not claim zero-downtime production migration.
