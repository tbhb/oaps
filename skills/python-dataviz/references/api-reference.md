---
name: api-reference
title: API quick reference
description: >-
  Quick reference for commonly used matplotlib and seaborn functions and their
  key parameters. Load when needing a quick lookup of function signatures or
  common parameter values.
principles:
  - Use this as a quick lookup, not comprehensive documentation
  - Refer to official docs for complete parameter lists
best_practices:
  - "**Check parameter names**: seaborn uses 'hue' not 'color' for grouping"
  - "**Know the defaults**: understand what functions compute automatically"
checklist:
  - Correct function for the task
  - Key parameters specified
related:
  - matplotlib-fundamentals
  - seaborn-fundamentals
  - plot-types
---

# API quick reference

## Matplotlib core

### Figure and axes creation

```python
fig, ax = plt.subplots(figsize=(10, 6))
fig, axes = plt.subplots(nrows, ncols, figsize=(w, h))
fig, axes = plt.subplots(2, 2, sharex=True, sharey=True)
fig, ax = plt.subplots(constrained_layout=True)
```

### Common plot methods

| Method | Key parameters |
|--------|---------------|
| `ax.plot(x, y)` | `linewidth`, `linestyle`, `marker`, `color`, `label` |
| `ax.scatter(x, y)` | `s` (size), `c` (color), `marker`, `alpha`, `cmap` |
| `ax.bar(x, height)` | `width`, `color`, `edgecolor`, `label` |
| `ax.barh(y, width)` | `height`, `color`, `edgecolor` |
| `ax.hist(data)` | `bins`, `density`, `alpha`, `edgecolor` |
| `ax.boxplot(data)` | `labels`, `showmeans`, `notch` |
| `ax.imshow(data)` | `cmap`, `aspect`, `vmin`, `vmax`, `interpolation` |
| `ax.contour(X, Y, Z)` | `levels`, `cmap`, `colors` |
| `ax.contourf(X, Y, Z)` | `levels`, `cmap`, `alpha` |
| `ax.errorbar(x, y, yerr)` | `fmt`, `capsize`, `capthick` |
| `ax.fill_between(x, y1, y2)` | `alpha`, `color`, `label` |

### Customization methods

```python
# Labels and title
ax.set_xlabel('label', fontsize=12)
ax.set_ylabel('label', fontsize=12)
ax.set_title('title', fontsize=14)

# Limits and scale
ax.set_xlim(left, right)
ax.set_ylim(bottom, top)
ax.set_xscale('log')  # 'linear', 'log', 'symlog'

# Ticks
ax.set_xticks(positions)
ax.set_xticklabels(labels, rotation=45, ha='right')
ax.tick_params(axis='both', labelsize=10)

# Legend
ax.legend(loc='best')
ax.legend(bbox_to_anchor=(1.05, 1), loc='upper left')

# Grid
ax.grid(True, alpha=0.3, linestyle='--')

# Spines
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)
```

### Saving

```python
plt.savefig('file.png', dpi=300, bbox_inches='tight')
plt.savefig('file.pdf', bbox_inches='tight')
plt.savefig('file.svg', bbox_inches='tight')
```

### Line styles

| Style | String |
|-------|--------|
| Solid | `'-'` or `'solid'` |
| Dashed | `'--'` or `'dashed'` |
| Dash-dot | `'-.'` or `'dashdot'` |
| Dotted | `':'` or `'dotted'` |

### Markers

| Marker | String |
|--------|--------|
| Point | `'.'` |
| Circle | `'o'` |
| Square | `'s'` |
| Triangle | `'^'`, `'v'`, `'<'`, `'>'` |
| Star | `'*'` |
| Plus | `'+'` |
| X | `'x'` |
| Diamond | `'D'`, `'d'` |

## Seaborn relational

### scatterplot()

```python
sns.scatterplot(data=df, x='x', y='y',
    hue='category',     # Color grouping
    size='value',       # Size encoding
    style='type',       # Marker style
    palette='Set2',     # Color palette
    sizes=(20, 200),    # Size range
    alpha=0.7,
    ax=ax
)
```

### lineplot()

```python
sns.lineplot(data=df, x='x', y='y',
    hue='category',
    style='type',
    markers=True,
    dashes=False,
    errorbar='ci',      # 'sd', 'se', ('ci', 95), None
    estimator='mean',   # Aggregation function
    ax=ax
)
```

### relplot() (figure-level)

```python
sns.relplot(data=df, x='x', y='y',
    hue='category',
    col='group',        # Column faceting
    row='time',         # Row faceting
    col_wrap=3,         # Wrap columns
    kind='scatter',     # or 'line'
    height=3,
    aspect=1.5
)
```

## Seaborn distribution

### histplot()

```python
sns.histplot(data=df, x='value',
    hue='group',
    bins=30,            # Number or method
    stat='density',     # 'count', 'frequency', 'probability', 'percent'
    kde=True,           # Overlay KDE
    multiple='layer',   # 'stack', 'dodge', 'fill'
    element='bars',     # 'step', 'poly'
    ax=ax
)
```

### kdeplot()

