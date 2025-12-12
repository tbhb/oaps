---
name: plot-types
title: Plot types guide
description: >-
  Comprehensive guide to selecting and creating different plot types with both
  matplotlib and seaborn. Load when deciding which visualization to use or
  needing code examples for specific plot types.
principles:
  - Choose plot type based on data structure and question
  - Use seaborn for statistical plots, matplotlib for custom visualizations
  - Consider accessibility when selecting colors and styles
best_practices:
  - "**Distribution**: histplot/kdeplot for single variable, jointplot for bivariate"
  - "**Relationships**: scatterplot for exploration, regplot for trends"
  - "**Comparisons**: boxplot/violinplot for distributions, barplot for aggregates"
  - "**Time series**: lineplot with proper date formatting"
checklist:
  - Plot type matches data structure
  - Appropriate for the analytical question
  - Accessible colors and styling
related:
  - matplotlib-fundamentals
  - seaborn-fundamentals
  - styling
---

# Plot types guide

## Selection guide

| Data Type | Recommended | Seaborn | Matplotlib |
|-----------|-------------|---------|------------|
| Single continuous | Distribution | `histplot`, `kdeplot` | `hist` |
| Two continuous | Relationship | `scatterplot`, `regplot` | `scatter`, `plot` |
| Time series | Trend | `lineplot` | `plot` |
| Categorical vs continuous | Comparison | `boxplot`, `violinplot`, `barplot` | `boxplot`, `bar` |
| Matrix/grid | Heatmap | `heatmap`, `clustermap` | `imshow` |
| Correlation matrix | Relationship | `heatmap` | `imshow` |
| Pairwise relationships | Overview | `pairplot` | Manual subplots |
| Bivariate with margins | Joint | `jointplot` | Manual layout |
| 3D data | Surface/scatter | - | `plot_surface`, `scatter` |
| Proportions | Parts of whole | - | `pie`, `bar` |

## Line plots

**Use for:** Time series, continuous trends, function visualization.

### Matplotlib

```python
fig, ax = plt.subplots(figsize=(10, 6))
ax.plot(x, y, linewidth=2, label='Series 1')
ax.plot(x, y2, linewidth=2, linestyle='--', label='Series 2')
ax.set_xlabel('X')
ax.set_ylabel('Y')
ax.legend()
```

### Seaborn (with aggregation)

```python
# Automatic mean and confidence interval
sns.lineplot(data=df, x='time', y='value', hue='category', errorbar='ci')

# Faceted
sns.relplot(data=df, x='time', y='value', hue='group', col='condition', kind='line')
```

### With error bands

```python
ax.plot(x, y_mean, linewidth=2)
ax.fill_between(x, y_mean - y_std, y_mean + y_std, alpha=0.3)
```

## Scatter plots

**Use for:** Relationships, correlations, clusters.

### Basic scatter

```python
# Matplotlib
ax.scatter(x, y, s=50, alpha=0.6)

# Seaborn
sns.scatterplot(data=df, x='x', y='y')
```

### Multi-dimensional encoding

```python
sns.scatterplot(data=df, x='x', y='y',
                hue='category',      # Color
                size='importance',   # Size
                style='type',        # Marker
                alpha=0.6)
```

### With regression line

```python
sns.regplot(data=df, x='x', y='y', scatter_kws={'alpha': 0.5})
```

### Large datasets

```python
# Hexbin for density
ax.hexbin(x, y, gridsize=30, cmap='viridis')

# 2D histogram
ax.hist2d(x, y, bins=30, cmap='Blues')
```

## Bar charts

**Use for:** Categorical comparisons, counts.

### Vertical bars

```python
# Matplotlib
ax.bar(categories, values, color='steelblue', edgecolor='black')

# Seaborn (with error bars)
sns.barplot(data=df, x='category', y='value', errorbar='ci')
```

### Grouped bars

```python
# Seaborn
sns.barplot(data=df, x='category', y='value', hue='group')

# Matplotlib
x = np.arange(len(categories))
width = 0.35
ax.bar(x - width/2, values1, width, label='Group 1')
ax.bar(x + width/2, values2, width, label='Group 2')
ax.set_xticks(x)
ax.set_xticklabels(categories)
```

### Stacked bars

```python
ax.bar(categories, values1, label='Part 1')
ax.bar(categories, values2, bottom=values1, label='Part 2')
```

### Count plot

```python
sns.countplot(data=df, x='category', hue='group')
```

## Histograms

**Use for:** Distribution of single variable.

### Basic histogram

```python
# Matplotlib
ax.hist(data, bins=30, edgecolor='black', alpha=0.7)

# Seaborn
sns.histplot(data=df, x='value', bins=30)
```

### Overlapping distributions

```python
sns.histplot(data=df, x='value', hue='group', element='step', stat='density')
```

### With KDE overlay

```python
sns.histplot(data=df, x='value', kde=True, stat='density')
```

### Normalized

```python
sns.histplot(data=df, x='value', stat='probability')  # or 'density', 'percent'
```

## KDE (Kernel Density Estimation)

**Use for:** Smooth distribution estimates.

### Univariate

```python
sns.kdeplot(data=df, x='value', hue='group', fill=True, alpha=0.5)
```

### Bivariate

```python
sns.kdeplot(data=df, x='x', y='y', fill=True, levels=10, cmap='viridis')
```

### Bandwidth adjustment

```python
sns.kdeplot(data=df, x='value', bw_adjust=0.5)  # Less smooth
sns.kdeplot(data=df, x='value', bw_adjust=2)    # More smooth
```

