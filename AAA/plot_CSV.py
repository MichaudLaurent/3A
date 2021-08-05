import os
import json
import itertools
import matplotlib
matplotlib.use('Agg')
import numpy as np
import pandas as pd
from .helper_functions import *
import matplotlib.pyplot as plt
from sklearn.linear_model import HuberRegressor
from .qudev_plot_style import plot_style


def plot_csv(
        variation_parameters_dict,
        root_of_variation_name,
        dielectric_materials,
        exec_option):
    pending_projects = get_project_list(
        variation_parameters_dict,
        root_of_variation_name
    )

    plot_style()

    for pending_project in pending_projects:
        analyse_p_ratio(pending_project,
                        dielectric_materials,
                        exec_option=exec_option,
                        root_of_variation_name=root_of_variation_name)

    project_list = get_project_list(
        variation_parameters_dict=variation_parameters_dict,
        root_of_variation_name=root_of_variation_name
    )

    if exec_option == 'local':
        saving_address = os.getcwd() + "\\"
    else:
        saving_address = os.getcwd() + "/"
    p_MA = []
    p_MS = []
    p_SA = []
    p_sub_bot = []
    p_sub_top = []
    p_vac = []
    Q = []

    for project in project_list:
        with open(f"{saving_address}p_ratio_{project}.json") as jsonFile:
            project_results = json.load(jsonFile)
            project_dict = {}
            Q_inv = 0
            for entries in project_results:
                project_dict.update({entries['name']: entries})
                Q_inv = Q_inv + entries['losses']
            p_MA.append(project_dict['MA']['slope'] * 100)
            p_MS.append(project_dict['MS']['slope'] * 100)
            p_SA.append(project_dict['SA']['slope'] * 100)
            p_sub_bot.append(project_dict['sub_bot']['intercept'])
            p_sub_top.append(project_dict['sub_top']['intercept'])
            p_vac.append(project_dict['vac']['intercept'])
            Q.append(1 / Q_inv)

    p_MA = np.array(p_MA)
    p_MS = np.array(p_MS)
    p_SA = np.array(p_SA)
    p_sub_bot = np.array(p_sub_bot)
    p_sub_top = np.array(p_sub_top)
    p_vac = np.array(p_vac)
    Q = np.array(Q)

    sweep_list = []
    names = []
    for keys in variation_parameters_dict:
        sweep_list.append(variation_parameters_dict[keys]['sweep'])
    for tuple_sweep in itertools.product(*sweep_list):
        names.append(f"(qb gap = {tuple_sweep[0]}, cp gap = {tuple_sweep[1]})")

    table_p_ratio = np.transpose(
        np.array([p_MA, p_MS, p_SA, p_sub_bot, p_sub_top, p_vac, Q]))
    table_colors = np.transpose(
        np.array([p_MA / p_MA[0], p_MS / p_MS[0], p_SA / p_SA[0],
                  p_sub_bot / p_sub_bot[0],
                  p_sub_top / p_sub_top[0],
                  p_vac / p_vac[0], Q / Q[0]])) - 0.5
    colours = plt.cm.bwr(table_colors)
    table_p_ratio = np.around(table_p_ratio, decimals=4)

    fig, ax = plt.subplots()
    ax.set_axis_off()
    table = ax.table(
        cellText=table_p_ratio,
        rowLabels=names,
        colLabels=['p MA', 'p MS', 'p SA', 'p sub bot', 'p sub top', 'p vac',
                   'Q'],
        cellLoc='center',
        loc='upper left',
        cellColours=colours)
    project_name = 'overall view'
    ax.set_title(project_name,
                 fontweight="bold")

    plt.savefig(project_name + '.png', dpi=300, bbox_inches='tight',
                pad_inches=0)
    plt.close()

    for domain in ['p_MA', 'p_MS', 'p_SA', 'p_sub_bot', 'p_sub_top', 'p_vac',
                   'Q']:
        exec(f"p_grid = np.around(np.reshape({domain},[-1,3]), decimals = 4)")
        c_grid = p_grid / p_grid[0, 0]

        fig, ax = plt.subplots()
        ax.set_axis_off()
        table = ax.table(
            cellText=p_grid,
            rowLabels=['qb gap = 10', 'qb gap = 20', 'qb gap = 30'],
            colLabels=['cp gap = 10', 'cp gap = 20', 'cp gap = 30'],
            cellLoc='center',
            loc='upper left',
            cellColours=plt.cm.bwr(c_grid - 0.5))
        project_name = 'p ratio for ' + domain
        ax.set_title(project_name,
                     fontweight="bold")

        plt.savefig(project_name + '.png', dpi=300, bbox_inches='tight',
                    pad_inches=0)
        plt.close()


