---
name: transformations
title: Polars data transformations
description: Comprehensive guide to joins, concatenation, pivoting, unpivoting, exploding, and reshaping operations in Polars. Load when combining DataFrames or reshaping data structures.
principles:
  - Filter DataFrames before joining to reduce data processed
  - Use appropriate join types to minimize result size
  - Rechunk after concatenation for better subsequent performance
  - Pivot and unpivot are inverses for reshaping between wide and long formats
best_practices:
  - "**Filter before joining**: Reduce data size before expensive join operations"
  - "**Use semi/anti joins over inner+filter**: More efficient for filtering by existence"
  - "**Rechunk after concatenation**: Use `rechunk=True` for better performance"
  - "**Use asof joins for time-series**: Join to nearest timestamp efficiently"
checklist:
  - Join type matches the use case (inner, left, outer, semi, anti)
  - DataFrames filtered before joining where possible
  - Concatenation uses rechunk=True for many DataFrames
  - Column name conflicts handled with suffix parameter
related:
  - operations
  - best-practices
---

# Polars data transformations

Comprehensive guide to joins, concatenation, and reshaping operations in Polars.

## Joins

Joins combine data from multiple DataFrames based on common columns.

### Basic join types

**Inner join (intersection):**

```python
# Keep only matching rows from both DataFrames
result = df1.join(df2, on="id", how="inner")
```

**Left join (all left + matches from right):**

```python
# Keep all rows from left, add matching rows from right
result = df1.join(df2, on="id", how="left")
```

**Outer join (union):**

```python
# Keep all rows from both DataFrames
result = df1.join(df2, on="id", how="outer")
```

**Cross join (Cartesian product):**

```python
# Every row from left with every row from right
result = df1.join(df2, how="cross")
```

**Semi join (filtered left):**

```python
# Keep only left rows that have a match in right
result = df1.join(df2, on="id", how="semi")
```

**Anti join (non-matching left):**

```python
# Keep only left rows that DON'T have a match in right
result = df1.join(df2, on="id", how="anti")
```

### Join syntax variations

**Single column join:**

```python
df1.join(df2, on="id")
```

**Multiple columns join:**

```python
df1.join(df2, on=["id", "date"])
```

**Different column names:**

```python
df1.join(df2, left_on="user_id", right_on="id")
```

**Multiple different columns:**

```python
df1.join(
    df2,
    left_on=["user_id", "date"],
    right_on=["id", "timestamp"]
)
```

### Suffix handling

When both DataFrames have columns with the same name (other than join keys):

```python
# Add suffixes to distinguish columns
result = df1.join(df2, on="id", suffix="_right")

# Results in: value, value_right (if both had "value" column)
```

### Join examples

**Example 1: Customer orders**

```python
customers = pl.DataFrame({
    "customer_id": [1, 2, 3, 4],
    "name": ["Alice", "Bob", "Charlie", "David"]
})

orders = pl.DataFrame({
    "order_id": [101, 102, 103],
    "customer_id": [1, 2, 1],
    "amount": [100, 200, 150]
})

# Inner join - only customers with orders
result = customers.join(orders, on="customer_id", how="inner")

# Left join - all customers, even without orders
result = customers.join(orders, on="customer_id", how="left")
```

**Example 2: Time-series data**

```python
prices = pl.DataFrame({
    "date": ["2023-01-01", "2023-01-02", "2023-01-03"],
    "stock": ["AAPL", "AAPL", "AAPL"],
    "price": [150, 152, 151]
})

volumes = pl.DataFrame({
    "date": ["2023-01-01", "2023-01-02"],
    "stock": ["AAPL", "AAPL"],
    "volume": [1000000, 1100000]
})

result = prices.join(
    volumes,
    on=["date", "stock"],
    how="left"
)
```

### Asof joins (nearest match)

For time-series data, join to nearest timestamp:

```python
# Join to nearest earlier timestamp
quotes = pl.DataFrame({
    "timestamp": [1, 2, 3, 4, 5],
    "stock": ["A", "A", "A", "A", "A"],
    "quote": [100, 101, 102, 103, 104]
})

trades = pl.DataFrame({
    "timestamp": [1.5, 3.5, 4.2],
    "stock": ["A", "A", "A"],
    "trade": [50, 75, 100]
})

result = trades.join_asof(
    quotes,
    on="timestamp",
    by="stock",
    strategy="backward"  # or "forward", "nearest"
)
```

## Concatenation

Concatenation stacks DataFrames together.

### Vertical concatenation (stack rows)

