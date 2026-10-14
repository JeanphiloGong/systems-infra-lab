# Q01 v1: normalize dependencies and join at read time

<!-- checkpoint: checkpoint.py -->
```python
customers={1:"Ada"}; products={7:"Widget"}; orders={10:(1,7,12)}
customers[1]="A. Lovelace"
row={"customer":customers[orders[10][0]],"product":products[orders[10][1]],"price":orders[10][2]}
assert row == {"customer":"A. Lovelace","product":"Widget","price":12}
try: orders[11]=(9,7,1); assert orders[11][0] in customers
except AssertionError: print({"join":row,"foreign_key_rejected":True})
```

The dependency `customer_id -> customer_name` is stored once. The join adds read work but prevents update anomalies; price remains an order snapshot.
