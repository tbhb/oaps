---
name: styling
title: Styling and customization
description: >-
  Comprehensive guide to colormaps, color palettes, themes, typography, and
  visual customization for matplotlib and seaborn. Load when customizing plot
  appearance or creating publication-quality figures.
principles:
  - Use perceptually uniform colormaps for continuous data
  - Consider colorblind accessibility in color choices
  - Match colormap type to data type (sequential, diverging, qualitative)
  - Use consistent styling across related figures
best_practices:
  - "**Avoid jet**: Use viridis, plasma, or cividis instead"
  - "**Diverging for centered data**: coolwarm, RdBu for data with meaningful zero"
  - "**Qualitative for categories**: tab10, Set2 for distinct groups"
  - "**Colorblind-safe**: viridis, cividis, or colorblind palette"
checklist:
  - Colormap matches data type
  - Colors are accessible
  - Consistent styling across figure panels
  - Appropriate DPI and format for output
related:
  - matplotlib-fundamentals
  - seaborn-fundamentals
  - api-reference
---

# Styling and customization

## Colormaps

### Categories

**Perceptually uniform sequential** - Best for ordered data:

- `viridis` (default, colorblind-friendly)
- `plasma`
- `inferno`
- `magma`
- `cividis` (optimized for colorblind viewers)

**Traditional sequential**:

- `Blues`, `Greens`, `Reds`, `Oranges`, `Purples`
- `YlOrBr`, `YlOrRd`, `OrRd`, `PuRd`
- `BuPu`, `GnBu`, `PuBu`, `YlGnBu`

**Diverging** - For data with meaningful center:

- `coolwarm` (blue to red)
- `RdBu` (red-blue)
- `RdYlBu` (red-yellow-blue)
- `PiYG`, `PRGn`, `BrBG`, `PuOr`

**Qualitative** - For categorical data:

- `tab10` (10 distinct colors)
- `tab20` (20 distinct colors)
- `Set1`, `Set2`, `Set3`
- `Pastel1`, `Pastel2`
- `Dark2`, `Accent`, `Paired`

**Cyclic** - For phase/angle data:

- `twilight`
- `twilight_shifted`
- `hsv`

### Best practices

1. **Avoid `jet`** - Not perceptually uniform, misleading
2. **Use perceptually uniform colormaps** for continuous data
3. **Consider colorblind users** - Test with simulators
4. **Match colormap to data type**:
   - Sequential: increasing/decreasing values
   - Diverging: data with meaningful center
   - Qualitative: distinct categories
5. **Reverse with `_r` suffix**: `viridis_r`, `coolwarm_r`

### Usage

```python
# In imshow/heatmap
ax.imshow(data, cmap='viridis')
sns.heatmap(data, cmap='coolwarm', center=0)

# In scatter
ax.scatter(x, y, c=values, cmap='plasma')
sns.scatterplot(data=df, x='x', y='y', hue='value', palette='viridis')
```

### Custom colormaps

```python
from matplotlib.colors import LinearSegmentedColormap

# From color list
colors = ['blue', 'white', 'red']
cmap = LinearSegmentedColormap.from_list('custom', colors, N=100)

# Use
ax.imshow(data, cmap=cmap)
```

### Discrete colormaps

```python
import matplotlib.colors as mcolors

cmap = plt.cm.viridis
bounds = np.linspace(0, 10, 11)
norm = mcolors.BoundaryNorm(bounds, cmap.N)
im = ax.imshow(data, cmap=cmap, norm=norm)
```

## Seaborn color palettes

### Qualitative palettes

```python
# Built-in palettes
sns.set_palette('colorblind')  # Colorblind-friendly
sns.set_palette('deep')        # Default, vivid
sns.set_palette('muted')       # Softer
sns.set_palette('pastel')      # Light
sns.set_palette('bright')      # Highly saturated
sns.set_palette('dark')        # Dark values
```

### Sequential palettes