```python
df1 = pl.DataFrame({"a": [1, 2], "b": [3, 4]})
df2 = pl.DataFrame({"a": [5, 6], "b": [7, 8]})

# Stack rows
result = pl.concat([df1, df2], how="vertical")
# Result: 4 rows, same columns
```

**Handling mismatched schemas:**

```python
df1 = pl.DataFrame({"a": [1, 2], "b": [3, 4]})
df2 = pl.DataFrame({"a": [5, 6], "c": [7, 8]})

# Diagonal concat - fills missing columns with nulls
result = pl.concat([df1, df2], how="diagonal")
# Result: columns a, b, c (with nulls where not present)
```

### Horizontal concatenation (stack columns)

```python
df1 = pl.DataFrame({"a": [1, 2, 3]})
df2 = pl.DataFrame({"b": [4, 5, 6]})

# Stack columns
result = pl.concat([df1, df2], how="horizontal")
# Result: 3 rows, columns a and b
```

**Note:** Horizontal concat requires same number of rows.

### Concatenation options

```python
# Rechunk after concatenation (better performance for subsequent operations)
result = pl.concat([df1, df2], rechunk=True)

# Parallel execution
result = pl.concat([df1, df2], parallel=True)
```

### Use cases

**Combining data from multiple sources:**

```python
# Read multiple files and concatenate
files = ["data_2023.csv", "data_2024.csv", "data_2025.csv"]
dfs = [pl.read_csv(f) for f in files]
combined = pl.concat(dfs, how="vertical")
```

**Adding computed columns:**

```python
base = pl.DataFrame({"value": [1, 2, 3]})
computed = pl.DataFrame({"doubled": [2, 4, 6]})
result = pl.concat([base, computed], how="horizontal")
```

## Pivoting (wide format)

Convert unique values from one column into multiple columns.

### Basic pivot

```python
df = pl.DataFrame({
    "date": ["2023-01", "2023-01", "2023-02", "2023-02"],
    "product": ["A", "B", "A", "B"],
    "sales": [100, 150, 120, 160]
})

# Pivot: products become columns
pivoted = df.pivot(
    values="sales",
    index="date",
    columns="product"
)
# Result:
# date     | A   | B
# 2023-01  | 100 | 150
# 2023-02  | 120 | 160
```

### Pivot with aggregation

When there are duplicate combinations, aggregate:

```python
df = pl.DataFrame({
    "date": ["2023-01", "2023-01", "2023-01"],
    "product": ["A", "A", "B"],
    "sales": [100, 110, 150]
})

# Aggregate duplicates
pivoted = df.pivot(
    values="sales",
    index="date",
    columns="product",
    aggregate_function="sum"  # or "mean", "max", "min", etc.
)
```

### Multiple index columns

```python
df = pl.DataFrame({
    "region": ["North", "North", "South", "South"],
    "date": ["2023-01", "2023-01", "2023-01", "2023-01"],
    "product": ["A", "B", "A", "B"],
    "sales": [100, 150, 120, 160]
})

pivoted = df.pivot(
    values="sales",
    index=["region", "date"],
    columns="product"
)
```

## Unpivoting/melting (long format)

Convert multiple columns into rows (opposite of pivot).

### Basic unpivot

```python
df = pl.DataFrame({
    "date": ["2023-01", "2023-02"],
    "product_A": [100, 120],
    "product_B": [150, 160]
})

# Unpivot: convert columns to rows
unpivoted = df.unpivot(
    index="date",
    on=["product_A", "product_B"]
)
# Result:
# date     | variable   | value
# 2023-01  | product_A  | 100
# 2023-01  | product_B  | 150
# 2023-02  | product_A  | 120
# 2023-02  | product_B  | 160
```

### Custom column names

```python
unpivoted = df.unpivot(
    index="date",
    on=["product_A", "product_B"],
    variable_name="product",
    value_name="sales"
)
```

### Unpivot by pattern

```python
# Unpivot all columns matching pattern
df = pl.DataFrame({
    "id": [1, 2],
    "sales_Q1": [100, 200],
    "sales_Q2": [150, 250],
    "sales_Q3": [120, 220],
    "revenue_Q1": [1000, 2000]
})

# Unpivot all sales columns
unpivoted = df.unpivot(
    index="id",
    on=pl.col("^sales_.*$")
)
```

## Exploding (unnesting lists)

Convert list columns into multiple rows.

### Basic explode

