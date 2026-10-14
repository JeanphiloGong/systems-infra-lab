# Q01 v3: compare read cost, write cost, and snapshot boundaries

<!-- checkpoint: checkpoint.py -->
```python
customers={1:"Ada"}; products={7:"Widget"}; orders={10:(1,7,12)}
normalized_reads=2  # customer and product lookups for one order
view={10:{"customer":"Ada","product":"Widget","price":12}}
denormalized_reads=1
products[7]="New Widget"; view_writes=1
assert view[10]["product"] == "Widget"  # stale copy
orders[11]=(1,7,13)  # a later order gets a new historical snapshot
assert orders[10][2] == 12 and orders[11][2] == 13 and view_writes == 1
print({"normalized_read_ops":normalized_reads,"denormalized_read_ops":denormalized_reads,"extra_write_ops":view_writes,"stale_read_model":True,"snapshot_price":orders[10][2]})
```

The read model saves joins but adds maintenance writes and a stale-read failure mode. Historical purchase price is not redundant current product data: it is part of the order fact and must remain unchanged when the product changes.