```python
sns.set_palette('rocket')   # Wide luminance range
sns.set_palette('mako')     # Blue-green
sns.set_palette('flare')    # Warm, restricted luminance
sns.set_palette('crest')    # Cool, restricted luminance
```

### Diverging palettes

```python
sns.set_palette('vlag')     # Blue to red
sns.set_palette('icefire')  # Blue to orange
```

### Custom palettes

```python
# Specific colors
custom = ['#E64B35', '#4DBBD5', '#00A087', '#3C5488']
sns.set_palette(custom)

# Generate from colormap
palette = sns.color_palette('viridis', n_colors=5)

# Light to dark gradient
palette = sns.light_palette('seagreen', n_colors=5)

# Diverging from hues
palette = sns.diverging_palette(250, 10, n=9)
```

### Per-plot palette

```python
sns.scatterplot(data=df, x='x', y='y', hue='category', palette='Set2')
```

## Themes and styles

### Seaborn themes

```python
# Complete theme
sns.set_theme(style='whitegrid', context='paper', font_scale=1.1)

# Reset to defaults
sns.set_theme()
```

### Styles

```python
sns.set_style('darkgrid')   # Gray background with white grid (default)
sns.set_style('whitegrid')  # White background with gray grid
sns.set_style('dark')       # Gray background, no grid
sns.set_style('white')      # White background, no grid
sns.set_style('ticks')      # White with axis ticks
```

### Contexts (scaling)

```python
sns.set_context('paper')     # Smallest (default)
sns.set_context('notebook')  # Slightly larger
sns.set_context('talk')      # Presentation slides
sns.set_context('poster')    # Large format
```

### Despine

```python
sns.despine()                          # Remove top and right
sns.despine(left=True)                 # Also remove left
sns.despine(offset=10, trim=True)      # Offset and trim
```

### Matplotlib style sheets

```python
# List available
print(plt.style.available)

# Apply
plt.style.use('seaborn-v0_8-whitegrid')
plt.style.use('ggplot')
plt.style.use('fivethirtyeight')

# Temporary
with plt.style.context('ggplot'):
    fig, ax = plt.subplots()
    ax.plot(x, y)
```

## rcParams configuration

### Global settings

```python
plt.rcParams.update({
    # Figure
    'figure.figsize': (10, 6),
    'figure.dpi': 100,
    'figure.facecolor': 'white',
    'figure.constrained_layout.use': True,

    # Saving
    'savefig.dpi': 300,
    'savefig.bbox': 'tight',
    'savefig.pad_inches': 0.1,

    # Font
    'font.family': 'sans-serif',
    'font.sans-serif': ['Arial', 'Helvetica'],
    'font.size': 12,

    # Axes
    'axes.labelsize': 14,
    'axes.titlesize': 16,
    'axes.linewidth': 1.5,
    'axes.grid': False,
    'axes.spines.top': False,
    'axes.spines.right': False,

    # Lines
    'lines.linewidth': 2,
    'lines.markersize': 8,

    # Ticks
    'xtick.labelsize': 10,
    'ytick.labelsize': 10,
    'xtick.direction': 'in',
    'ytick.direction': 'in',
    'xtick.major.size': 6,
    'ytick.major.size': 6,

    # Legend
    'legend.fontsize': 12,
    'legend.frameon': True,
    'legend.framealpha': 1.0,

    # Grid
    'grid.alpha': 0.3,
    'grid.linestyle': '--',
})
```

### Temporary settings

```python
with plt.rc_context({'font.size': 14, 'lines.linewidth': 2.5}):
    fig, ax = plt.subplots()
    ax.plot(x, y)
```

## Typography

### Font configuration

```python
plt.rcParams['font.family'] = 'serif'
plt.rcParams['font.serif'] = ['Times New Roman']

# Or sans-serif
plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['font.sans-serif'] = ['Arial', 'Helvetica']
```

### Math text

