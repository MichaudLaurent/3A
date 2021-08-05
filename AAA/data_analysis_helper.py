from typing import List
import pandas
import numpy as np
from AAA.specific_types import *
from AAA.helper_functions import *
import matplotlib
import warnings
from scipy.odr import *

matplotlib.use('Agg')
import gc

from mpl_toolkits.axes_grid1.inset_locator import inset_axes
from .qudev_plot_style import plot_style
import os
from scipy import stats
import matplotlib.pyplot as plt

from sklearn.linear_model import HuberRegressor


def clean_entry_name(entry: str) -> str:
    """ Remove redundant characters writen by the ANSYS reporter tool."""
    entry = entry.replace("ExprCache(", "")
    entry = entry.replace(")", "")
    entry = entry.replace(" ", "")
    final_entry = ''
    for c in entry:
        if c != '[':
            final_entry += c
        else:
            return final_entry
    return entry


def extract_float_from_string(s: Union[float, int, str]) -> float:
    """ Only keep digits and '.' from a string and convert it
    into a float
    """
    if isinstance(s, int):
        return float(s)
    if isinstance(s, float):
        return float(s)
    temp_s = ''
    for c in s:
        if c.isdigit():
            temp_s += c
        elif c == '.':
            temp_s += c

    return float(temp_s)


def find_number_of_solved_setups(design_variable_name: str,
                                 data_frame: pandas.DataFrame):
    """ Find the number of solved variations using a design variable.
    This is 'a hack': design variable are constant for any given mesh
    refinement steps. When receiving the full list of cache variables from a
    solved setup, all the passes are listed."""
    variations = set(data_frame[design_variable_name])
    return len(variations)


def final_entries_dict_from_cache_report(
        full_csv_file_path: str,
        solved_setup_number: int,
        c_target_cache_variables: List[CMatrixTarget] = None,
        convert_all_entries_to_percent: bool = False):
    """ Create a dictionary containing the final values of the
    target parameters and the design parameters.

    Parameters
    ----------
    full_csv_file_path : str
        Full path of the csv file.
    solved_setup_number : int
        Number of optimization steps.
    c_target_cache_variables : List[CMatrixTarget], optional
        If given, the entries of these cache variables will be
        converted to femto Farad units (pico Farad by default on ANSYS).
    convert_all_entries_to_percent : bool, default is False.
        To be use when all the entries correspond to participation ratios.
    Returns
    -------
    dict:
        Dictionary keys are .csv column entries (removed from all brackets
        and units).
    """
    file = pandas.read_csv(full_csv_file_path)
    for column_entry in file.columns:
        column_str = str(column_entry)
        file = file.rename(columns={column_str: clean_entry_name(column_str)})

    final_quantities = {}
    for column_name in list(file.columns):
        if convert_all_entries_to_percent:
            conversion_factor = 100
        else:
            conversion_factor = 1
        opti_var_vect = np.reshape(np.array(file[column_name]) * conversion_factor,
                                   [solved_setup_number, -1])
        temp_list = []
        len_list = []
        for i in range(solved_setup_number):
            temp_vect = [x for x in opti_var_vect[i] if not np.isnan(x)]
            temp_list.append(temp_vect[-1])
            len_list.append(len(temp_vect))
        conv_length = np.min(len_list)
        conv_list = []
        for i in range(solved_setup_number):
            temp_vect = [x for x in opti_var_vect[i] if not np.isnan(x)]
            conv_list.append(temp_vect[-conv_length:])

        if c_target_cache_variables is not None:
            capacitance_var_name = [var.name for var in c_target_cache_variables]
            if column_name in capacitance_var_name:
                # convert pico to femto farad.
                final_quantities.update({column_name: np.array(temp_list) * 1000})
            else:
                final_quantities.update({column_name: temp_list})
        else:
            final_quantities.update({column_name: temp_list})
        final_quantities.update({f"{column_name}_conv": conv_list})
    return final_quantities


def dict_from_report(full_csv_file_path):
    """ Return a dictionary with column names as keys and column content
    as associated list."""
    file = pandas.read_csv(full_csv_file_path)
    final_quantities = {}
    for entry in file.columns:
        temp_list = []
        for item in file[entry]:
            if entry == 'Cost':
                temp_list.append(np.log(extract_float_from_string(item)))
            else:
                temp_list.append(extract_float_from_string(item))

        final_quantities.update({entry: temp_list})
    return final_quantities


