---
name: io-guide
title: Polars data I/O guide
description: Comprehensive guide to reading and writing data in various formats with Polars including CSV, Parquet, JSON, Excel, databases, cloud storage, and Arrow. Load when working with file I/O or data sources.
principles:
  - Use lazy mode (scan_*) for large files to enable query optimization
  - Prefer Parquet for large datasets due to compression and performance
  - Specify data types when known to avoid inference overhead
  - Use streaming for datasets larger than memory
best_practices:
  - "**Use scan_* instead of read_***: Enables predicate and projection pushdown"
  - "**Prefer Parquet over CSV**: Better compression, faster reads, type preservation"
  - "**Specify dtypes**: Avoid type inference overhead and ensure correctness"
  - "**Use streaming for very large data**: `collect(streaming=True)` or sink functions"
checklist:
  - Large files use lazy mode (scan_*)
  - Data types specified for CSV reads
  - Parquet used for performance-critical data
  - Cloud credentials configured for remote storage
related:
  - best-practices
  - core-concepts
---

# Polars data I/O guide

Comprehensive guide to reading and writing data in various formats with Polars.

## CSV files

### Reading CSV

**Eager mode (loads into memory):**

```python
import polars as pl

# Basic read
df = pl.read_csv("data.csv")

# With options
df = pl.read_csv(
    "data.csv",
    separator=",",
    has_header=True,
    columns=["col1", "col2"],  # Select specific columns
    n_rows=1000,  # Read only first 1000 rows
    skip_rows=10,  # Skip first 10 rows
    dtypes={"col1": pl.Int64, "col2": pl.Utf8},  # Specify types
    null_values=["NA", "null", ""],  # Define null values
    encoding="utf-8",
    ignore_errors=False
)
```

**Lazy mode (scans without loading - recommended for large files):**

```python
# Scan CSV (builds query plan)
lf = pl.scan_csv("data.csv")

# Apply operations
result = lf.filter(pl.col("age") > 25).select("name", "age")

# Execute and load
df = result.collect()
```

### Writing CSV

```python
# Basic write
df.write_csv("output.csv")

# With options
df.write_csv(
    "output.csv",
    separator=",",
    include_header=True,
    null_value="",  # How to represent nulls
    quote_char='"',
    line_terminator="\n"
)
```

### Multiple CSV files

**Read multiple files:**

```python
# Read all CSVs in directory
lf = pl.scan_csv("data/*.csv")

# Read specific files
lf = pl.scan_csv(["file1.csv", "file2.csv", "file3.csv"])
```

## Parquet files

Parquet is the recommended format for performance and compression.

### Reading Parquet

**Eager:**

```python
df = pl.read_parquet("data.parquet")

# With options
df = pl.read_parquet(
    "data.parquet",
    columns=["col1", "col2"],  # Select specific columns
    n_rows=1000,  # Read first N rows
    parallel="auto"  # Control parallelization
)
```

**Lazy (recommended):**

```python
lf = pl.scan_parquet("data.parquet")

# Automatic predicate and projection pushdown
result = lf.filter(pl.col("age") > 25).select("name", "age").collect()
```

### Writing Parquet

```python
# Basic write
df.write_parquet("output.parquet")

# With compression
df.write_parquet(
    "output.parquet",
    compression="snappy",  # Options: "snappy", "gzip", "brotli", "lz4", "zstd"
    statistics=True,  # Write statistics (enables predicate pushdown)
    use_pyarrow=False  # Use Rust writer (faster)
)
```

### Partitioned Parquet (Hive-style)

**Write partitioned:**

```python
# Write with partitioning
df.write_parquet(
    "output_dir",
    partition_by=["year", "month"]  # Creates directory structure
)
# Creates: output_dir/year=2023/month=01/data.parquet
```

**Read partitioned:**

```python
lf = pl.scan_parquet("output_dir/**/*.parquet")

# Hive partitioning columns are automatically added
result = lf.filter(pl.col("year") == 2023).collect()
```

## JSON files

### Reading JSON

**NDJSON (newline-delimited JSON) - recommended:**

```python
df = pl.read_ndjson("data.ndjson")

# Lazy
lf = pl.scan_ndjson("data.ndjson")
```

**Standard JSON:**

```python
df = pl.read_json("data.json")

# From JSON string
df = pl.read_json('{"col1": [1, 2], "col2": ["a", "b"]}')
```

### Writing JSON

```python
# Write NDJSON
df.write_ndjson("output.ndjson")

# Write standard JSON
df.write_json("output.json")

# Pretty printed
df.write_json("output.json", pretty=True, row_oriented=False)
```

