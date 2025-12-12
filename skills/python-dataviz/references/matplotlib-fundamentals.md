---
name: matplotlib-fundamentals
title: Matplotlib fundamentals
description: >-
  Core matplotlib concepts including the object hierarchy, interfaces, common
  plotting operations, and figure management. Load when working with matplotlib
  directly or needing fine-grained control over visualizations.
principles:
  - Use object-oriented interface for production code
  - Create figures explicitly rather than relying on implicit state
  - Set figure size at creation time
  - Close figures explicitly to prevent memory leaks
best_practices:
  - "**OO interface**: Always use `fig, ax = plt.subplots()` for production code"
  - "**Constrained layout**: Use `constrained_layout=True` to prevent overlaps"
  - "**Explicit sizing**: Set figsize at creation, not after"
  - "**Memory management**: Close figures with `plt.close(fig)` when done"
checklist:
  - Using object-oriented interface (not pyplot state machine)
  - Figure size set at creation
  - Using constrained_layout or tight_layout
  - Figures closed after saving
related:
  - styling
  - api-reference
  - troubleshooting
---

# Matplotlib fundamentals

## The matplotlib hierarchy

Matplotlib uses a hierarchical structure of objects:

1. **Figure** - The top-level container for all plot elements
2. **Axes** - The actual plotting area where data is displayed (one Figure can contain multiple Axes)
3. **Artist** - Everything visible on the figure (lines, text, ticks, patches, etc.)
4. **Axis** - The number line objects (x-axis, y-axis) that handle ticks and labels

## Interfaces

### Object-oriented interface (recommended)

```python
import matplotlib.pyplot as plt
import numpy as np

# Create figure and axes explicitly
fig, ax = plt.subplots(figsize=(10, 6))

# Generate and plot data
x = np.linspace(0, 2*np.pi, 100)
ax.plot(x, np.sin(x), label='sin(x)')
ax.plot(x, np.cos(x), label='cos(x)')

# Customize
ax.set_xlabel('x')
ax.set_ylabel('y')
ax.set_title('Trigonometric Functions')
ax.legend()
ax.grid(True, alpha=0.3)

# Save and/or display
plt.savefig('plot.png', dpi=300, bbox_inches='tight')
plt.show()
```

### pyplot interface (quick exploration only)

```python
plt.plot([1, 2, 3, 4])
plt.ylabel('some numbers')
plt.show()
```

The pyplot interface maintains state automatically but is harder to debug and maintain.

## Figure creation

### Single axes

```python
fig, ax = plt.subplots(figsize=(10, 6))
```

### Multiple subplots (regular grid)

```python
fig, axes = plt.subplots(2, 2, figsize=(12, 10))
axes[0, 0].plot(x, y1)
axes[0, 1].scatter(x, y2)
axes[1, 0].bar(categories, values)
axes[1, 1].hist(data, bins=30)
```

### Mosaic layout (flexible)

```python
fig, axes = plt.subplot_mosaic([['left', 'right_top'],
                                 ['left', 'right_bottom']],
                                figsize=(10, 8))
axes['left'].plot(x, y)
axes['right_top'].scatter(x, y)
axes['right_bottom'].hist(data)
```

### GridSpec (maximum control)

```python
from matplotlib.gridspec import GridSpec

fig = plt.figure(figsize=(12, 8))
gs = GridSpec(3, 3, figure=fig)
ax1 = fig.add_subplot(gs[0, :])      # Top row, all columns
ax2 = fig.add_subplot(gs[1:, 0])     # Bottom two rows, first column
ax3 = fig.add_subplot(gs[1:, 1:])    # Bottom two rows, last two columns
```

## Common plotting methods

### Line plots

```python
ax.plot(x, y, linewidth=2, linestyle='--', marker='o', color='blue', label='data')
```

### Scatter plots

```python
ax.scatter(x, y, s=sizes, c=colors, alpha=0.6, cmap='viridis')
```

### Bar charts

```python
ax.bar(categories, values, color='steelblue', edgecolor='black')
ax.barh(categories, values)  # Horizontal
```

### Histograms

```python
ax.hist(data, bins=30, edgecolor='black', alpha=0.7, density=True)
```

### Heatmaps

```python
im = ax.imshow(matrix, cmap='coolwarm', aspect='auto')
plt.colorbar(im, ax=ax)
```

### Contours

```python
contour = ax.contour(X, Y, Z, levels=10)
ax.clabel(contour, inline=True, fontsize=8)
contourf = ax.contourf(X, Y, Z, levels=20, cmap='viridis')
```

### Error bars

```python
ax.errorbar(x, y, yerr=error, fmt='o-', capsize=5, capthick=2)
```

### Fill between

```python
ax.fill_between(x, y - std, y + std, alpha=0.3, label='uncertainty')
```

## Customization

### Labels and titles

```python
ax.set_xlabel('X Label', fontsize=12)
ax.set_ylabel('Y Label', fontsize=12)
ax.set_title('Title', fontsize=14, fontweight='bold')
fig.suptitle('Figure Title', fontsize=16)
```