def optimization_report(
        title: str,
        png_path_name: str,
        cache_report_path: str,
        opti_report_path: str,
        cache_variables: List[CMatrixTarget],
        optimization_variables: List[OptimizationVariable],
        opti_run: int):
    """ Create a table out of the optimization result in direct correspondence
    with the design design parameter values.

    Parameters
    ----------
    title : str
        Title of the table plot.
    png_path_name : str
        Absolute path of the png file to create.
    cache_report_path : str
        Absolute path to the .csv file containing the cache variable report.
    opti_report_path : str
        Absolute path to the .csv file containing the optimization report.
    cache_variables : List[CMatrixCacheVariable]
        List of capacitance matrix component added to the cache variable list
        of the solver.
    optimization_variables : List[OptimizationVariable]
        List of optimization variable used in the Optimetrics setup.
    opti_run : int
        Number of optimization steps.
    """

    dict_cache = final_entries_dict_from_cache_report(
        full_csv_file_path=cache_report_path,
        solved_setup_number=opti_run,
        c_target_cache_variables=cache_variables)
    dict_opti = dict_from_report(opti_report_path)

    # Find the index which has to be used on the optimization report list
    # to match the one of the cache variables report. (Link the cost function
    # to the capacitance matrix elements).

    cache_var_names = [var['name'] for var in optimization_variables]
    nbr = len(dict_cache[list(dict_cache.keys())[0]])

    matching_indices = []
    for i in range(nbr):
        cache_entry = []
        for var in cache_var_names:
            cache_entry.append(dict_cache[var][i])

        diff_list = []
        for j in range(nbr):
            opti_entry = []
            for var in cache_var_names:
                opti_entry.append(dict_opti[var][j])
            diff_list.append(np.linalg.norm(np.array(opti_entry) - np.array(cache_entry)))
        matching_indices.append(np.argmin(diff_list))

    if len(matching_indices) != nbr:
        return None

    table_components = []
    column_names = []
    for optimization_variable in optimization_variables:
        table_components.append(
            [[dict_opti[optimization_variable['name']][i] for i in matching_indices]])
        column_names.append(optimization_variable['name'])
    for cache_variable in cache_variables:
        table_components.append([dict_cache[cache_variable.name]])
        column_names.append(cache_variable.displaying_name)
    table_components.append([dict_opti['Cost']])
    column_names.append('Log(Cost)')

    # Sort all the table components by decreasing value of cost function.

    sorting_indices = np.argsort(dict_opti['Cost'])

    for i in range(len(table_components)):
        table_components[i][0] = [table_components[i][0][j] for j in sorting_indices]

    assembled_table = None
    for i in range(len(table_components) - 1):
        if assembled_table is None:
            assembled_table = np.concatenate(
                (table_components[0],
                 table_components[1]), axis=0)
        else:
            assembled_table = np.concatenate(
                (assembled_table,
                 table_components[i + 1]), axis=0)

    fig, ax = plt.subplots()
    ax.set_axis_off()
    ax.table(
        cellText=np.around(assembled_table, decimals=3).transpose(),
        colLabels=column_names,
        cellLoc='center',
        loc='upper left')

    ax.set_title(title,
                 fontweight="bold")

    plt.savefig(png_path_name, dpi=300, bbox_inches='tight', pad_inches=0)
    plt.cla()
    plt.clf()
    plt.close('all')
    plt.close(fig)
    # matplotlib is known to exhibit memory leaks even with the use of
    # plt.close(fig) and plt.close('all'). We use the garbage collector
    # to better clean the cache. This is important since we only query 1 GB
    # of RAM on EULER of the entire run.
    gc.collect()


