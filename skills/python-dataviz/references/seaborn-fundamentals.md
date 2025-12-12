---
name: seaborn-fundamentals
title: Seaborn fundamentals
description: >-
  Core seaborn concepts including design philosophy, data structures, function
  categories, and integration with matplotlib. Load when working with statistical
  visualizations or dataset-oriented plotting.
principles:
  - Work with DataFrames and named variables, not raw arrays
  - Use semantic mappings to encode additional dimensions
  - Leverage automatic statistical estimation and aggregation
  - Combine seaborn for plotting with matplotlib for customization
best_practices:
  - "**Data format**: Use tidy/long-form data with meaningful column names"
  - "**Figure vs axes**: Choose figure-level for faceting, axes-level for integration"
  - "**Semantic mappings**: Use hue, size, style to encode additional variables"
  - "**Customization**: Use seaborn for main plot, matplotlib for fine-tuning"
checklist:
  - Data in tidy/long-form format
  - Meaningful column names (used as labels)
  - Appropriate function level (figure vs axes)
  - Error bars and aggregation understood
related:
  - matplotlib-fundamentals
  - seaborn-objects
  - plot-types
---

# Seaborn fundamentals

## Design philosophy

Seaborn follows these core principles:

1. **Dataset-oriented**: Work directly with DataFrames and named variables
2. **Semantic mapping**: Automatically translate data values into visual properties
3. **Statistical awareness**: Built-in aggregation, error estimation, confidence intervals
4. **Aesthetic defaults**: Publication-ready themes and color palettes
5. **Matplotlib integration**: Full compatibility with matplotlib customization

## Quick start

```python
import seaborn as sns
import matplotlib.pyplot as plt
import pandas as pd

# Load example dataset
df = sns.load_dataset('tips')

# Create visualization
sns.scatterplot(data=df, x='total_bill', y='tip', hue='day')
plt.show()
```

## Data structure requirements

### Long-form data (preferred)

Each variable is a column, each observation is a row:

```python
   subject  condition  measurement
0        1    control         10.5
1        1  treatment         12.3
2        2    control          9.8
3        2  treatment         13.1
```

**Advantages:**

- Works with all seaborn functions
- Easy to remap variables to visual properties
- Natural for DataFrame operations

### Wide-form data

Variables spread across columns:

```python
   control  treatment
0     10.5       12.3
1      9.8       13.1
```

**Use for:** Simple matrices, correlation heatmaps, quick plots.

**Converting wide to long:**

```python
df_long = df.melt(var_name='condition', value_name='measurement')
```

## Function levels

### Axes-level functions

Plot to a single matplotlib Axes object.

- Accept `ax=` parameter for precise placement
- Return Axes object
- Integrate into complex matplotlib figures

**Examples:** `scatterplot`, `histplot`, `boxplot`, `regplot`, `heatmap`

```python
fig, axes = plt.subplots(2, 2, figsize=(10, 10))
sns.scatterplot(data=df, x='x', y='y', ax=axes[0, 0])
sns.histplot(data=df, x='x', ax=axes[0, 1])
sns.boxplot(data=df, x='cat', y='y', ax=axes[1, 0])
sns.kdeplot(data=df, x='x', y='y', ax=axes[1, 1])
```

### Figure-level functions

Manage entire figure including all subplots.

- Built-in faceting via `col` and `row` parameters
- Return FacetGrid, JointGrid, or PairGrid objects
- Use `height` and `aspect` for sizing
- Cannot be placed in existing figure

**Examples:** `relplot`, `displot`, `catplot`, `lmplot`, `jointplot`, `pairplot`

```python
# Automatic faceting
sns.relplot(data=df, x='x', y='y', col='category', row='group',
            hue='type', height=3, aspect=1.2)
```

### When to use which

| Use case | Function level |
|----------|---------------|
| Faceted visualizations (small multiples) | Figure-level |
| Integration with matplotlib figures | Axes-level |
| Quick exploratory analysis | Figure-level |
| Custom multi-plot layouts | Axes-level |

## Plotting categories

### Relational plots

**Use for:** Relationships between continuous variables.

- `scatterplot()` - Individual observations as points
- `lineplot()` - Trends with automatic aggregation and CI
- `relplot()` - Figure-level interface

```python
sns.scatterplot(data=df, x='x', y='y', hue='category', size='value')
sns.lineplot(data=df, x='time', y='value', hue='group', errorbar='ci')
```

### Distribution plots

**Use for:** Understanding data spread and shape.

- `histplot()` - Histograms with flexible binning
- `kdeplot()` - Kernel density estimates
- `ecdfplot()` - Empirical cumulative distribution
- `rugplot()` - Individual observation marks
- `displot()` - Figure-level interface
- `jointplot()` - Bivariate with marginals
- `pairplot()` - Pairwise relationships

```python
sns.histplot(data=df, x='value', hue='group', stat='density', kde=True)
sns.kdeplot(data=df, x='x', y='y', fill=True, levels=10)
```

### Categorical plots

**Use for:** Comparisons across discrete categories.

**Scatterplots:**