```python
df = pl.DataFrame({
    "id": [1, 2],
    "values": [[1, 2, 3], [4, 5]]
})

# Explode list into rows
exploded = df.explode("values")
# Result:
# id | values
# 1  | 1
# 1  | 2
# 1  | 3
# 2  | 4
# 2  | 5
```

### Multiple column explode

```python
df = pl.DataFrame({
    "id": [1, 2],
    "letters": [["a", "b"], ["c", "d"]],
    "numbers": [[1, 2], [3, 4]]
})

# Explode multiple columns (must be same length)
exploded = df.explode("letters", "numbers")
```

## Transposing

Swap rows and columns:

```python
df = pl.DataFrame({
    "metric": ["sales", "costs", "profit"],
    "Q1": [100, 60, 40],
    "Q2": [150, 80, 70]
})

# Transpose
transposed = df.transpose(
    include_header=True,
    header_name="quarter",
    column_names="metric"
)
# Result: quarters as rows, metrics as columns
```

## Reshaping patterns

### Pattern 1: Wide to long to wide

```python
# Start wide
wide = pl.DataFrame({
    "id": [1, 2],
    "A": [10, 20],
    "B": [30, 40]
})

# To long
long = wide.unpivot(index="id", on=["A", "B"])

# Back to wide (maybe with transformations)
wide_again = long.pivot(values="value", index="id", columns="variable")
```

### Pattern 2: Nested to flat

```python
# Nested data
df = pl.DataFrame({
    "user": [1, 2],
    "purchases": [
        [{"item": "A", "qty": 2}, {"item": "B", "qty": 1}],
        [{"item": "C", "qty": 3}]
    ]
})

# Explode and unnest
flat = (
    df.explode("purchases")
    .unnest("purchases")
)
```

### Pattern 3: Aggregation to pivot

```python
# Raw data
sales = pl.DataFrame({
    "date": ["2023-01", "2023-01", "2023-02"],
    "product": ["A", "B", "A"],
    "sales": [100, 150, 120]
})

# Aggregate then pivot
result = (
    sales
    .group_by("date", "product")
    .agg(pl.col("sales").sum())
    .pivot(values="sales", index="date", columns="product")
)
```

## Advanced transformations

### Conditional reshaping

```python
# Pivot only certain values
df.filter(pl.col("year") >= 2020).pivot(...)

# Unpivot with filtering
df.unpivot(index="id", on=pl.col("^sales.*$"))
```

### Multi-level transformations

```python
# Complex reshaping pipeline
result = (
    df
    .unpivot(index="id", on=pl.col("^Q[0-9]_.*$"))
    .with_columns(
        quarter=pl.col("variable").str.extract(r"Q([0-9])", 1),
        metric=pl.col("variable").str.extract(r"Q[0-9]_(.*)", 1)
    )
    .drop("variable")
    .pivot(values="value", index=["id", "quarter"], columns="metric")
)
```

## Performance considerations

### Join performance

```python
# 1. Join on indexed/sorted columns when possible
df1_sorted = df1.sort("id")
df2_sorted = df2.sort("id")
result = df1_sorted.join(df2_sorted, on="id")

# 2. Use appropriate join type
# semi/anti are faster than inner+filter
matches = df1.join(df2, on="id", how="semi")  # Better than filtering after inner join

# 3. Filter before joining
df1_filtered = df1.filter(pl.col("active"))
result = df1_filtered.join(df2, on="id")  # Smaller join
```

### Concatenation performance

```python
# 1. Rechunk after concatenation
result = pl.concat(dfs, rechunk=True)

# 2. Use lazy mode for large concatenations
lf1 = pl.scan_parquet("file1.parquet")
lf2 = pl.scan_parquet("file2.parquet")
result = pl.concat([lf1, lf2]).collect()
```

### Pivot performance

```python
# 1. Filter before pivoting
pivoted = df.filter(pl.col("year") == 2023).pivot(...)

# 2. Specify aggregate function explicitly
pivoted = df.pivot(..., aggregate_function="first")  # Faster than "sum" if only one value
```

## Common use cases

### Time series alignment

```python
# Align two time series with different timestamps
ts1.join_asof(ts2, on="timestamp", strategy="backward")
```

### Feature engineering

```python
# Create lag features
df.with_columns(
    pl.col("value").shift(1).over("user_id").alias("prev_value"),
    pl.col("value").shift(2).over("user_id").alias("prev_prev_value")
)
```

### Data denormalization

```python
# Combine normalized tables
orders.join(customers, on="customer_id").join(products, on="product_id")
```

### Report generation

```python
# Pivot for reporting
sales.pivot(values="amount", index="month", columns="product")
```