def p_ratio_plots(
        path_to_csv_directory: str,
        dielectric_domains: List[DielectricMaterial],
        variation_parameters_listing: VariationParametersListing,
        hfss_sweep_points: int,
        refinement_iterations: int = 6):
    """ Plot p ratios for the dielectric domains along with the convergence data."""

    plot_style()
    font_size = 25
    bigger_size = 30
    colors = ['k', 'r']
    line_nbr = 2
    col_nbr = 3
    inset_percentage = 40
    plt.rc('font', size=font_size)  # controls default text sizes
    plt.rc('axes', titlesize=font_size)  # fontsize of the axes title
    plt.rc('axes', labelsize=font_size)  # fontsize of the x and y labels
    plt.rc('xtick', labelsize=font_size)  # fontsize of the tick labels
    plt.rc('ytick', labelsize=font_size)  # fontsize of the tick labels
    plt.rc('legend', fontsize=font_size)  # legend fontsize
    plt.rc('figure', titlesize=bigger_size)  # fontsize of the figure title
    plt.rcParams['xtick.major.size'] = 10
    plt.rcParams['xtick.major.width'] = 2

    # ODR modelization

    def f(B, x):
        return B[0] * x + B[1]

    linear = Model(f)

    for project in variation_parameters_listing['project_list']:
        dictionary = final_entries_dict_from_cache_report(
            full_csv_file_path=os.path.join(path_to_csv_directory, "",
                                            f"hfss_cache_{project}.csv"),
            solved_setup_number=hfss_sweep_points,
            convert_all_entries_to_percent=True)

        llt = dictionary['lossy_layer_thickness']
        llt = [llt[i] * 10 for i in range(len(llt))]

        fig, axs = plt.subplots(line_nbr, col_nbr,
                                figsize=(30, 20))
        fitted_p_ratio = []
        for index, dielectric_domain in enumerate(dielectric_domains):
            domain_name = dielectric_domain['final_name']
            ax1 = axs[index // col_nbr, index % col_nbr]

            key = f"p_{domain_name}1_conv"
            y_err = []
            for i in range(len(llt)):
                final_value = dictionary[key][i][-1]
                y_err.append(np.std(dictionary[key][i][-3:]))
                ax1.scatter(llt[i], final_value, color=colors[i % 2])
            x = llt
            y = dictionary[f"p_{domain_name}1"]
            mydata = RealData(x=x, y=y, sy=y_err)

            huber = HuberRegressor(alpha=0.0, epsilon=1.35)
            huber.fit(np.reshape(np.array(x), [len(x), -1]), y)
            coef_ = huber.coef_ * x + huber.intercept_

            ax1.errorbar(x, coef_, yerr=y_err,
                         label='Huber regression',
                         linestyle='--',
                         color='k')
            r2 = huber.score(np.reshape(np.array(x), [len(x), -1]), y)

            from matplotlib.offsetbox import AnchoredText
            anchored_text = AnchoredText('R2 =' + str(truncate(r2, 2)),
                                         loc='lower right',
                                         frameon=False)
            ax1.add_artist(anchored_text)
            ax1.set_ylim((coef_[0] * 0.9, coef_[-1] * 1.1))
            ax1.set_title(f"Dielectric domain {domain_name}")
            ax1.set_xlabel("thin layer thickness [nm]")
            ax1.set_ylabel(r'participation [%]')
            if dielectric_domain['layer_thickness'] != 0:
                participation = (dielectric_domain['layer_thickness'] *
                                 huber.coef_)
            else:
                participation = huber.intercept_

            # unit less percentage
            losses = participation * dielectric_domain['loss_tangent'] / 100
            fitted_p_ratio.append({
                'name': dielectric_domain['final_name'],
                'slope': float(huber.coef_),
                'intercept': float(huber.intercept_),
                'losses': float(losses),
                'participation': float(participation)})

            if huber.coef_ > 0:
                loc = 2
            else:
                loc = 3
            ax2 = inset_axes(ax1,
                             width=f"{inset_percentage}%",
                             height=f"{inset_percentage}%",
                             loc=loc,
                             borderpad=1.2)

            ax2.tick_params(labelleft=False, labelbottom=False)

            for i in range(len(llt)):
                key = f"p_{domain_name}1_conv"
                if refinement_iterations > len(dictionary[key][i]):
                    warnings.warn(f"refinement_iterations ({refinement_iterations}) "
                                  "exceeds total iterations"
                                  f"number ({len(dictionary[key][i])}")
                    refinement_iterations = len(dictionary[key][i])

                conv_vect = dictionary[key][i][-refinement_iterations:]
                ax2.plot(conv_vect,
                         linestyle='--',
                         marker='o',
                         color=colors[i % 2])
            ax2.set_xlabel(f"last {len(conv_vect)} iterations")
            ax2.set_ylabel(r'participation [%]')

        fig.suptitle(f"participation ratio for {project}")
        fig.tight_layout()
        fig.savefig(os.path.join(os.getcwd(), "",
                                 'p_ratio_results', "",
                                 'convergence', "",
                                 f"{project}_convergence_report.png"), dpi=300)
        plt.cla()
        plt.clf()
        plt.close('all')
        plt.close(fig)
        gc.collect()

        save_dict_as_json_file(dict_to_save=fitted_p_ratio,
                               json_name=f"p_ratio_{project}",
                               sub_directory=os.path.join("p_ratio_results",
                                                          "json_p_ratio"))


def table_plot(
        project_listing: VariationParametersListing,
        cartesian_var_param: List[VariationParameters],
        dielectric_domains: List[DielectricMaterial],
        root_of_variation_name: str):
    p_ma = []
    p_ms = []
    p_sa = []
    p_sub_bot = []
    p_sub_top = []
    p_vac = []
    q = []

    for project in project_listing['project_list']:
        with open(os.path.join(os.getcwd(), "",
                               "p_ratio_results", "",
                               "json_p_ratio", "",
                               f"p_ratio_{project}.json")) as jsonFile:
            project_results = json.load(jsonFile)

        project_dict = {}
        q_inv = 0
        for entries in project_results:
            project_dict.update({entries['name']: entries})
            q_inv = q_inv + entries['losses']

        p_ma.append(project_dict['MA']['participation'])
        p_ms.append(project_dict['MS']['participation'])
        p_sa.append(project_dict['SA']['participation'])
        p_sub_bot.append(project_dict['sub_bot']['participation'])
        p_sub_top.append(project_dict['sub_top']['participation'])
        p_vac.append(project_dict['vac']['participation'])
        q.append(1 / q_inv)

    p_ma = np.array(p_ma)
    p_ms = np.array(p_ms)
    p_sa = np.array(p_sa)
    p_sub_bot = np.array(p_sub_bot)
    p_sub_top = np.array(p_sub_top)
    p_vac = np.array(p_vac)
    q = np.array(q)

    sweep_list = []
    names = []
    for var_param in cartesian_var_param:
        sweep_list.append(var_param['sweep'])

    for tuple_sweep in itertools.product(*sweep_list):
        names.append(f"(qb gap = {tuple_sweep[0]}, cp gap = {tuple_sweep[1]})")

    def renorm_c_grid(color_grid):

        unfolded_grid = []
        for x in color_grid:
            for y in x:
                unfolded_grid.append(y)

        if np.max(unfolded_grid - np.min(unfolded_grid)) != 0:
            color_grid = ((unfolded_grid - np.min(unfolded_grid)) /
                          (np.max(unfolded_grid - np.min(unfolded_grid))))
        else:
            color_grid = unfolded_grid - np.min(unfolded_grid)

        color_grid = np.reshape(color_grid, [-1, 3])

        return color_grid

    domain_var = {'p_ma': p_ma,
                  'p_ms': p_ms,
                  'p_sa': p_sa,
                  'p_sub_bot': p_sub_bot,
                  'p_sub_top': p_sub_top,
                  'p_vac': p_vac,
                  'q': q}

    p_ratio_stats = {}
    for domain in domain_var:
        p_ratio_stats.update({
            domain: {'min': np.min(domain_var[domain]),
                     'max': np.max(domain_var[domain]),
                     'average': np.mean(domain_var[domain]),
                     'std': np.std(domain_var[domain])}})

    save_dict_as_json_file(dict_to_save=p_ratio_stats,
                           json_name=f"p_ratio_stats_{root_of_variation_name}",
                           sub_directory=os.path.join("p_ratio_results",
                                                      "json_p_ratio"))

    for domain in domain_var.keys():
        p_grid_0 = np.reshape(domain_var[domain], [-1, 3])
        p_grid = p_grid_0 / p_grid_0[0, 0]
        p_grid = np.around((p_grid - 1) * 100, decimals=2)
        p_grid[0, 0] = np.format_float_scientific(np.float32(p_grid_0[0, 0]))
        c_grid = renorm_c_grid(p_grid)
        fig, ax = plt.subplots()
        ax.set_axis_off()
        ax.table(
            cellText=p_grid,
            rowLabels=['qb gap = 15', 'qb gap = 20', 'qb gap = 25'],
            colLabels=['cp gap = 15', 'cp gap = 20', 'cp gap = 25'],
            cellLoc='center',
            loc='upper left')
        # cellColours=plt.cm.bwr(c_grid))

        ax.set_title(domain,
                     fontweight="bold")

        plt.savefig(os.path.join(os.getcwd(), "",
                                 "p_ratio_results", "",
                                 "tables", "",
                                 f"{root_of_variation_name}_{domain}.png"),
                    dpi=300, bbox_inches='tight',
                    pad_inches=0)
        plt.close()


def report_p_ratio_stats(root_of_variation_names: List[str],
                         dielectric_domains: List[DielectricMaterial]):
    plot_style()
    font_size = 25
    bigger_size = 30

    plt.rc('font', size=font_size)  # controls default text sizes
    plt.rc('axes', titlesize=font_size)  # fontsize of the axes title
    plt.rc('axes', labelsize=font_size)  # fontsize of the x and y labels
    plt.rc('xtick', labelsize=font_size)  # fontsize of the tick labels
    plt.rc('ytick', labelsize=font_size)  # fontsize of the tick labels
    plt.rc('legend', fontsize=font_size)  # legend fontsize
    plt.rc('figure', titlesize=bigger_size)  # fontsize of the figure title

    line_nbr = 2
    col_nbr = 3

    plt.tick_params(
        axis='both',  # changes apply to the x-axis
        which='both',  # both major and minor ticks are affected
        bottom=False,  # ticks along the bottom edge are off
        left=False,
        right=False,
        top=False,  # ticks along the top edge are off
        labelbottom=False)  # labels along the bottom edge are off

    fig, axs = plt.subplots(line_nbr, col_nbr,
                            figsize=(30, 20))
    import matplotlib.ticker as ticker

    domain_var = ('p_ma', 'p_ms', 'p_sa',
                  'p_sub_bot', 'p_sub_top',
                  'p_vac')

    label_list = ['MA', 'MS', 'SA',
                  'bottom substrate', 'top substrate',
                  'vacuum']

    for index0, root_of_variation_name in enumerate(root_of_variation_names):

        with open(os.path.join(
                os.getcwd(), "",
                "p_ratio_results", "",
                "json_p_ratio", "",
                f"p_ratio_stats_{root_of_variation_name}.json")) as jsonFile:
            p_ratio_stats = json.load(jsonFile)

        for index, domain_name in enumerate(domain_var):
            ax1 = axs[index // col_nbr, index % col_nbr]

            ax1.set_xticklabels(root_of_variation_names)
            ax1.xaxis.set_major_locator(ticker.FixedLocator([0, 1, 2, 3]))
            ax1.errorbar(x=index0,
                         y=p_ratio_stats[domain_name]['average'],
                         yerr=[[(p_ratio_stats[domain_name]['average'] -
                                 p_ratio_stats[domain_name]['min'])],
                               [(p_ratio_stats[domain_name]['max'] -
                                 p_ratio_stats[domain_name]['average'])]],
                         fmt='.k', ecolor='gray', lw=1)
            ax1.errorbar(x=index0,
                         y=p_ratio_stats[domain_name]['average'],
                         yerr=p_ratio_stats[domain_name]['std'],
                         fmt='ok', lw=3)
            ax1.set_title(f"{label_list[index]} p-ratio [%]")

    fig.suptitle(f"p_ratio_stats")
    fig.tight_layout()
    fig.savefig(os.path.join(
        os.getcwd(), "",
        'p_ratio_results', "",
        'stats', "",
        f"stats_report.png"), dpi=300)
    plt.close(fig)

    domain_var = ('p_ma', 'p_ms', 'p_sa',
                  'p_sub_bot', 'p_sub_top',
                  'p_vac')

    label_list = ['MA', 'MS', 'SA',
                  'bottom substrate', 'top substrate',
                  'vacuum']

    for index, domain_name in enumerate(domain_var):

        fig, ax1 = plt.subplots(figsize=(10, 10))
        ax1.xaxis.set_major_locator(ticker.FixedLocator([0, 1, 2, 3]))
        for index0, root_of_variation_name in enumerate(root_of_variation_names):
            with open(os.path.join(
                    os.getcwd(), "",
                    "p_ratio_results", "",
                    "json_p_ratio", "",
                    f"p_ratio_stats_{root_of_variation_name}.json")) as jsonFile:
                p_ratio_stats = json.load(jsonFile)

            ax1.set_xticklabels(root_of_variation_names)
            ax1.errorbar(x=index0,
                         y=p_ratio_stats[domain_name]['average'],
                         yerr=[[(p_ratio_stats[domain_name]['average'] -
                                 p_ratio_stats[domain_name]['min'])],
                               [(p_ratio_stats[domain_name]['max'] -
                                 p_ratio_stats[domain_name]['average'])]],
                         fmt='.k', ecolor='gray', lw=1)
            ax1.errorbar(x=index0,
                         y=p_ratio_stats[domain_name]['average'],
                         yerr=p_ratio_stats[domain_name]['std'],
                         fmt='ok', lw=3)

        fig.suptitle(f"p-ratio contribution: {label_list[index]}")
        fig.tight_layout()
        fig.savefig(os.path.join(
            os.getcwd(), "",
            'p_ratio_results', "",
            'stats', "",
            f"p_ratio_stats_{domain_name}.png"), dpi=300)
        plt.close(fig)

    plt.cla()
    plt.clf()
    plt.close('all')
    gc.collect()


def report_losses_histo_average_p(root_of_variation_names: List[str],
                                  dielectric_domains: List[DielectricMaterial]):
    plot_style()
    font_size = 20
    bigger_size = 30

    plt.rc('font', size=font_size)  # controls default text sizes
    plt.rc('axes', titlesize=font_size)  # fontsize of the axes title
    plt.rc('axes', labelsize=font_size)  # fontsize of the x and y labels
    plt.rc('xtick', labelsize=font_size)  # fontsize of the tick labels
    plt.rc('ytick', labelsize=font_size)  # fontsize of the tick labels
    plt.rc('legend', fontsize=font_size)  # legend fontsize
    plt.rc('figure', titlesize=bigger_size)  # fontsize of the figure title

    plt.tick_params(
        axis='both',  # changes apply to the x-axis
        which='both',  # both major and minor ticks are affected
        bottom=False,  # ticks along the bottom edge are off
        left=False,
        right=False,
        top=False,  # ticks along the top edge are off
        labelbottom=False)  # labels along the bottom edge are off

    for root_of_variation_name in root_of_variation_names:
        with open(os.path.join(
                os.getcwd(), "",
                "p_ratio_results", "",
                "json_p_ratio", "",
                f"p_ratio_stats_{root_of_variation_name}.json")) as jsonFile:
            p_ratio_stats = json.load(jsonFile)
        losses = {}
        for index, dielectric_domain in enumerate(dielectric_domains):
            if dielectric_domain['final_name'] in ['MA', 'MS', 'SA']:
                domain_name = f"p_{dielectric_domain['final_name'].lower()}"
            else:
                domain_name = f"p_{dielectric_domain['final_name']}"
            losses.update({dielectric_domain['final_name']: (
                    dielectric_domain['loss_tangent'] *
                    p_ratio_stats[domain_name]['average'])})
        sum_losses = 0
        for key in losses:
            sum_losses += losses[key]
        for key in losses:
            losses[key] /= sum_losses
        print(f"{root_of_variation_name}: {1 / sum_losses * 100}")
        Q_dielectric = 1 / sum_losses * 100
        labels = []
        sizes = []
        colors = []
        conversion_label = {
            'MA': 'MA',
            'MS': 'MS',
            'SA': 'SA',
            'sub_bot': "bottom substrate",
            'sub_top': 'top substrate'}

        color_per_label = {
            'MA': '#F1C40F',  # red
            'MS': '#6008CC',  # blue
            'SA': '#E74C3C',  # turquoise
            'sub_bot': '#2E86C1',  # purple
            'sub_top': '#09AD32'}  # green
        root_of_variation_name_display = {
            'O1_no_GND': 'O1 no GND',
            'O1_GND': 'O1 GND',
            'O2_GND': 'O2 GND',
            'O2_no_GND': 'O2 no GND'}
        for key in losses:
            if key != 'vac':
                if not (root_of_variation_name == 'O2_GND' and
                        key == 'sub_bot'):
                    labels.append(conversion_label[key])
                    sizes.append(losses[key])
                    colors.append(color_per_label[key])

        plt.rc('text', usetex=True)
        fig, ax1 = plt.subplots()
        ax1.pie(sizes, labels=labels, autopct='%1.1f%%',
                startangle=90, colors=colors,
                normalize=False)
        ax1.axis('equal')  # Equal aspect ratio ensures that pie is drawn as a circle.
        fig.suptitle(f"Q={truncate(Q_dielectric / 1e+6, 2)}M")
        plt.rc('text', usetex=False)
        fig.tight_layout()
        fig.savefig(os.path.join(
            os.getcwd(), "",
            'p_ratio_results', "",
            'stats', "",
            f"histogram_{root_of_variation_name}.png"), dpi=300)
        plt.cla()
        plt.clf()
        plt.close('all')
        plt.close(fig)
        gc.collect()


def report_losses_histo_selected_p(project_name: str):
    plot_style()
    font_size = 20
    bigger_size = 30

    plt.rc('font', size=font_size)  # controls default text sizes
    plt.rc('axes', titlesize=font_size)  # fontsize of the axes title
    plt.rc('axes', labelsize=font_size)  # fontsize of the x and y labels
    plt.rc('xtick', labelsize=font_size)  # fontsize of the tick labels
    plt.rc('ytick', labelsize=font_size)  # fontsize of the tick labels
    plt.rc('legend', fontsize=font_size)  # legend fontsize
    plt.rc('figure', titlesize=bigger_size)  # fontsize of the figure title

    plt.tick_params(
        axis='both',  # changes apply to the x-axis
        which='both',  # both major and minor ticks are affected
        bottom=False,  # ticks along the bottom edge are off
        left=False,
        right=False,
        top=False,  # ticks along the top edge are off
        labelbottom=False)  # labels along the bottom edge are off

    with open(os.path.join(
            os.getcwd(), "",
            "p_ratio_results", "",
            "json_p_ratio", "",
            f"p_ratio_{project_name}.json")) as jsonFile:
        p_ratio_dicts = json.load(jsonFile)
    losses = {}
    for p_ratio_dielectric in p_ratio_dicts:
        if p_ratio_dielectric['name'] != 'vac':
            losses.update({p_ratio_dielectric['name']: p_ratio_dielectric['losses']})

    sum_losses = 0
    for key in losses:
        sum_losses += losses[key]
    for key in losses:
        losses[key] /= sum_losses
    Q_dielectric = 1 / sum_losses
    labels = []
    sizes = []
    colors = []
    conversion_label = {
        'MA': 'MA',
        'MS': 'MS',
        'SA': 'SA',
        'sub_bot': "bottom substrate",
        'sub_top': 'top substrate'}

    color_per_label = {
        'MA': '#F1C40F',  # red
        'MS': '#6008CC',  # blue
        'SA': '#E74C3C',  # turquoise
        'sub_bot': '#2E86C1',  # purple
        'sub_top': '#09AD32'}  # green

    for key in losses:
        if key != 'vac':
            if not ('O2_GND' in project_name and
                    key == 'sub_bot'):
                labels.append(conversion_label[key])
                sizes.append(losses[key])
                colors.append(color_per_label[key])

    plt.rc('text', usetex=True)
    fig, ax1 = plt.subplots()
    ax1.pie(sizes, labels=labels, autopct='%1.1f%%',
            startangle=90, colors=colors)
    ax1.axis('equal')  # Equal aspect ratio ensures that pie is drawn as a circle.

    fig.suptitle(f"Q={truncate(Q_dielectric / 1e+6, 2)}M")
    plt.rc('text', usetex=False)
    fig.tight_layout()
    fig.savefig(os.path.join(
        os.getcwd(), "",
        'p_ratio_results', "",
        'stats', "",
        f"histogram_{project_name}.png"), dpi=300)
    plt.cla()
    plt.clf()
    plt.close('all')
    plt.close(fig)
    gc.collect()