- `stripplot()` - Points with jitter
- `swarmplot()` - Non-overlapping points

**Distribution:**

- `boxplot()` - Quartiles and outliers
- `violinplot()` - KDE + quartiles
- `boxenplot()` - Enhanced boxplot for large data

**Estimates:**

- `barplot()` - Mean with confidence intervals
- `pointplot()` - Point estimates with lines
- `countplot()` - Observation counts

**Figure-level:** `catplot()` (set `kind` parameter)

```python
sns.violinplot(data=df, x='day', y='value', hue='sex', split=True)
sns.barplot(data=df, x='category', y='value', errorbar=('ci', 95))
```

### Regression plots

**Use for:** Linear relationships and model assessment.

- `regplot()` - Axes-level regression
- `lmplot()` - Figure-level with faceting
- `residplot()` - Residual analysis

```python
sns.regplot(data=df, x='x', y='y', order=2, ci=95)
sns.lmplot(data=df, x='x', y='y', hue='group', col='condition')
```

### Matrix plots

**Use for:** Rectangular data, correlations.

- `heatmap()` - Color-encoded matrix
- `clustermap()` - Hierarchically-clustered heatmap

```python
corr = df.corr()
sns.heatmap(corr, annot=True, fmt='.2f', cmap='coolwarm', center=0)
```

## Semantic mappings

Map data variables to visual properties:

```python
sns.scatterplot(data=df, x='x', y='y',
                hue='category',      # Color
                size='importance',   # Point size
                style='type')        # Marker style
```

### Key parameters

- `hue` - Color encoding (categorical or continuous)
- `size` - Point/line size
- `style` - Marker or line style
- `col`, `row` - Facet into subplots (figure-level only)

### Control ordering

```python
sns.boxplot(data=df, x='day', y='value',
            order=['Mon', 'Tue', 'Wed', 'Thu', 'Fri'],
            hue_order=['A', 'B', 'C'])
```

## Statistical estimation

Many functions compute statistics automatically:

```python
# lineplot computes mean and 95% CI by default
sns.lineplot(data=df, x='time', y='value')

# Control error representation
sns.lineplot(data=df, x='time', y='value', errorbar='sd')  # Standard deviation
sns.lineplot(data=df, x='time', y='value', errorbar=('ci', 95))  # CI level
sns.lineplot(data=df, x='time', y='value', errorbar=None)  # No error bars

# barplot uses mean by default
sns.barplot(data=df, x='category', y='value', estimator='median')
```

### Error bar options

- `'ci'` or `('ci', level)` - Bootstrap confidence interval
- `'pi'` or `('pi', level)` - Percentile interval
- `'se'` or `('se', scale)` - Standard error
- `'sd'` - Standard deviation
- `None` - No error bars

## Multi-plot grids

### FacetGrid

Create subplots from categorical variables:

```python
g = sns.FacetGrid(df, col='time', row='sex', hue='smoker')
g.map(sns.scatterplot, 'total_bill', 'tip')
g.add_legend()
```

### PairGrid

Pairwise relationships:

```python
g = sns.PairGrid(df, hue='species')
g.map_upper(sns.scatterplot)
g.map_lower(sns.kdeplot)
g.map_diag(sns.histplot)
g.add_legend()
```

### JointGrid

Bivariate with marginals:

```python
g = sns.JointGrid(data=df, x='x', y='y')
g.plot_joint(sns.scatterplot)
g.plot_marginals(sns.histplot)
```

## Theming

### Set theme

```python
sns.set_theme(style='whitegrid', palette='pastel', font='sans-serif')
sns.set_theme()  # Reset to defaults
```

### Styles

- `'darkgrid'` - Gray background with white grid (default)
- `'whitegrid'` - White background with gray grid
- `'dark'` - Gray background, no grid
- `'white'` - White background, no grid
- `'ticks'` - White background with axis ticks

### Contexts

Scale elements for different use cases:

- `'paper'` - Smallest (default)
- `'notebook'` - Slightly larger
- `'talk'` - Presentation slides
- `'poster'` - Large format

```python
sns.set_context('talk', font_scale=1.2)
```

### Despine

Remove top and right spines:

```python
sns.despine(offset=10, trim=True)
```

## Integration with matplotlib

```python
# Create seaborn plot
ax = sns.scatterplot(data=df, x='x', y='y')

# Customize with matplotlib
ax.set(xlabel='Custom X Label', ylabel='Custom Y Label', title='Title')
ax.axhline(y=0, color='r', linestyle='--')
ax.legend(bbox_to_anchor=(1.05, 1))
plt.tight_layout()
```

## Saving figures

### Axes-level functions

```python
fig, ax = plt.subplots(figsize=(8, 6))
sns.scatterplot(data=df, x='x', y='y', ax=ax)
plt.savefig('figure.png', dpi=300, bbox_inches='tight')
```

### Figure-level functions

```python
g = sns.relplot(data=df, x='x', y='y', col='group')
g.savefig('figure.png', dpi=300, bbox_inches='tight')
g.savefig('figure.pdf')
```
