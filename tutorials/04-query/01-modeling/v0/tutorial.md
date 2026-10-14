# Q01 v0: duplicated customer data drifts

<!-- checkpoint: checkpoint.py -->
```python
orders=[{"id":1,"customer":"Ada","product":"Widget"},{"id":2,"customer":"Ada","product":"Widget"}]
orders[0]["customer"]="A. Lovelace"
assert orders[1]["customer"] != orders[0]["customer"]
print({"inconsistent_rows":2})
```

The same customer fact was written twice, so one update leaves a contradiction. This is the concrete pressure for normalization.
