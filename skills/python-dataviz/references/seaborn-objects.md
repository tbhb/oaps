---
name: seaborn-objects
title: Seaborn objects interface
description: >-
  Modern declarative API for building visualizations through composition using
  seaborn.objects. Load when building complex layered plots or wanting ggplot2-
  style syntax.
principles:
  - Separate what to show (data/mappings) from how to show it (marks/stats)
  - Build plots by composing marks, stats, and moves
  - Method chaining creates new Plot objects
best_practices:
  - "**Layering**: Use multiple .add() calls to overlay marks"
  - "**Transforms**: Stat applies first, then Move"
  - "**Saving**: Use .save() not plt.savefig()"
checklist:
  - Using seaborn 0.12+ for objects interface
  - Proper method chaining
  - Correct mark/stat/move composition
related:
  - seaborn-fundamentals
  - plot-types
---

# Seaborn objects interface

The `seaborn.objects` interface provides a modern, declarative API for building visualizations through composition, similar to ggplot2.

## Core concept

Separate **what to show** (data and mappings) from **how to show it** (marks, stats, moves):

1. Create a `Plot` with data and aesthetic mappings
2. Add layers with `.add()` combining marks and transformations
3. Customize with `.scale()`, `.label()`, `.limit()`, `.theme()`
4. Render with `.show()` or `.save()`

## Basic usage

```python
from seaborn import objects as so
import pandas as pd

# Create plot with mappings
p = so.Plot(data=df, x='x_var', y='y_var')

# Add mark
p = p.add(so.Dot())

# Display
p.show()
```

## Plot class

### Initialization

```python
so.Plot(data=None, x=None, y=None, color=None, alpha=None,
        marker=None, pointsize=None, stroke=None, text=None)
```

### Key methods

#### add()

Add a layer with mark and optional transformations.

```python
# Simple mark
p.add(so.Dot())

# Mark with stat
p.add(so.Line(), so.PolyFit(order=2))

# Mark with stat and move
p.add(so.Bar(), so.Agg(), so.Dodge())

# Layer-specific mappings
p.add(so.Dot(), color='category')
```

#### facet()

Create subplots from categorical variables.

```python
p.facet(col='time', row='sex')
p.facet(col='category', wrap=3)
```

#### pair()

Create pairwise subplots.

```python
p = so.Plot(df).pair(x=['a', 'b', 'c'])
p.add(so.Dot())
```

#### scale()

Customize data-to-visual mappings.

```python
p.scale(
    x=so.Continuous().tick(every=5),
    y=so.Continuous(trans='log'),
    color=so.Nominal(['#1f77b4', '#ff7f0e']),
    pointsize=(5, 20)
)
```

#### label()

Set axis labels and titles.

```python
p.label(x='X Label', y='Y Label', title='Title', color='Category')
```

#### limit()

Set axis limits.

```python
p.limit(x=(0, 100), y=(0, 50))
```

#### theme()

Apply matplotlib style settings.

```python
p.theme({**sns.axes_style('whitegrid')})
```

#### layout()

Configure subplot layout.

```python
p.layout(size=(10, 6), engine='constrained')
```

#### share()

Control axis sharing across facets.

```python
p.share(x=True, y=False)
```

#### on()

Plot on existing matplotlib axes.

```python
fig, ax = plt.subplots()
so.Plot(df, x='x', y='y').add(so.Dot()).on(ax)
```

#### save()

Save to file.

```python
p.save('plot.png', dpi=300, bbox_inches='tight')
```

## Mark objects

### Dot

Points for individual observations.

```python
so.Dot(color='blue', pointsize=10, alpha=0.5)
```

**Properties:** `color`, `alpha`, `marker`, `pointsize`, `edgecolor`, `edgewidth`

### Line

Lines connecting observations.

```python
so.Line(linewidth=2, linestyle='--')
```

**Properties:** `color`, `alpha`, `linewidth`, `linestyle`, `marker`

### Path

Like Line but connects in data order (not sorted by x).

```python
so.Path()  # For trajectories
```

### Bar

Rectangular bars.

```python
so.Bar(color='steelblue', width=0.8)
```

**Properties:** `color`, `alpha`, `edgecolor`, `edgewidth`, `width`

### Area

Filled area to baseline.

```python
so.Area(alpha=0.3)
```

### Band

Filled band between two lines.

```python
so.Band(alpha=0.2)  # Use with Est() stat
```

### Range

Line with endpoint markers.

```python
so.Range()  # Use with Est() stat
```

