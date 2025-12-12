---
name: core-concepts
title: Polars core concepts
description: Detailed explanations of Polars expressions, data types, lazy vs eager evaluation, type system, and parallelization. Load when working with expression composition, type casting, null handling, or understanding query optimization.
principles:
  - Expressions are composable units that describe transformations without executing immediately
  - Lazy evaluation enables automatic query optimization before execution
  - Strict typing prevents silent bugs and ensures predictable behavior
  - Parallelization happens automatically when staying within the expression API
best_practices:
  - "**Use expressions over raw values**: Always use `pl.col()` to reference columns"
  - "**Prefer lazy mode for large data**: Use `scan_*` instead of `read_*`"
  - "**Cast types explicitly**: Polars won't silently convert types"
  - "**Stay in expression API**: Avoid Python functions to maintain parallelization"
checklist:
  - Expression uses proper context (select, with_columns, filter, group_by.agg)
  - Large datasets use lazy evaluation with scan_* functions
  - Type casts are explicit where needed
  - Null handling is intentional
related:
  - operations
  - best-practices
---

# Polars core concepts

## Expressions

Expressions are the foundation of Polars' API. They are composable units that describe data transformations without executing them immediately.

### What are expressions?

An expression describes a transformation on data. It only materializes (executes) within specific contexts:

- `select()` - Select and transform columns
- `with_columns()` - Add or modify columns
- `filter()` - Filter rows
- `group_by().agg()` - Aggregate data

### Expression syntax

**Basic column reference:**

```python
pl.col("column_name")
```

**Computed expressions:**

```python
# Arithmetic
pl.col("height") * 2
pl.col("price") + pl.col("tax")

# With alias
(pl.col("weight") / (pl.col("height") ** 2)).alias("bmi")

# Method chaining
pl.col("name").str.to_uppercase().str.slice(0, 3)
```

### Expression contexts

**Select context:**

```python
df.select(
    "name",  # Simple column name
    pl.col("age"),  # Expression
    (pl.col("age") * 12).alias("age_in_months")  # Computed expression
)
```

**With_columns context:**

```python
df.with_columns(
    age_doubled=pl.col("age") * 2,
    name_upper=pl.col("name").str.to_uppercase()
)
```

**Filter context:**

```python
df.filter(
    pl.col("age") > 25,
    pl.col("city").is_in(["NY", "LA", "SF"])
)
```

**Group_by context:**

```python
df.group_by("department").agg(
    pl.col("salary").mean(),
    pl.col("employee_id").count()
)
```

### Expression expansion

Apply operations to multiple columns at once:

**All columns:**

```python
df.select(pl.all() * 2)
```

**Pattern matching:**

```python
# All columns ending with "_value"
df.select(pl.col("^.*_value$") * 100)

# All numeric columns
df.select(pl.col(pl.NUMERIC_DTYPES) + 1)
```

**Exclude patterns:**

```python
df.select(pl.all().exclude("id", "name"))
```

### Expression composition

Expressions can be stored and reused:

```python
# Define reusable expressions
age_expression = pl.col("age") * 12
name_expression = pl.col("name").str.to_uppercase()

# Use in multiple contexts
df.select(age_expression, name_expression)
df.with_columns(age_months=age_expression)
```

## Data types

Polars has a strict type system based on Apache Arrow.

### Core data types

**Numeric:**

- `Int8`, `Int16`, `Int32`, `Int64` - Signed integers
- `UInt8`, `UInt16`, `UInt32`, `UInt64` - Unsigned integers
- `Float32`, `Float64` - Floating point numbers

**Text:**

- `Utf8` / `String` - UTF-8 encoded strings
- `Categorical` - Categorized strings (low cardinality)
- `Enum` - Fixed set of string values

**Temporal:**

- `Date` - Calendar date (no time)
- `Datetime` - Date and time with optional timezone
- `Time` - Time of day
- `Duration` - Time duration/difference

**Boolean:**

- `Boolean` - True/False values

**Nested:**

- `List` - Variable-length lists
- `Array` - Fixed-length arrays
- `Struct` - Nested record structures

**Other:**

- `Binary` - Binary data
- `Object` - Python objects (avoid in production)
- `Null` - Null type

### Type casting

Convert between types explicitly:

```python
# Cast to different type
df.select(
    pl.col("age").cast(pl.Float64),
    pl.col("date_string").str.strptime(pl.Date, "%Y-%m-%d"),
    pl.col("id").cast(pl.Utf8)
)
```

### Null handling

Polars uses consistent null handling across all types:

**Check for nulls:**

```python
df.filter(pl.col("value").is_null())
df.filter(pl.col("value").is_not_null())
```

**Fill nulls:**

```python
pl.col("value").fill_null(0)
pl.col("value").fill_null(strategy="forward")
pl.col("value").fill_null(strategy="backward")
pl.col("value").fill_null(strategy="mean")
```