def analyse_eigen_frequency(
        project
):
    eigen_mode = pd.read_csv("eigen_mode_for_" + project + ".csv")

    thickness = list(np.array(eigen_mode[eigen_mode.columns[0]]))

    thickness_sorted = []
    for elem in thickness:
        if not elem in thickness_sorted:
            thickness_sorted.append(elem)

    sweep_point = len(thickness_sorted)

    freq = np.array(eigen_mode[eigen_mode.columns[2]])
    freq = np.reshape(freq, [sweep_point, -1])

    final_freq = []
    for i in range(sweep_point):
        freq_per_pass = freq[i]
        freq_per_pass = [x for x in freq_per_pass if str(x) != "nan"]
        final_freq.append(freq_per_pass[-1] * 1e-9)

    plt.plot(thickness_sorted, final_freq, 'rx', label="numerical simulation",
             zorder=100)

    from sklearn.linear_model import HuberRegressor

    huber = HuberRegressor(alpha=0.0, epsilon=1.35)
    huber.fit(np.reshape(np.array(thickness_sorted), [sweep_point, -1]),
              final_freq)
    coef_ = huber.coef_ * thickness_sorted + huber.intercept_
    plt.plot(thickness_sorted, coef_, label='Huber regression', zorder=20)

    selected_thickness = []
    final_freq_outiler = []
    index_outliers = []
    for i in range(sweep_point):
        if abs(final_freq[i] - coef_[i]) / coef_[i] * 100 > 0.08:
            selected_thickness.append(thickness_sorted[i])
            final_freq_outiler.append(final_freq[i])
            index_outliers.append(i)

    plt.plot(selected_thickness, final_freq_outiler, 'bs', label='outliers',
             zorder=50)

    plt.xlabel("thickness [um]")
    plt.ylabel("frequency [GHz]")
    plt.legend()
    plt.savefig('freq_plot_outliers' + project + '.png', dpi=200)
    plt.close()


