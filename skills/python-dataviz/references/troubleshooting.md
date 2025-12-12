---
name: troubleshooting
title: Troubleshooting guide
description: >-
  Solutions to common matplotlib and seaborn issues including display problems,
  layout issues, memory leaks, and styling problems. Load when encountering
  errors or unexpected behavior.
principles:
  - Most issues stem from using pyplot state machine instead of OO interface
  - Layout issues are solved with constrained_layout or tight_layout
  - Memory issues require explicit figure closing
best_practices:
  - "**Use OO interface**: Avoid pyplot state machine issues"
  - "**Close figures**: Prevent memory leaks with plt.close(fig)"
  - "**Check data shapes**: Ensure x and y have matching lengths"
checklist:
  - Using object-oriented interface
  - Constrained layout or tight_layout applied
  - Figures closed after saving
  - Data shapes match
related:
  - matplotlib-fundamentals
  - seaborn-fundamentals
---

# Troubleshooting guide

## Display issues

### Plots not showing

**Problem:** `plt.show()` doesn't display anything.

**Solutions:**

```python
# Check backend
import matplotlib
print(matplotlib.get_backend())

# Try different backend (before importing pyplot)
matplotlib.use('TkAgg')  # or 'Qt5Agg', 'MacOSX'
import matplotlib.pyplot as plt

# In Jupyter
%matplotlib inline    # Static images
%matplotlib widget    # Interactive

# Ensure show() is called
plt.plot([1, 2, 3])
plt.show()
```

### Figures not updating interactively

**Solution:**

```python
plt.ion()  # Enable interactive mode
plt.plot(x, y)
plt.draw()
plt.pause(0.001)
```

### "main thread is not in main loop" error

**Solution:**

```python
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend
import matplotlib.pyplot as plt
plt.ioff()
```

## Layout issues

### Overlapping labels and titles

**Solutions:**

```python
# Solution 1: Constrained layout (recommended)
fig, ax = plt.subplots(constrained_layout=True)

# Solution 2: Tight layout
plt.tight_layout()

# Solution 3: Manual adjustment
plt.subplots_adjust(left=0.15, right=0.95, top=0.95, bottom=0.15)

# Solution 4: Save with tight bbox
plt.savefig('figure.png', bbox_inches='tight')

# Solution 5: Rotate tick labels
ax.set_xticklabels(labels, rotation=45, ha='right')
```

### Colorbar affects subplot size

**Solutions:**

```python
# Solution 1: Constrained layout
fig, ax = plt.subplots(constrained_layout=True)
im = ax.imshow(data)
plt.colorbar(im, ax=ax)

# Solution 2: Dedicated colorbar axes
from mpl_toolkits.axes_grid1 import make_axes_locatable
divider = make_axes_locatable(ax)
cax = divider.append_axes("right", size="5%", pad=0.05)
plt.colorbar(im, cax=cax)
```

### Subplots too close together

**Solutions:**

```python
# Solution 1: Constrained layout
fig, axes = plt.subplots(2, 2, constrained_layout=True)

# Solution 2: Adjust spacing
plt.subplots_adjust(hspace=0.4, wspace=0.4)

# Solution 3: Tight layout with padding
plt.tight_layout(h_pad=2.0, w_pad=2.0)
```

## Memory issues

### Memory leak with many figures

**Solution:**

```python
fig, ax = plt.subplots()
ax.plot(x, y)
plt.savefig('plot.png')
plt.close(fig)  # or plt.close('all')

# Clear without closing
plt.clf()  # Clear figure
plt.cla()  # Clear axes
```

### Large file sizes

**Solutions:**

```python
# Reduce DPI
plt.savefig('figure.png', dpi=150)

# Rasterize complex plots
ax.plot(x, y, rasterized=True)

# Use vector format for simple plots
plt.savefig('figure.pdf')
```

### Slow plotting with large datasets

**Solutions:**

```python
# Downsample
from scipy.signal import decimate
y_down = decimate(y, 10)

# Rasterize
ax.plot(x, y, rasterized=True)

# Use hexbin instead of scatter
ax.hexbin(x, y, gridsize=50, cmap='viridis')
```

## Font issues

### Font not found warning

**Solutions:**

```python
# Use available fonts
from matplotlib.font_manager import findfont, FontProperties
print(findfont(FontProperties(family='sans-serif')))

# Rebuild font cache
import matplotlib.font_manager
matplotlib.font_manager._rebuild()

# Suppress warnings
import warnings
warnings.filterwarnings("ignore", category=UserWarning)

# Specify fallback fonts
plt.rcParams['font.sans-serif'] = ['Arial', 'DejaVu Sans', 'sans-serif']
```

### LaTeX rendering errors

**Solutions:**