## Excel files

### Reading Excel

```python
# Read first sheet
df = pl.read_excel("data.xlsx")

# Specific sheet
df = pl.read_excel("data.xlsx", sheet_name="Sheet1")
# Or by index
df = pl.read_excel("data.xlsx", sheet_id=0)

# With options
df = pl.read_excel(
    "data.xlsx",
    sheet_name="Sheet1",
    columns=["A", "B", "C"],  # Excel columns
    n_rows=100,
    skip_rows=5,
    has_header=True
)
```

### Writing Excel

```python
# Write to Excel
df.write_excel("output.xlsx")

# Multiple sheets
with pl.ExcelWriter("output.xlsx") as writer:
    df1.write_excel(writer, worksheet="Sheet1")
    df2.write_excel(writer, worksheet="Sheet2")
```

## Database connectivity

### Read from database

```python
import polars as pl

# Read entire table
df = pl.read_database("SELECT * FROM users", connection_uri="postgresql://...")

# Using connectorx for better performance
df = pl.read_database_uri(
    "SELECT * FROM users WHERE age > 25",
    uri="postgresql://user:pass@localhost/db"
)
```

### Write to database

```python
# Using SQLAlchemy
from sqlalchemy import create_engine

engine = create_engine("postgresql://user:pass@localhost/db")
df.write_database("table_name", connection=engine)

# With options
df.write_database(
    "table_name",
    connection=engine,
    if_exists="replace",  # or "append", "fail"
)
```

### Common database connectors

**PostgreSQL:**

```python
uri = "postgresql://username:password@localhost:5432/database"
df = pl.read_database_uri("SELECT * FROM table", uri=uri)
```

**MySQL:**

```python
uri = "mysql://username:password@localhost:3306/database"
df = pl.read_database_uri("SELECT * FROM table", uri=uri)
```

**SQLite:**

```python
uri = "sqlite:///path/to/database.db"
df = pl.read_database_uri("SELECT * FROM table", uri=uri)
```

## Cloud storage

### AWS S3

```python
# Read from S3
df = pl.read_parquet("s3://bucket/path/to/file.parquet")
lf = pl.scan_parquet("s3://bucket/path/*.parquet")

# Write to S3
df.write_parquet("s3://bucket/path/output.parquet")

# With credentials
import os
os.environ["AWS_ACCESS_KEY_ID"] = "your_key"
os.environ["AWS_SECRET_ACCESS_KEY"] = "your_secret"
os.environ["AWS_REGION"] = "us-west-2"

df = pl.read_parquet("s3://bucket/file.parquet")
```

### Azure Blob Storage

```python
# Read from Azure
df = pl.read_parquet("az://container/path/file.parquet")

# Write to Azure
df.write_parquet("az://container/path/output.parquet")

# With credentials
os.environ["AZURE_STORAGE_ACCOUNT_NAME"] = "account"
os.environ["AZURE_STORAGE_ACCOUNT_KEY"] = "key"
```

### Google Cloud Storage (GCS)

```python
# Read from GCS
df = pl.read_parquet("gs://bucket/path/file.parquet")

# Write to GCS
df.write_parquet("gs://bucket/path/output.parquet")

# With credentials
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "/path/to/credentials.json"
```

## Google BigQuery

```python
# Read from BigQuery
df = pl.read_database(
    "SELECT * FROM project.dataset.table",
    connection_uri="bigquery://project"
)

# Or using Google Cloud SDK
from google.cloud import bigquery
client = bigquery.Client()

query = "SELECT * FROM project.dataset.table WHERE date > '2023-01-01'"
df = pl.from_pandas(client.query(query).to_dataframe())
```

## Apache Arrow

### IPC/Feather format

**Read:**

```python
df = pl.read_ipc("data.arrow")
lf = pl.scan_ipc("data.arrow")
```

**Write:**

```python
df.write_ipc("output.arrow")

# Compressed
df.write_ipc("output.arrow", compression="zstd")
```

### Arrow streaming

```python
# Write streaming format
df.write_ipc("output.arrows", compression="zstd")

# Read streaming
df = pl.read_ipc("output.arrows")
```

### From/To Arrow

```python
import pyarrow as pa

# From Arrow Table
arrow_table = pa.table({"col": [1, 2, 3]})
df = pl.from_arrow(arrow_table)

# To Arrow Table
arrow_table = df.to_arrow()
```

## In-memory formats

### Python dictionaries

