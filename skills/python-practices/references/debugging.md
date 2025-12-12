---
name: debugging
title: Debugging standard
description: Profiling with py-spy, memory profiling with memray, debugger usage, logging patterns. Load when debugging issues.
commands:
  uv run pytest --pdb: Run tests and drop into debugger on failure
  uv run pytest -x --pdb: Stop on first failure and debug
  uv run pytest -s: Run tests showing print output
  py-spy top --pid <PID>: Profile running Python process
  py-spy record -o profile.svg -- python script.py: Record CPU profile
  memray run script.py: Record memory allocations
  memray flamegraph <binfile>: Generate memory flamegraph
principles:
  - Use interactive debugging with `breakpoint()` for step-through analysis
  - Profile before optimizing - measure, don't guess
  - Use appropriate profiling tools for CPU (py-spy) vs memory (memray) issues
  - Apply structured logging for production observability
  - Use appropriate log levels based on severity and context
best_practices:
  - '**Use breakpoint()**: Prefer breakpoint() over import pdb; pdb.set_trace() for Python 3.7+'
  - '**Use py-spy for CPU profiling**: Non-invasive profiling of running processes'
  - '**Use memray for memory profiling**: Detailed memory allocation tracking'
  - '**Structured logging**: Implement with context (e.g., structlog)'
  - '**Assert invariants**: Use assert statements to validate during development'
  - '**Debug failing tests**: Use pytest --pdb for interactive debugging'
  - '**Print debugging**: Use for quick investigations, **ALWAYS** remove before committing'
  - "**Profile before optimizing**: Use py-spy to measure, don't guess"
checklist:
  - Use breakpoint() for interactive debugging
  - Use py-spy for CPU profiling
  - Use memray for memory profiling
  - Use structured logging (structlog)
  - pytest --pdb for test debugging
references:
  https://docs.python.org/3/library/pdb.html: pdb debugger documentation
  https://docs.python.org/3/library/logging.html: logging module documentation
---

## Python debugger (pdb)

### Setting breakpoints

**Always** use `breakpoint()` for Python 3.7+.

```python
# In code
breakpoint()  # Python 3.7+

# Or explicitly (legacy)
import pdb

pdb.set_trace()
```

### Common pdb commands

| Command   | Description                 |
| --------- | --------------------------- |
| `n`       | Next line (step over)       |
| `s`       | Step into function          |
| `c`       | Continue to next breakpoint |
| `p expr`  | Print expression            |
| `pp expr` | Pretty print                |
| `l`       | List source code            |
| `w`       | Print stack trace           |
| `q`       | Quit debugger               |

## CPU profiling with py-spy

```bash
# Profile running process
py-spy top --pid <PID>

# Record profile to file
py-spy record -o profile.svg -- python script.py

# Sample rate (default 100)
py-spy record -r 200 -o profile.svg -- python script.py
```

## Memory profiling with memray

```bash
# Record memory allocations
memray run script.py

# Generate flamegraph
memray flamegraph memray-script.py.<pid>.bin

# Show summary
memray summary memray-script.py.<pid>.bin

# Track specific allocations
memray run --trace-python-allocators script.py
```

## Logging

### Setup

```python
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)
```

### Structured logging with structlog

```python
import structlog

logger = structlog.get_logger()


def process_order(order_id: str) -> None:
    logger.info("processing_order", order_id=order_id)
    try:
        # process
        logger.info("order_processed", order_id=order_id)
    except Exception as e:
        logger.error("order_failed", order_id=order_id, error=str(e))
        raise
```

### Log levels

| Level    | Use for                           |
| -------- | --------------------------------- |
| DEBUG    | Detailed diagnostic info          |
| INFO     | General operational events        |
| WARNING  | Unexpected but handled situations |
| ERROR    | Errors that need attention        |
| CRITICAL | System failures                   |

## Debugging tests

```bash
# Drop into debugger on failure
pytest --pdb

# Drop into debugger on first failure
pytest -x --pdb

# Verbose output
pytest -v

# Show print statements
pytest -s

# Show locals in traceback
pytest --tb=long
```

## Common debugging techniques

### Print debugging (quick)

**ALWAYS** remove print debugging statements before committing.

```python
def process(data: list[int]) -> int:
    print(f"DEBUG: data = {data}")
    result = sum(data)
    print(f"DEBUG: result = {result}")
    return result
```

### Using assert for invariants

```python
def divide(a: int, b: int) -> float:
    assert b != 0, "Divisor cannot be zero"
    return a / b
```

### Inspecting objects

```python
# Show object attributes
print(dir(obj))

# Show object dict
print(vars(obj))

# Type information
print(type(obj))
print(obj.__class__.__mro__)
```

## Performance debugging

**ALWAYS** profile before optimizing. Measure, don't guess.

```bash
# Time a command
time python script.py

# Profile with cProfile
python -m cProfile -s cumulative script.py

# Line profiler (needs line_profiler package)
kernprof -l -v script.py
```
