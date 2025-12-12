---
name: benchmarking
title: Benchmarking standard
description: Performance benchmarking practices using pytest-benchmark for measuring, comparing, and detecting performance regressions
commands:
  just benchmark: Run all benchmarks
  just benchmark-save <name>: Save benchmark results with variance-resistant settings
  just benchmark-compare <name>: Compare current results against saved baseline
  just benchmark-check <name>: Check for regressions (>15% median)
  just benchmark-ci: Run benchmarks with CI-optimized settings
  uv run pytest tests/benchmarks/ -v: Run benchmarks with verbose output
  uv run pytest tests/benchmarks/ --benchmark-autosave: Save baseline for future comparison
  uv run pytest tests/benchmarks/ --benchmark-compare: Run with comparison to saved baseline
  uv run pytest tests/benchmarks/ --benchmark-json=results.json: Generate JSON output
principles:
  - '**NEVER** optimize without benchmarking first'
  - Establish baselines before making changes
  - Verify improvements with data
  - Test realistic scenarios
  - Use appropriate data sizes
  - Control for external factors
  - Verify correctness in benchmarks
best_practices:
  - '**Isolate benchmarks**: Run in dedicated environment'
  - '**Multiple rounds**: Use enough iterations for statistical significance (min 20)'
  - '**Warmup**: Include warmup rounds to avoid cold-start effects'
  - '**Verify correctness**: Always assert results are correct'
  - '**Control variables**: Minimize external factors'
  - '**Use median**: Prefer median over mean for regression thresholds'
checklist:
  - Benchmark tests realistic scenarios
  - Correctness verified in each benchmark
  - Baseline saved for comparison
  - Results are statistically significant
  - No external factors affecting results
references:
  https://pytest-benchmark.readthedocs.io/en/latest/: pytest-benchmark documentation
---

## Writing benchmarks

### Basic benchmark

```python
def test_benchmark_processing(benchmark):
    """Benchmark data processing."""
    data = setup_test_data(size=1000)

    result = benchmark(process_data, data)

    # **Always** verify correctness
    assert result is not None
    assert len(result) == 1000
```

### Benchmark with setup

```python
def test_benchmark_with_setup(benchmark):
    """Benchmark with separate setup phase."""

    def setup():
        return setup_complex_data()

    def teardown(data):
        cleanup(data)

    result = benchmark.pedantic(
        process_data,
        setup=setup,
        teardown=teardown,
        rounds=100,
        warmup_rounds=10,
    )

    assert result.success
```

### Parameterized benchmarks

```python
import pytest


@pytest.mark.parametrize("size", [100, 1000, 10000])
def test_benchmark_scaling(benchmark, size):
    """Benchmark processing at different scales."""
    data = generate_data(size)

    result = benchmark(process_data, data)

    assert len(result) == size
```

## Benchmark organization

```text
tests/
└── benchmarks/
    ├── microbenchmarks/
    │   ├── test_processing_benchmark.py
    │   └── test_validation_benchmark.py
    ├── integration/
    │   └── test_end_to_end_benchmark.py
    └── memory/
        └── test_memory_usage.py
```

## Naming conventions

```python
# Microbenchmarks
def test_benchmark_process_single_item(benchmark): ...


def test_benchmark_process_batch(benchmark): ...


# Memory benchmarks
def test_memory_peak_usage(benchmark): ...
```

## Interpreting results

### Key metrics

- **Mean**: Average execution time
- **Stddev**: Variation in times
- **Min/Max**: Extremes
- **Rounds**: Number of iterations
- **OPS**: Operations per second

### Warning signs

- High stddev indicates inconsistent performance
- Large gap between min and max
- Unexpected scaling behavior

## Regression detection

```bash
# Save baseline after known-good state
just benchmark-save baseline

# After changes, compare and fail on regression
just benchmark-check baseline
```

### Threshold selection

- **Local/self-hosted**: `median:10%` - controlled environment
- **CI (shared runners)**: `median:15%` - accounts for variance
- **Why median**: Robust to outliers from noisy neighbors

## CI variance handling

GitHub Actions runners have significant variance (10-30%) due to shared infrastructure. The CI configuration mitigates this:

| Setting                               | Value     | Why                                            |
| ------------------------------------- | --------- | ---------------------------------------------- |
| `--benchmark-warmup=on`               | Enabled   | Primes CPU caches; reduces cold-start variance |
| `--benchmark-warmup-iterations=1000`  | 1000      | Sufficient iterations to stabilize             |
| `--benchmark-min-rounds=20`           | 20        | More samples improve statistical significance  |
| `--benchmark-max-time=2.0`            | 2 seconds | Allow more time for stable measurements        |
| `--benchmark-disable-gc`              | Enabled   | Removes garbage collection jitter              |
| `--benchmark-timer=time.process_time` | CPU time  | Excludes I/O wait (CI only)                    |

Use `just benchmark-ci` for CI-optimized settings.