### Text

Text labels at data points.

```python
so.Text(fontsize=10, halign='center')
```

Requires `text` mapping.

## Stat objects

Stats transform data before rendering.

### Agg

Aggregate observations by group.

```python
so.Agg(func='mean')  # 'median', 'sum', 'min', 'max', 'count'
```

### Est

Estimate with error intervals.

```python
so.Est(func='mean', errorbar=('ci', 95))
# errorbar: 'sd', 'se', ('ci', level), ('pi', level)
```

### Hist

Bin and count observations.

```python
so.Hist(stat='count', bins='auto')
# stat: 'count', 'density', 'probability', 'percent'
```

### KDE

Kernel density estimate.

```python
so.KDE(bw_adjust=1.0, gridsize=200)
```

### Count

Count observations per group.

```python
so.Count()
```

### PolyFit

Polynomial regression fit.

```python
so.PolyFit(order=2)  # 1=linear, 2=quadratic
```

## Move objects

Moves adjust positions to resolve overlaps.

### Dodge

Shift positions side-by-side.

```python
so.Dodge(gap=0.1)
```

### Stack

Stack marks vertically.

```python
so.Stack()
```

### Jitter

Add random noise.

```python
so.Jitter(width=0.2)
```

### Shift

Shift by constant amount.

```python
so.Shift(x=0.1)
```

## Scale objects

### Continuous

For numeric data.

```python
so.Continuous(trans='log').tick(every=10).label(like='{x:.1f}')
```

### Nominal

For categorical data.

```python
so.Nominal(order=['A', 'B', 'C'])
so.Nominal(['#1f77b4', '#ff7f0e'])  # Explicit colors
```

### Temporal

For datetime data.

```python
so.Temporal().tick(every=('month', 1)).label(concise=True)
```

## Complete examples

### Layered scatter with regression

```python
(
    so.Plot(df, x='total_bill', y='tip', color='time')
    .add(so.Dot(), alpha=0.5)
    .add(so.Line(), so.PolyFit(order=2))
    .label(x='Total Bill ($)', y='Tip ($)')
)
```

### Grouped bar chart with error bars

```python
(
    so.Plot(df, x='category', y='value', color='group')
    .add(so.Bar(), so.Agg('mean'), so.Dodge())
    .add(so.Range(), so.Est(errorbar='se'), so.Dodge())
)
```

### Faceted distribution

```python
(
    so.Plot(df, x='measurement', color='treatment')
    .facet(col='timepoint', wrap=3)
    .add(so.Area(alpha=0.5), so.KDE())
    .share(x=True, y=False)
)
```

### Complex multi-layer

```python
(
    so.Plot(df, x='date', y='value')
    .add(so.Dot(color='gray', pointsize=3), alpha=0.3)
    .add(so.Line(color='blue', linewidth=2), so.Agg('mean'))
    .add(so.Band(color='blue', alpha=0.2), so.Est())
    .facet(col='sensor', row='location')
    .scale(x=so.Temporal().label(concise=True))
    .layout(size=(12, 8))
)
```

## Migration from function interface

### Scatter plot

```python
# Function interface
sns.scatterplot(data=df, x='x', y='y', hue='category', size='value')

# Objects interface
so.Plot(df, x='x', y='y', color='category', pointsize='value').add(so.Dot())
```

### Line plot with CI

```python
# Function interface
sns.lineplot(data=df, x='time', y='value', hue='group', errorbar='ci')

# Objects interface
(
    so.Plot(df, x='time', y='value', color='group')
    .add(so.Line(), so.Est())
)
```

### Bar plot

```python
# Function interface
sns.barplot(data=df, x='category', y='value', hue='group', errorbar='ci')

# Objects interface
(
    so.Plot(df, x='category', y='value', color='group')
    .add(so.Bar(), so.Agg(), so.Dodge())
    .add(so.Range(), so.Est(), so.Dodge())
)
```

## Tips

1. **Method chaining**: Each method returns a new Plot object
2. **Layer composition**: Multiple `.add()` calls overlay marks
3. **Transform order**: In `.add(mark, stat, move)`, stat applies first
4. **Variable priority**: Layer mappings override Plot mappings
5. **Scale shortcuts**: Use tuples for ranges: `pointsize=(5, 20)`
6. **Jupyter rendering**: Plots auto-render when returned
7. **Saving**: Use `.save()` rather than `plt.savefig()`
8. **Matplotlib access**: Use `.on(ax)` to integrate