def analyse_p_ratio(
        project,
        dielectric_materials,
        exec_option,
        root_of_variation_name):

    p_ratio_data = pd.read_csv("p_ratio_for_" + project + ".csv")
    thickness = list(np.array(p_ratio_data[p_ratio_data.columns[0]]))

    thickness_sorted = []
    for elem in thickness:
        if elem not in thickness_sorted:
            thickness_sorted.append(elem)

    sweep_point = len(thickness_sorted)

    p_ratio_dicts = {}
    for i in range(len(p_ratio_data.columns) - 2):
        name_dielectric = p_ratio_data.columns[i + 2].replace(
            "ExprCache(", ""
        ).replace(
            ")", ""
        ).replace(
            "[]", ""
        ).replace(
            " ", ""
        ).replace(
            "1", "")

        p_ratio_dielectric = np.array(p_ratio_data[p_ratio_data.columns[i + 2]])

        p_ratio_dielectric = np.reshape(
            p_ratio_dielectric,
            [sweep_point, -1])

        p_ratio = []
        thickness_not_nan = []

        for j in range(sweep_point):
            p_ratio_diel_vs_thickness = p_ratio_dielectric[j]
            p_ratio_diel_vs_thickness = [x for x in
                                         p_ratio_diel_vs_thickness if
                                         str(x) != 'nan']

            if len(p_ratio_diel_vs_thickness) > 0:
                p_ratio.append(p_ratio_diel_vs_thickness[-1])
                thickness_not_nan.append(thickness_sorted[j])

        p_ratio_dicts.update({name_dielectric: {
            'thickness_not_nan': thickness_not_nan,
            'p_ratio': p_ratio}})

    fig, axs_0 = plt.subplots(2, 3, figsize=(15, 10))

    fitted_p_ratio = []
    Q_inv = 0
    for index, dielectric_material in enumerate(dielectric_materials):
        if (dielectric_material['final_name'] == 'MA' or
                dielectric_material['final_name'] == 'MS'):
            name_diel_mat = dielectric_material['final_name'] + '_O'
            adjust_coef = 10 / dielectric_material['epsilon_r']
        else:
            name_diel_mat = dielectric_material['final_name']
            adjust_coef = 1

        p_ratio_dict = p_ratio_dicts['p_' + name_diel_mat]
        x = p_ratio_dict['thickness_not_nan']
        y = np.array(p_ratio_dict['p_ratio']) * adjust_coef
        axs = axs_0[index // 3, index % 3]
        axs.plot(x, y, 'rx')

        huber = HuberRegressor(alpha=0.0, epsilon=1.35)
        huber.fit(np.reshape(np.array(x), [len(x), -1]), y)
        coef_ = huber.coef_ * x + huber.intercept_
        axs.plot(x, coef_, label='Huber regression', zorder=20)
        axs.set_ylim((coef_[0], coef_[-1]))
        axs.set_xlabel("thickness [um]")
        axs.set_title('p_' + dielectric_material['final_name'] + '[%]')

        if dielectric_material['layer_thickness'] != 0:
            losses = (dielectric_material['layer_thickness'] *
                      huber.coef_ * dielectric_material['loss_tangent'])
        else:
            losses = (huber.intercept_ * dielectric_material['loss_tangent'])
        Q_inv = Q_inv + losses
        fitted_p_ratio.append({
            'name': dielectric_material['final_name'],
            'slope': float(huber.coef_),
            'intercept': float(huber.intercept_),
            'losses': float(losses)})

    if exec_option == 'local':
        saving_address = os.getcwd() + "\\"
    else:
        saving_address = os.getcwd() + "/"

    with open(saving_address +
              f"p_ratio_{project}.json",
              'w') as jsonFile:
        jsonFile.write(json.dumps(fitted_p_ratio, indent=4))

    fig.suptitle(project, fontsize=16)
    plt.savefig('p_ratio_for' + project + '.png', dpi=200)
    plt.close()

    for thin_layer in ['MA', 'MS', 'SA']:
        if root_of_variation_name == 'O2_no_GND':
            plot_grid(2, 1,
                      [thin_layer + '_P',
                       thin_layer + '_O'],
                      p_ratio_dicts,
                      project + thin_layer)
        else:
            plot_grid(2, 2,
                      [thin_layer + '_bot_P',
                       thin_layer + '_bot_O',
                       thin_layer + '_top_P',
                       thin_layer + '_top_O'],
                      p_ratio_dicts,
                      project + thin_layer)

    return p_ratio_dicts


def plot_grid(
        fig_along_x,
        fig_along_y,
        domain_name_list,
        p_ratio_dicts,
        project
):
    fig, axs_0 = plt.subplots(fig_along_x,
                              fig_along_y,
                              figsize=(15, 10))

    for index, domain_name in enumerate(domain_name_list):
        E_domain = p_ratio_dicts['E_' + domain_name]
        E_total = p_ratio_dicts['E_tot']
        x = E_domain['thickness_not_nan']
        y = np.array(E_domain['p_ratio']) / np.array(E_total['p_ratio']) * 100
        axs = axs_0[index // fig_along_x, index % fig_along_y]
        axs.plot(x, y, 'rx')

        from sklearn.linear_model import HuberRegressor

        huber = HuberRegressor(alpha=0.0, epsilon=1.35)
        huber.fit(np.reshape(np.array(x), [len(x), -1]), y)
        coef_ = huber.coef_ * x + huber.intercept_
        axs.plot(x, coef_, label='Huber regression', zorder=20)
        # axs.set_ylim((coef_[0], coef_[-1]))
        axs.set_xlabel("thickness [um]")
        axs.set_title('p_' + domain_name + '[%]')

    fig.suptitle(project, fontsize=16)
    plt.savefig('p_ratio_O_P_for' + project + '.png', dpi=200)
    plt.close()
