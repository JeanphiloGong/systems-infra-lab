import json
import sys

from model import HACluster


def run(version: int):
    cluster = HACluster()
    cluster.write("a", "order", "one")
    if version == 0:
        cluster.stop("a"); cluster.tick(3)
        return {"rto_window": cluster.now, "rpo_rows": cluster.nodes["b"].rows}
    if version == 1:
        cluster.stop("a"); cluster.promote("b"); cluster.write("b", "order", "two")
        return {"primary": cluster.primary, "confirmed": cluster.nodes["b"].rows}
    if version == 2:
        cluster.stop("a"); cluster.tick(6)
        return {"automatic_primary": cluster.primary, "generation": cluster.generation}
    if version == 3:
        cluster.isolate("a"); cluster.promote("b")
        try:
            cluster.write("a", "order", "stale")
        except RuntimeError:
            fenced = True
        else:
            fenced = False
        cluster.write("b", "order", "two")
        return {"old_primary_fenced": fenced, "new_value": cluster.nodes["b"].rows["order"]}
    if version == 4:
        cluster.stop("a"); cluster.promote("b"); cluster.write("b", "order", "two")
        cluster.nodes["a"].alive = True; cluster.rejoin("a"); cluster.promote("a"); cluster.write("a", "order", "three")
        return {"cutover_primary": cluster.primary, "rows": cluster.nodes["a"].rows}
    raise ValueError("version must be 0..4")


if __name__ == "__main__":
    print(json.dumps(run(int(sys.argv[1])), sort_keys=True))
