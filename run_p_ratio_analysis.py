#!/usr/bin/env python

import sys

from AAA.user_dependent_utility_functions import *

from AAA.p_ratio_analysis_class import PRatioAnalysis

if len(sys.argv) > 1:
    exec_option = sys.argv[1]
else:
    exec_option = 'local'

if len(sys.argv) > 2:
    root_of_variation_name = sys.argv[2]
else:
    root_of_variation_name = 'O2'

dummy_test = False

resource_dicts = get_resource_dicts(dummy_test=dummy_test)

designs_properties = get_designs_properties(root_of_variation_name)

cartesian_var_param = [
    VariationParameters(var_name='qb_gap', sweep=[20]),
    VariationParameters(var_name='cp_gap', sweep=[20])]

# Example of a VariationParametersListing object
list_var_param = VariationParametersListing(
    project_list=[f"{root_of_variation_name}_qb_gap_25_cp_gap_25"],
    variable_order_convention=['qb_gap', 'cp_gap'],
    variation_values_list=[[25, 25]])

p_ratio_setup = PRatioAnalysis(
    exec_option=exec_option,
    root_of_variation_name=root_of_variation_name,
    reference_project_name='simple_job',
    reference_maxwell_design_name='maxwell_design',
    reference_maxwell_design_properties=designs_properties['Maxwell'],
    maxwell_cache_variables=get_c_matrix_cache_variables(root_of_variation_name),
    maxwell_optimization_variables=get_optimization_variables(root_of_variation_name),
    maxwell_target_parameters=get_optimization_targets(root_of_variation_name),
    reference_hfss_design_name='hfss_design',
    reference_hfss_design_properties=designs_properties['HFSS'],
    dielectric_materials=get_dielectric_materials(root_of_variation_name),
    resources_requested_script=resource_dicts['script'],
    resources_requested_optimization=resource_dicts['optimization'],
    resources_requested_sweep=resource_dicts['sweep'],
    ansys_exec_address=r'"C:\Program '
                       r'Files\AnsysEM\AnsysEM19.5\Win64\ansysedt.exe" ',
    list_var_param=cartesian_var_param)

p_ratio_setup.create_maxwell_setup(opti_max_iter=30)
p_ratio_setup.create_hfss_setup(**get_modify_hfss_setup_args(dummy_test=dummy_test))
p_ratio_setup.create_design_variation()
p_ratio_setup.run_preparation_task()

p_ratio_setup.create_p_ratio_tasks()
p_ratio_setup.run_p_ratio_tasks()