## Box plots

**Use for:** Distribution summary, quartiles, outliers.

### Basic

```python
# Matplotlib
ax.boxplot([data1, data2, data3], labels=['A', 'B', 'C'])

# Seaborn
sns.boxplot(data=df, x='category', y='value')
```

### Grouped

```python
sns.boxplot(data=df, x='category', y='value', hue='group')
```

### With individual points

```python
sns.boxplot(data=df, x='category', y='value')
sns.stripplot(data=df, x='category', y='value', color='black', alpha=0.3, size=3)
```

## Violin plots

**Use for:** Distribution shape with density.

```python
sns.violinplot(data=df, x='category', y='value', hue='group', split=True)
```

### With inner annotations

```python
sns.violinplot(data=df, x='category', y='value', inner='quartile')
# inner options: 'box', 'quartile', 'point', 'stick', None
```

## Heatmaps

**Use for:** Matrix data, correlations.

### Correlation matrix

```python
corr = df.corr()
mask = np.triu(np.ones_like(corr, dtype=bool))  # Upper triangle mask
sns.heatmap(corr, mask=mask, annot=True, fmt='.2f',
            cmap='coolwarm', center=0, square=True)
```

### With annotations

```python
sns.heatmap(matrix, annot=True, fmt='.1f', cmap='viridis',
            linewidths=0.5, cbar_kws={'label': 'Value'})
```

### Clustered

```python
sns.clustermap(data, method='ward', cmap='viridis',
               standard_scale=1, figsize=(10, 10))
```

## Joint plots

**Use for:** Bivariate distribution with marginals.

```python
# Scatter with marginal histograms
sns.jointplot(data=df, x='x', y='y', kind='scatter')

# KDE
sns.jointplot(data=df, x='x', y='y', kind='kde', fill=True)

# Regression
sns.jointplot(data=df, x='x', y='y', kind='reg')

# Hexbin for large data
sns.jointplot(data=df, x='x', y='y', kind='hex')
```

### With hue

```python
sns.jointplot(data=df, x='x', y='y', hue='category')
```

## Pair plots

**Use for:** Pairwise relationships overview.

```python
sns.pairplot(data=df, hue='species', corner=True)
```

### Custom diagonal

```python
sns.pairplot(data=df, hue='species', diag_kind='kde')
```

### Selected variables

```python
sns.pairplot(data=df, vars=['var1', 'var2', 'var3'], hue='group')
```

## Contour plots

**Use for:** 3D data on 2D plane, topography.

### Contour lines

```python
contour = ax.contour(X, Y, Z, levels=10, cmap='viridis')
ax.clabel(contour, inline=True, fontsize=8)
```

### Filled contours

```python
contourf = ax.contourf(X, Y, Z, levels=20, cmap='viridis')
plt.colorbar(contourf)
```

## 3D plots

**Use for:** Three-dimensional data visualization.

```python
from mpl_toolkits.mplot3d import Axes3D

fig = plt.figure(figsize=(10, 8))
ax = fig.add_subplot(111, projection='3d')

# Surface
ax.plot_surface(X, Y, Z, cmap='viridis')

# Scatter
ax.scatter(x, y, z, c=colors, cmap='viridis')

# Labels
ax.set_xlabel('X')
ax.set_ylabel('Y')
ax.set_zlabel('Z')
ax.view_init(elev=30, azim=45)
```

## Time series

**Use for:** Temporal data.

### With proper date formatting

```python
import matplotlib.dates as mdates

ax.plot(dates, values)
ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
ax.xaxis.set_major_locator(mdates.DayLocator(interval=7))
plt.xticks(rotation=45, ha='right')
```

### Seaborn with aggregation

```python
sns.lineplot(data=df, x='date', y='value', hue='category', errorbar='sd')
```

### Shaded regions

```python
ax.axvspan(start_date, end_date, alpha=0.2, color='gray', label='Period')
```

## Categorical scatters

### Strip plot (jittered)

```python
sns.stripplot(data=df, x='category', y='value', jitter=0.2)
```

### Swarm plot (non-overlapping)

```python
sns.swarmplot(data=df, x='category', y='value')
```

### Point plot (with CI)

```python
sns.pointplot(data=df, x='timepoint', y='value', hue='treatment',
              markers=['o', 's'], linestyles=['-', '--'])
```

## Pie and donut charts

**Use sparingly for proportions.**

```python
ax.pie(sizes, labels=labels, autopct='%1.1f%%', startangle=90)
ax.axis('equal')

# Donut
ax.pie(sizes, labels=labels, autopct='%1.1f%%',
       wedgeprops=dict(width=0.5), startangle=90)
```

## Polar plots

**Use for:** Cyclic data, radar charts.

```python
ax = plt.subplot(111, projection='polar')
ax.plot(theta, r, linewidth=2)
ax.fill(theta, r, alpha=0.25)
```

## Combining plot types

### Box + strip

```python
sns.boxplot(data=df, x='category', y='value', color='lightblue')
sns.stripplot(data=df, x='category', y='value', color='black', alpha=0.3)
```

### Violin + swarm

```python
sns.violinplot(data=df, x='category', y='value', inner=None, alpha=0.3)
sns.swarmplot(data=df, x='category', y='value', color='black', size=3)
```

### Scatter + regression

```python
sns.scatterplot(data=df, x='x', y='y', alpha=0.5)
sns.regplot(data=df, x='x', y='y', scatter=False, color='red')
```