```python
# LaTeX-style (always available)
ax.set_xlabel(r'$\alpha$')
ax.set_title(r'$y = x^2 + \beta$')
ax.text(x, y, r'$\int_0^\infty e^{-x} dx$')

# Greek letters
ax.text(x, y, r'$\alpha, \beta, \gamma, \delta$')

# Subscripts/superscripts
ax.set_ylabel(r'$x_1^2 + x_2^2$')
```

### Full LaTeX (requires installation)

```python
plt.rcParams['text.usetex'] = True
plt.rcParams['text.latex.preamble'] = r'\usepackage{amsmath}'
```

## Spines and grids

### Spine customization

```python
# Hide spines
ax.spines['top'].set_visible(False)
ax.spines['right'].set_visible(False)

# Move spine
ax.spines['left'].set_position(('outward', 10))
ax.spines['bottom'].set_position(('data', 0))

# Style
ax.spines['left'].set_color('gray')
ax.spines['bottom'].set_linewidth(2)
```

### Grid customization

```python
ax.grid(True, which='major', linestyle='--', linewidth=0.8, alpha=0.3)
ax.grid(True, which='minor', linestyle=':', linewidth=0.5, alpha=0.2)
ax.set_axisbelow(True)  # Grid behind data
```

## Legend customization

### Positioning

```python
ax.legend(loc='best')
ax.legend(loc='upper right')
ax.legend(bbox_to_anchor=(1.05, 1), loc='upper left')  # Outside right
ax.legend(bbox_to_anchor=(0.5, -0.15), loc='upper center', ncol=3)  # Below
```

### Styling

```python
ax.legend(
    fontsize=12,
    frameon=True,
    framealpha=0.9,
    fancybox=True,
    shadow=True,
    ncol=2,
    title='Legend Title',
    edgecolor='black',
    facecolor='white'
)
```

### Custom entries

```python
from matplotlib.lines import Line2D

custom_lines = [
    Line2D([0], [0], color='red', lw=2),
    Line2D([0], [0], color='blue', lw=2, linestyle='--'),
    Line2D([0], [0], marker='o', color='w', markerfacecolor='green', markersize=10)
]
ax.legend(custom_lines, ['Label 1', 'Label 2', 'Label 3'])
```

## Publication-ready configuration

```python
# Complete publication style
plt.rcParams.update({
    'figure.figsize': (8, 6),
    'figure.dpi': 100,
    'savefig.dpi': 300,
    'savefig.bbox': 'tight',

    'font.family': 'sans-serif',
    'font.sans-serif': ['Arial'],
    'font.size': 11,

    'axes.labelsize': 12,
    'axes.titlesize': 14,
    'axes.linewidth': 1.5,
    'axes.spines.top': False,
    'axes.spines.right': False,

    'lines.linewidth': 2,
    'lines.markersize': 8,

    'xtick.labelsize': 10,
    'ytick.labelsize': 10,
    'xtick.direction': 'in',
    'ytick.direction': 'in',

    'legend.fontsize': 10,
    'legend.frameon': True,
})

# Seaborn equivalent
sns.set_theme(style='ticks', context='paper', font_scale=1.1,
              rc={'axes.spines.top': False, 'axes.spines.right': False})
```

## Dark theme

```python
plt.style.use('dark_background')

# Or manual
plt.rcParams.update({
    'figure.facecolor': '#1e1e1e',
    'axes.facecolor': '#1e1e1e',
    'axes.edgecolor': 'white',
    'axes.labelcolor': 'white',
    'text.color': 'white',
    'xtick.color': 'white',
    'ytick.color': 'white',
    'grid.color': 'gray',
})
```

## Color accessibility

### Colorblind-friendly palettes

```python
# Seaborn
sns.set_palette('colorblind')

# Matplotlib
colorblind_colors = ['#0173B2', '#DE8F05', '#029E73', '#CC78BC',
                     '#CA9161', '#949494', '#ECE133', '#56B4E9']
```

### Testing

- Use colorblind simulators to test visualizations
- Combine color with patterns/markers when possible
- Ensure sufficient contrast