```python
# Use raw strings
ax.set_xlabel(r'$\alpha$')  # Not '\alpha'

# Escape backslashes
ax.set_xlabel('$\\alpha$')

# Disable LaTeX if not installed
plt.rcParams['text.usetex'] = False
```

## Color issues

### Colorbar not matching plot

**Solution:**

```python
# Explicitly set vmin/vmax
im = ax.imshow(data, vmin=0, vmax=1, cmap='viridis')
plt.colorbar(im)

# Use same norm for multiple plots
from matplotlib.colors import Normalize
norm = Normalize(vmin=data.min(), vmax=data.max())
im1 = ax1.imshow(data1, norm=norm, cmap='viridis')
im2 = ax2.imshow(data2, norm=norm, cmap='viridis')
```

### Colormap reversed

**Solution:**

```python
# Add _r suffix to reverse
ax.imshow(data, cmap='viridis_r')
```

## Axis issues

### Axis limits not working

**Solutions:**

```python
# Set after plotting
ax.plot(x, y)
ax.set_xlim(0, 10)

# Disable autoscaling
ax.autoscale(False)
ax.set_xlim(0, 10)
```

### Log scale with zero/negative values

**Solutions:**

```python
# Filter non-positive values
mask = data > 0
ax.plot(x[mask], data[mask])
ax.set_yscale('log')

# Use symlog for mixed data
ax.set_yscale('symlog')

# Add small offset
ax.plot(x, data + 1e-10)
ax.set_yscale('log')
```

### Dates not displaying correctly

**Solution:**

```python
import matplotlib.dates as mdates
import pandas as pd

dates = pd.to_datetime(date_strings)
ax.plot(dates, values)
ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m-%d'))
ax.xaxis.set_major_locator(mdates.DayLocator(interval=7))
plt.xticks(rotation=45)
```

## Legend issues

### Legend covers data

**Solutions:**

```python
# Auto-position
ax.legend(loc='best')

# Place outside
ax.legend(bbox_to_anchor=(1.05, 1), loc='upper left')

# Semi-transparent
ax.legend(framealpha=0.7)

# Below plot
ax.legend(bbox_to_anchor=(0.5, -0.15), loc='upper center', ncol=3)
```

### Too many legend items

**Solutions:**

```python
# Label only some
for i, (x, y) in enumerate(data):
    label = f'Data {i}' if i % 5 == 0 else None
    ax.plot(x, y, label=label)

# Multiple columns
ax.legend(ncol=3)
```

## Seaborn-specific issues

### Legend outside plot area (figure-level)

**Solution:**

```python
g = sns.relplot(data=df, x='x', y='y', hue='category')
g._legend.set_bbox_to_anchor((0.9, 0.5))
```

### Figure too small

**Solutions:**

```python
# Figure-level functions
sns.relplot(data=df, x='x', y='y', height=6, aspect=1.5)

# Axes-level functions
fig, ax = plt.subplots(figsize=(10, 6))
sns.scatterplot(data=df, x='x', y='y', ax=ax)
```

### KDE too smooth or jagged

**Solution:**

```python
sns.kdeplot(data=df, x='x', bw_adjust=0.5)  # Less smooth
sns.kdeplot(data=df, x='x', bw_adjust=2)    # More smooth
```

### Colors not distinct

**Solutions:**

```python
# Different palette
sns.set_palette('bright')

# More colors
n = df['category'].nunique()
palette = sns.color_palette('husl', n_colors=n)
sns.scatterplot(data=df, x='x', y='y', hue='category', palette=palette)
```

## Common errors

### "AxesSubplot object is not subscriptable"

```python
# Wrong
fig, ax = plt.subplots()
ax[0].plot(x, y)  # Error!

# Correct
fig, ax = plt.subplots()
ax.plot(x, y)
```

### "x and y must have same first dimension"

```python
# Check shapes
print(f"x: {x.shape}, y: {y.shape}")
assert len(x) == len(y)
```

### "numpy.ndarray object has no attribute 'plot'"

```python
# Wrong
data.plot(x, y)

# Correct
ax.plot(x, y)
# Or for pandas
data.plot(ax=ax)
```

## Best practices to avoid issues

1. **Use object-oriented interface**

   ```python
   fig, ax = plt.subplots()
   ax.plot(x, y)
   ```

2. **Use constrained_layout**

   ```python
   fig, ax = plt.subplots(constrained_layout=True)
   ```

3. **Close figures explicitly**

   ```python
   plt.close(fig)
   ```

4. **Set figure size at creation**

   ```python
   fig, ax = plt.subplots(figsize=(10, 6))
   ```

5. **Use raw strings for math**

   ```python
   ax.set_xlabel(r'$\alpha$')
   ```

6. **Check data shapes**

   ```python
   assert len(x) == len(y)
   ```

7. **Use appropriate DPI**

   ```python
   plt.savefig('figure.png', dpi=300)  # Print
   plt.savefig('figure.png', dpi=150)  # Web
   ```
