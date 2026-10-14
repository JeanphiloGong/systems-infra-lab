"""A current-state row cannot explain how an order changed."""
import json


def current_state():
    return {"order-1": "paid"}


def experiment():
    state = current_state()
    assert state["order-1"] == "paid"
    return {"state": state, "history_available": False, "explanation": "current row stores result only"}


if __name__ == "__main__":
    print(json.dumps(experiment()))