```python
sns.kdeplot(data=df, x='x', y='y',  # y optional
    hue='group',
    fill=True,
    levels=10,          # Contour levels (bivariate)
    bw_adjust=1.0,      # Bandwidth multiplier
    common_norm=False,
    ax=ax
)
```

### displot() (figure-level)

```python
sns.displot(data=df, x='value',
    hue='group',
    col='category',
    kind='kde',         # 'hist', 'kde', 'ecdf'
    rug=True,
    height=3,
    aspect=1.5
)
```

### jointplot()

```python
sns.jointplot(data=df, x='x', y='y',
    hue='group',
    kind='scatter',     # 'kde', 'hist', 'hex', 'reg'
    height=6,
    ratio=4,            # Joint to marginal ratio
    marginal_kws={'bins': 30}
)
```

### pairplot()

```python
sns.pairplot(data=df,
    hue='species',
    vars=['a', 'b', 'c'],  # Subset of columns
    diag_kind='kde',       # 'hist', 'kde', None
    corner=True,           # Only lower triangle
    height=2.5
)
```

## Seaborn categorical

### boxplot()

```python
sns.boxplot(data=df, x='category', y='value',
    hue='group',
    order=['A', 'B', 'C'],
    palette='Set2',
    showmeans=True,
    notch=True,
    ax=ax
)
```

### violinplot()

```python
sns.violinplot(data=df, x='category', y='value',
    hue='group',
    split=True,         # Split violins by hue
    inner='quartile',   # 'box', 'quartile', 'point', 'stick', None
    ax=ax
)
```

### barplot()

```python
sns.barplot(data=df, x='category', y='value',
    hue='group',
    estimator='mean',   # Aggregation function
    errorbar='ci',      # 'sd', 'se', ('ci', 95)
    capsize=0.1,
    ax=ax
)
```

### stripplot() / swarmplot()

```python
sns.stripplot(data=df, x='category', y='value',
    hue='group',
    dodge=True,
    jitter=0.2,
    alpha=0.5,
    ax=ax
)

sns.swarmplot(data=df, x='category', y='value',
    hue='group',
    dodge=True,
    size=4,
    ax=ax
)
```

### catplot() (figure-level)

```python
sns.catplot(data=df, x='category', y='value',
    hue='group',
    col='time',
    kind='box',         # 'strip', 'swarm', 'box', 'violin', 'bar', 'point'
    height=4,
    aspect=0.8
)
```

## Seaborn regression

### regplot()

```python
sns.regplot(data=df, x='x', y='y',
    order=1,            # Polynomial order
    ci=95,              # Confidence interval
    scatter_kws={'alpha': 0.5},
    line_kws={'color': 'red'},
    ax=ax
)
```

### lmplot() (figure-level)

```python
sns.lmplot(data=df, x='x', y='y',
    hue='group',
    col='condition',
    order=1,
    ci=95,
    height=4,
    aspect=1.2
)
```

## Seaborn matrix

### heatmap()

```python
sns.heatmap(data,
    annot=True,         # Show values
    fmt='.2f',          # Annotation format
    cmap='coolwarm',
    center=0,           # Center colormap
    vmin=-1, vmax=1,    # Color limits
    square=True,
    linewidths=0.5,
    cbar_kws={'label': 'Value'},
    ax=ax
)
```

### clustermap()

```python
sns.clustermap(data,
    method='ward',       # Linkage method
    metric='euclidean',
    z_score=0,           # Normalize rows (0) or cols (1)
    cmap='viridis',
    figsize=(10, 10),
    row_colors=colors,
    col_colors=colors,
    dendrogram_ratio=0.1
)
```

## Seaborn theming

```python
# Complete theme
sns.set_theme(style='whitegrid', context='paper', font_scale=1.1)

# Style only
sns.set_style('ticks')  # 'darkgrid', 'whitegrid', 'dark', 'white', 'ticks'

# Context only (scaling)
sns.set_context('talk')  # 'paper', 'notebook', 'talk', 'poster'

# Palette
sns.set_palette('colorblind')

# Despine
sns.despine(offset=10, trim=True)
```

## Common parameter values

### errorbar options

- `'ci'` or `('ci', level)` - Bootstrap confidence interval
- `'pi'` or `('pi', level)` - Percentile interval
- `'se'` or `('se', scale)` - Standard error
- `'sd'` - Standard deviation
- `None` - No error bars

### stat options (histplot)

- `'count'` - Number of observations
- `'frequency'` - Count / bin width
- `'probability'` - Normalized to sum to 1
- `'percent'` - Normalized to sum to 100
- `'density'` - Normalized so area = 1

### kind options

| Function | Options |
|----------|---------|
| `relplot` | `'scatter'`, `'line'` |
| `displot` | `'hist'`, `'kde'`, `'ecdf'` |
| `catplot` | `'strip'`, `'swarm'`, `'box'`, `'violin'`, `'boxen'`, `'bar'`, `'point'`, `'count'` |
| `jointplot` | `'scatter'`, `'kde'`, `'hist'`, `'hex'`, `'reg'`, `'resid'` |