**Drop nulls:**

```python
df.drop_nulls()  # Drop any row with nulls
df.drop_nulls(subset=["col1", "col2"])  # Drop rows with nulls in specific columns
```

### Categorical data

Use categorical types for string columns with low cardinality (repeated values):

```python
# Cast to categorical
df.with_columns(
    pl.col("category").cast(pl.Categorical)
)

# Benefits:
# - Reduced memory usage
# - Faster grouping and joining
# - Maintains order information
```

## Lazy vs eager evaluation

Polars supports two execution modes: eager (DataFrame) and lazy (LazyFrame).

### Eager evaluation (DataFrame)

Operations execute immediately:

```python
import polars as pl

# DataFrame operations execute right away
df = pl.read_csv("data.csv")  # Reads file immediately
result = df.filter(pl.col("age") > 25)  # Filters immediately
final = result.select("name", "age")  # Selects immediately
```

**When to use eager:**

- Small datasets that fit in memory
- Interactive exploration in notebooks
- Simple one-off operations
- Immediate feedback needed

### Lazy evaluation (LazyFrame)

Operations build a query plan, optimized before execution:

```python
import polars as pl

# LazyFrame operations build a query plan
lf = pl.scan_csv("data.csv")  # Doesn't read yet
lf2 = lf.filter(pl.col("age") > 25)  # Adds to plan
lf3 = lf2.select("name", "age")  # Adds to plan
df = lf3.collect()  # NOW executes optimized plan
```

**When to use lazy:**

- Large datasets
- Complex query pipelines
- Only need subset of data
- Performance is critical
- Streaming required

### Query optimization

Polars automatically optimizes lazy queries:

**Predicate pushdown:** Filter operations pushed to data source when possible:

```python
# Only reads rows where age > 25 from CSV
lf = pl.scan_csv("data.csv")
result = lf.filter(pl.col("age") > 25).collect()
```

**Projection pushdown:** Only read needed columns from data source:

```python
# Only reads "name" and "age" columns from CSV
lf = pl.scan_csv("data.csv")
result = lf.select("name", "age").collect()
```

**Query plan inspection:**

```python
# View the optimized query plan
lf = pl.scan_csv("data.csv")
result = lf.filter(pl.col("age") > 25).select("name", "age")
print(result.explain())  # Shows optimized plan
```

### Streaming mode

Process data larger than memory:

```python
# Enable streaming for very large datasets
lf = pl.scan_csv("very_large.csv")
result = lf.filter(pl.col("age") > 25).collect(streaming=True)
```

**Streaming benefits:**

- Process data larger than RAM
- Lower peak memory usage
- Chunk-based processing
- Automatic memory management

**Streaming limitations:**

- Not all operations support streaming
- May be slower for small data
- Some operations require materializing entire dataset

### Converting between eager and lazy

**Eager to lazy:**

```python
df = pl.read_csv("data.csv")
lf = df.lazy()  # Convert to LazyFrame
```

**Lazy to eager:**

```python
lf = pl.scan_csv("data.csv")
df = lf.collect()  # Execute and return DataFrame
```

## Memory format

Polars uses Apache Arrow columnar memory format:

**Benefits:**

- Zero-copy data sharing with other Arrow libraries
- Efficient columnar operations
- SIMD vectorization
- Reduced memory overhead
- Fast serialization

**Implications:**

- Data stored column-wise, not row-wise
- Column operations very fast
- Random row access slower than pandas
- Best for analytical workloads

## Parallelization

Polars parallelizes operations automatically using Rust's concurrency:

**What gets parallelized:**

- Aggregations within groups
- Window functions
- Most expression evaluations
- File reading (multiple files)
- Join operations

**What to avoid for parallelization:**

- Python user-defined functions (UDFs)
- Lambda functions in `.map_elements()`
- Sequential `.pipe()` chains

**Best practice:**

```python
# Good: Stays in expression API (parallelized)
df.with_columns(
    pl.col("value") * 10,
    pl.col("value").log(),
    pl.col("value").sqrt()
)

# Bad: Uses Python function (sequential)
df.with_columns(
    pl.col("value").map_elements(lambda x: x * 10)
)
```

## Strict type system

Polars enforces strict typing:

**No silent conversions:**

```python
# This will error - can't mix types
# df.with_columns(pl.col("int_col") + "string")

# Must cast explicitly
df.with_columns(
    pl.col("int_col").cast(pl.Utf8) + "_suffix"
)
```

**Benefits:**

- Prevents silent bugs
- Predictable behavior
- Better performance
- Clearer code intent

**Integer nulls:** Unlike pandas, integer columns can have nulls without converting to float:

```python
# In pandas: Int column with null becomes Float
# In polars: Int column with null stays Int (with null values)
df = pl.DataFrame({"int_col": [1, 2, None, 4]})
# dtype: Int64 (not Float64)
```