### Axis limits and scales

```python
ax.set_xlim(0, 10)
ax.set_ylim(-1, 1)
ax.set_xscale('log')
ax.set_yscale('symlog')
```

### Ticks

```python
ax.set_xticks([0, 1, 2, 3, 4])
ax.set_xticklabels(['A', 'B', 'C', 'D', 'E'], rotation=45, ha='right')
ax.tick_params(axis='both', labelsize=10)
```

### Grid and spines

```python
ax.grid(True, alpha=0.3, linestyle='--')
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)
```

### Legend

```python
ax.legend(loc='best', fontsize=10, frameon=True)
ax.legend(bbox_to_anchor=(1.05, 1), loc='upper left')  # Outside
```

### Text and annotations

```python
ax.text(x, y, 'annotation', fontsize=12, ha='center')
ax.annotate('important', xy=(x, y), xytext=(x+1, y+1),
            arrowprops=dict(arrowstyle='->', color='red'))
```

## Saving figures

```python
# High-resolution PNG
plt.savefig('figure.png', dpi=300, bbox_inches='tight', facecolor='white')

# Vector formats for publications
plt.savefig('figure.pdf', bbox_inches='tight')
plt.savefig('figure.svg', bbox_inches='tight')

# Transparent background
plt.savefig('figure.png', dpi=300, bbox_inches='tight', transparent=True)
```

### Important parameters

- `dpi`: Resolution (300 for publications, 150 for web, 72 for screen)
- `bbox_inches='tight'`: Removes excess whitespace
- `facecolor='white'`: Ensures white background
- `transparent=True`: Transparent background

## 3D plots

```python
from mpl_toolkits.mplot3d import Axes3D

fig = plt.figure(figsize=(10, 8))
ax = fig.add_subplot(111, projection='3d')

# Surface plot
ax.plot_surface(X, Y, Z, cmap='viridis')

# 3D scatter
ax.scatter(x, y, z, c=colors, marker='o')

# Labels
ax.set_xlabel('X')
ax.set_ylabel('Y')
ax.set_zlabel('Z')
ax.view_init(elev=30, azim=45)
```

## Animation

```python
from matplotlib.animation import FuncAnimation

fig, ax = plt.subplots()
line, = ax.plot([], [])

def init():
    ax.set_xlim(0, 2*np.pi)
    ax.set_ylim(-1, 1)
    return line,

def update(frame):
    x = np.linspace(0, 2*np.pi, 100)
    y = np.sin(x + frame/10)
    line.set_data(x, y)
    return line,

anim = FuncAnimation(fig, update, init_func=init,
                     frames=100, interval=50, blit=True)

anim.save('animation.gif', writer='pillow', fps=20)
```

## Line and marker styles

### Line styles

- `'-'` or `'solid'` - Solid line
- `'--'` or `'dashed'` - Dashed line
- `'-.'` or `'dashdot'` - Dash-dot line
- `':'` or `'dotted'` - Dotted line

### Common markers

- `'.'` - Point
- `'o'` - Circle
- `'s'` - Square
- `'^'`, `'v'`, `'<'`, `'>'` - Triangles
- `'*'` - Star
- `'+'`, `'x'` - Plus, X
- `'D'`, `'d'` - Diamond

### Color specifications

- Single character: `'b'`, `'g'`, `'r'`, `'c'`, `'m'`, `'y'`, `'k'`, `'w'`
- Named colors: `'steelblue'`, `'coral'`, `'teal'`
- Hex codes: `'#FF5733'`
- RGB/RGBA tuples: `(0.1, 0.2, 0.3)`, `(0.1, 0.2, 0.3, 0.5)`

## rcParams configuration

```python
plt.rcParams.update({
    # Figure
    'figure.figsize': (10, 6),
    'figure.dpi': 100,
    'savefig.dpi': 300,
    'savefig.bbox': 'tight',

    # Font
    'font.family': 'sans-serif',
    'font.size': 12,

    # Axes
    'axes.labelsize': 14,
    'axes.titlesize': 16,
    'axes.grid': True,

    # Lines
    'lines.linewidth': 2,
    'lines.markersize': 8,

    # Ticks
    'xtick.labelsize': 10,
    'ytick.labelsize': 10,

    # Legend
    'legend.fontsize': 12,
    'legend.frameon': True,
})
```

## Useful utilities

```python
# Twin axes (two y-axes)
ax2 = ax1.twinx()

# Share axes between subplots
fig, (ax1, ax2) = plt.subplots(2, 1, sharex=True)

# Equal aspect ratio
ax.set_aspect('equal', adjustable='box')

# Scientific notation
ax.ticklabel_format(style='scientific', axis='y', scilimits=(0, 0))

# Date formatting
import matplotlib.dates as mdates
ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
ax.xaxis.set_major_locator(mdates.DayLocator(interval=7))
```
