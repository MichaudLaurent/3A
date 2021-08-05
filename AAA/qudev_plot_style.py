import matplotlib.pyplot as plt


def plot_style():
    font_size = 10
    marker_size = 6
    line_width = 2
    axes_line_width = 1
    tick_length = 2
    tick_width = 1
    tick_color = 'k'
    ticks_direction = 'in'
    axes_labelcolor = 'k'
    dpi = 900

    params = {
        'figure.dpi': dpi,
        'savefig.dpi': dpi,
        'font.size': font_size,
        'font.family': "Tahoma",
        'mathtext.default': 'it',
        'mathtext.fontset': "cm",
        'mathtext.it': 'cm',
        'figure.titlesize': font_size,
        'legend.fontsize': font_size,
        'axes.labelsize': font_size,
        'axes.labelcolor': axes_labelcolor,
        'axes.titlesize': font_size,
        'axes.linewidth': axes_line_width,
        'lines.markersize': marker_size,
        'lines.linewidth': line_width,
        'xtick.direction': ticks_direction,
        'ytick.direction': ticks_direction,
        'xtick.labelsize': font_size,
        'ytick.labelsize': font_size,
        'xtick.color': tick_color,
        'ytick.color': tick_color,
        'xtick.major.size': tick_length,
        'ytick.major.size': tick_length,
        'xtick.major.width': tick_width,
        'ytick.major.width': tick_width,
        'xtick.top': True,
        'xtick.bottom': True,
        'ytick.left': True,
        'ytick.right': True,
        'axes.formatter.useoffset': False,
        'pdf.fonttype': 42,
        'ps.fonttype': 42,
        # LEGEND
        'legend.loc': 'best',
        'legend.frameon': False
    }

    plt.rcParams.update(params)


plot_style()
