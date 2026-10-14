# Q01 v2: add a maintained read model

<!-- checkpoint: checkpoint.py -->
```python
customers={1:"Ada"}; products={7:"Widget"}; orders={10:(1,7,12)}
view={order_id:{"customer":customers[c],"product":products[p],"price":price} for order_id,(c,p,price) in orders.items()}
products[7]="New Widget"
assert view[10]["product"] == "Widget"  # stale until maintained
view[10]["product"] = products[7]
assert view[10]["product"] == "New Widget"
print({"read_joins":0,"view_update_writes":1,"stale_window":True})
```

The duplicated name is now a deliberate read-model copy. Its owner must update it or rebuild it; denormalization is not automatic consistency.
