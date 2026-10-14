from threading import Barrier, Thread
from labs.coordination.locks.model import FencedResource, LockService


def test_competition_has_one_winner() -> None:
    service=LockService(); barrier=Barrier(2); results=[]
    def attempt(owner):
        barrier.wait(); results.append(service.acquire(owner,0,10))
    threads=[Thread(target=attempt,args=(owner,)) for owner in ("a","b")]
    [thread.start() for thread in threads]; [thread.join() for thread in threads]
    assert sum(result is not None for result in results)==1


def test_expiry_token_and_fencing() -> None:
    service=LockService(); first=service.acquire("a",0,1); second=service.acquire("b",2,1); resource=FencedResource(); resource.write(second.token,"new")
    try: resource.write(first.token,"old")
    except ValueError: pass
    else: raise AssertionError("stale write accepted")


def test_old_release_cannot_delete_new_lease() -> None:
    service=LockService(); first=service.acquire("a",0,1); second=service.acquire("b",2,1); service.release("a",first.token); assert service.lease == second


def test_renew_rejects_stale_and_extends_current_lease() -> None:
    service=LockService(); first=service.acquire("a",0,1); second=service.acquire("b",2,1)
    try: service.renew("a",first.token,2,3)
    except ValueError: pass
    else: raise AssertionError("stale renew accepted")
    renewed=service.renew("b",second.token,2,3)
    assert renewed.token == second.token and renewed.expires_at == 5
