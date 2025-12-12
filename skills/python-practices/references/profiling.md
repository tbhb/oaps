---
name: profiling
title: Profiling standard
description: Performance profiling best practices using py-spy and other Python profiling tools
commands:
  uv run py-spy record -o profile.svg -- python script.py: Create flame graph SVG from CPU profiling
  uv run py-spy record -o profile.json --format speedscope -- python script.py: Create speedscope JSON for interactive visualization
  uv run py-spy top -- python script.py: Live top-like view of CPU usage
  uv run py-spy record --rate 250 -o profile.svg -- python script.py: Increase sampling rate for more detail
  uv run py-spy record --native -o profile.svg -- python script.py: Include native frames in profiling
  uv run python -m cProfile -o profile.prof script.py: Deterministic profiling with cProfile
  uv run python -m cProfile -s cumulative script.py: Profile and sort by cumulative time
principles:
  - '**Never** guess where bottlenecks are'
  - '**Always** measure before and after changes'
  - Focus optimization on actual hot paths
best_practices:
  - '**Use py-spy**: Use py-spy for sampling-based profiling'
  - '**Use cProfile**: Use cProfile for deterministic profiling'
  - '**Use tracemalloc**: Use tracemalloc for memory profiling'
  - '**Establish baseline**: Always establish baseline profile before optimizing'
  - '**Identify hot paths**: Identify hot paths with data'
  - '**Make targeted changes**: Make targeted changes at actual bottlenecks'
  - '**Verify improvements**: Verify improvements with profiling after changes'
checklist:
  - Baseline profile established
  - Hot paths identified with data
  - Changes targeted at actual bottlenecks
  - Improvements verified with profiling
  - No functionality broken
references:
  https://github.com/benfred/py-spy: py-spy sampling profiler
  https://bloomberg.github.io/memray/: memray memory profiler
---

## CPU profiling with py-spy

### Record profile to file

```bash
# Create flame graph SVG
uv run py-spy record -o profile.svg -- python script.py

# Create speedscope JSON
uv run py-spy record -o profile.json --format speedscope -- python script.py
```

### Live process profiling

```bash
# Top-like view
uv run py-spy top -- python script.py

# Attach to running process
uv run py-spy top --pid 12345
```

### Record options

```bash
# Increase sampling rate
uv run py-spy record --rate 250 -o profile.svg -- python script.py

# Include native frames
uv run py-spy record --native -o profile.svg -- python script.py

# Subprocesses too
uv run py-spy record --subprocesses -o profile.svg -- python script.py
```

## CPU profiling with cProfile

### Basic profiling

```bash
# Run with profiler
uv run python -m cProfile -o profile.prof script.py

# Sort by cumulative time
uv run python -m cProfile -s cumulative script.py
```

### Analyze results

```python
import pstats

# Load and analyze
p = pstats.Stats("profile.prof")
p.sort_stats("cumulative")
p.print_stats(20)  # Top 20 functions

# Filter by function name
p.print_stats("process")
```

### Profile specific code

```python
import cProfile
import pstats


def profile_function(func):
    """Decorator to profile a function."""

    def wrapper(*args, **kwargs):
        profiler = cProfile.Profile()
        result = profiler.runcall(func, *args, **kwargs)

        stats = pstats.Stats(profiler)
        stats.sort_stats("cumulative")
        stats.print_stats(10)

        return result

    return wrapper
```

## Memory profiling

### With tracemalloc

```python
import tracemalloc

# Start tracing
tracemalloc.start()

# Run code to profile
result = process_large_data()

# Get snapshot
snapshot = tracemalloc.take_snapshot()

# Print top memory consumers
top_stats = snapshot.statistics("lineno")
for stat in top_stats[:10]:
    print(stat)
```

### Comparing snapshots

```python
import tracemalloc

tracemalloc.start()

# First snapshot
process_step1()
snapshot1 = tracemalloc.take_snapshot()

# Second snapshot
process_step2()
snapshot2 = tracemalloc.take_snapshot()

# Compare
top_stats = snapshot2.compare_to(snapshot1, "lineno")
for stat in top_stats[:10]:
    print(stat)
```

## Flame graph analysis

### Reading flame graphs

- **Width**: Time spent in function (wider = more time)
- **Height**: Call stack depth (taller = deeper calls)
- **Colors**: Usually arbitrary, can indicate different categories

### What to look for

1. **Wide bars at top**: Direct time consumers
1. **Wide bars lower**: Functions called frequently
1. **Many thin bars**: Possibly inefficient iteration
1. **Deep stacks**: Potential for stack optimization

## Optimization workflow

1. **Establish baseline**: Profile current state
1. **Identify hot path**: Find actual bottleneck
1. **Hypothesize**: Theory for improvement
1. **Implement**: Make targeted change
1. **Verify**: Profile again to confirm improvement
1. **Repeat**: If needed, go back to step 2

## Common optimizations

### Algorithm improvements

```python
# O(n^2) - linear search in loop
for item in items:
    if item in other_items:  # O(n) lookup each time
        ...

# O(n) - use set for O(1) lookup
other_set = set(other_items)
for item in items:
    if item in other_set:  # O(1) lookup
        ...
```

### Caching

```python
from functools import lru_cache


@lru_cache(maxsize=128)
def expensive_computation(key: str) -> Result:
    """Cache expensive results."""
    return compute(key)
```

### Generator expressions

```python
# Memory-heavy: creates full list
data = [transform(x) for x in large_input]
result = sum(data)

# Memory-efficient: processes one at a time
data = (transform(x) for x in large_input)
result = sum(data)
```