```python
# From dict
df = pl.DataFrame({
    "col1": [1, 2, 3],
    "col2": ["a", "b", "c"]
})

# To dict
data_dict = df.to_dict()  # Column-oriented
data_dict = df.to_dict(as_series=False)  # Lists instead of Series
```

### NumPy arrays

```python
import numpy as np

# From NumPy
arr = np.array([[1, 2], [3, 4], [5, 6]])
df = pl.DataFrame(arr, schema=["col1", "col2"])

# To NumPy
arr = df.to_numpy()
```

### Pandas DataFrames

```python
import pandas as pd

# From Pandas
pd_df = pd.DataFrame({"col": [1, 2, 3]})
pl_df = pl.from_pandas(pd_df)

# To Pandas
pd_df = pl_df.to_pandas()

# Zero-copy when possible
pl_df = pl.from_arrow(pd_df)
```

### Lists of rows

```python
# From list of dicts
data = [
    {"name": "Alice", "age": 25},
    {"name": "Bob", "age": 30}
]
df = pl.DataFrame(data)

# To list of dicts
rows = df.to_dicts()

# From list of tuples
data = [("Alice", 25), ("Bob", 30)]
df = pl.DataFrame(data, schema=["name", "age"])
```

## Streaming large files

For datasets larger than memory, use lazy mode with streaming:

```python
# Streaming mode
lf = pl.scan_csv("very_large.csv")
result = lf.filter(pl.col("value") > 100).collect(streaming=True)

# Streaming with multiple files
lf = pl.scan_parquet("data/*.parquet")
result = lf.group_by("category").agg(pl.col("value").sum()).collect(streaming=True)
```

## Best practices

### Format selection

**Use Parquet when:**

- Need compression (up to 10x smaller than CSV)
- Want fast reads/writes
- Need to preserve data types
- Working with large datasets
- Need predicate pushdown

**Use CSV when:**

- Need human-readable format
- Interfacing with legacy systems
- Data is small
- Need universal compatibility

**Use JSON when:**

- Working with nested/hierarchical data
- Need web API compatibility
- Data has flexible schema

**Use Arrow IPC when:**

- Need zero-copy data sharing
- Fastest serialization required
- Working between Arrow-compatible systems

### Reading large files

```python
# 1. Always use lazy mode
lf = pl.scan_csv("large.csv")  # NOT read_csv

# 2. Filter and select early (pushdown optimization)
result = (
    lf
    .select("col1", "col2", "col3")  # Only needed columns
    .filter(pl.col("date") > "2023-01-01")  # Filter early
    .collect()
)

# 3. Use streaming for very large data
result = lf.filter(...).select(...).collect(streaming=True)

# 4. Read only needed rows during development
df = pl.read_csv("large.csv", n_rows=10000)  # Sample for testing
```

### Writing large files

```python
# 1. Use Parquet with compression
df.write_parquet("output.parquet", compression="zstd")

# 2. Use partitioning for very large datasets
df.write_parquet("output", partition_by=["year", "month"])

# 3. Write streaming
lf = pl.scan_csv("input.csv")
lf.sink_parquet("output.parquet")  # Streaming write
```

### Performance tips

```python
# 1. Specify dtypes when reading CSV
df = pl.read_csv(
    "data.csv",
    dtypes={"id": pl.Int64, "name": pl.Utf8}  # Avoids inference
)

# 2. Use appropriate compression
df.write_parquet("output.parquet", compression="snappy")  # Fast
df.write_parquet("output.parquet", compression="zstd")    # Better compression

# 3. Parallel reading
df = pl.read_csv("data.csv", parallel="auto")

# 4. Read multiple files in parallel
lf = pl.scan_parquet("data/*.parquet")  # Automatic parallel read
```

## Error handling

```python
try:
    df = pl.read_csv("data.csv")
except pl.exceptions.ComputeError as e:
    print(f"Error reading CSV: {e}")

# Ignore errors during parsing
df = pl.read_csv("messy.csv", ignore_errors=True)

# Handle missing files
from pathlib import Path
if Path("data.csv").exists():
    df = pl.read_csv("data.csv")
else:
    print("File not found")
```

## Schema management

```python
# Infer schema from sample
schema = pl.read_csv("data.csv", n_rows=1000).schema

# Use inferred schema for full read
df = pl.read_csv("data.csv", dtypes=schema)

# Define schema explicitly
schema = {
    "id": pl.Int64,
    "name": pl.Utf8,
    "date": pl.Date,
    "value": pl.Float64
}
df = pl.read_csv("data.csv", dtypes=schema)
```
