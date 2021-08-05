from AAA.specific_types import *
from typing import List, Dict, Union
from AAA.helper_functions import get_design_properties_from_text_file


def get_dielectric_materials(
        root_of_variation_name: str) -> List[DielectricMaterial]:
    epsilon_r_Nb2O5 = 33
    epsilon_r_SiO2 = 4.5
    epsilon_r_Si = 11.45

    MA_thickness = 5  # nm
    MS_thickness = 2  # nm
    SA_thickness = 3  # nm

    MA_loss_tangent = 4.7e-2
    MS_loss_tangent = 1.3e-2
    SA_loss_tangent = 7.1e-4
    Si_loss_tangent = 1.2e-7

    if root_of_variation_name in ['O1_GND', 'O1_no_GND']:

        return [
            {'regions': ['MA_bot', 'MA_top'],
             'epsilon_r': epsilon_r_Nb2O5,
             'final_name': 'MA',
             'layer_thickness': MA_thickness,
             'loss_tangent': MA_loss_tangent},

            {'regions': ['SA_bot', 'SA_top'],
             'epsilon_r': epsilon_r_SiO2,
             'final_name': 'SA',
             'layer_thickness': SA_thickness,
             'loss_tangent': SA_loss_tangent},

            {'regions': ['MS_bot', 'MS_top'],
             'epsilon_r': epsilon_r_Si,
             'final_name': 'MS',
             'layer_thickness': MS_thickness,
             'loss_tangent': MS_loss_tangent},

            {'regions': ['sub_bot'],
             'epsilon_r': epsilon_r_Si,
             'final_name': 'sub_bot',
             'layer_thickness': 0,
             'loss_tangent': Si_loss_tangent},

            {'regions': ['sub_top'],
             'epsilon_r': epsilon_r_Si,
             'final_name': 'sub_top',
             'layer_thickness': 0,
             'loss_tangent': Si_loss_tangent},

            {'regions': ['Region'],
             'epsilon_r': 1,
             'final_name': 'vac',
             'layer_thickness': 0,
             'loss_tangent': 0},
        ]

    elif root_of_variation_name == 'O2_no_GND':

        return [
            {'regions': ['MA_top'],
             'epsilon_r': epsilon_r_Nb2O5,
             'final_name': 'MA',
             'layer_thickness': MA_thickness,
             'loss_tangent': MA_loss_tangent},

            {'regions': ['SA_bot', 'SA_top'],
             'epsilon_r': epsilon_r_SiO2,
             'final_name': 'SA',
             'layer_thickness': SA_thickness,
             'loss_tangent': SA_loss_tangent},

            {'regions': ['MS_top'],
             'epsilon_r': epsilon_r_Si,
             'final_name': 'MS',
             'layer_thickness': MS_thickness,
             'loss_tangent': MS_loss_tangent},

            {'regions': ['sub_bot'],
             'epsilon_r': epsilon_r_Si,
             'final_name': 'sub_bot',
             'layer_thickness': 0,
             'loss_tangent': Si_loss_tangent},

            {'regions': ['sub_top'],
             'epsilon_r': epsilon_r_Si,
             'final_name': 'sub_top',
             'layer_thickness': 0,
             'loss_tangent': Si_loss_tangent},

            {'regions': ['Region'],
             'epsilon_r': 1,
             'final_name': 'vac',
             'layer_thickness': 0,
             'loss_tangent': 0},
        ]

    elif root_of_variation_name == 'O2_GND':

        return [
            {'regions': ['MA_bot', 'MA_top'],
             'epsilon_r': epsilon_r_Nb2O5,
             'final_name': 'MA',
             'layer_thickness': MA_thickness,
             'loss_tangent': MA_loss_tangent},

            {'regions': ['SA_top'],
             'epsilon_r': epsilon_r_SiO2,
             'final_name': 'SA',
             'layer_thickness': SA_thickness,
             'loss_tangent': SA_loss_tangent},

            {'regions': ['MS_top'],
             'epsilon_r': epsilon_r_Si,
             'final_name': 'MS',
             'layer_thickness': MS_thickness,
             'loss_tangent': MS_loss_tangent},

            {'regions': ['sub_bot'],
             'epsilon_r': epsilon_r_Si,
             'final_name': 'sub_bot',
             'layer_thickness': 0,
             'loss_tangent': Si_loss_tangent},

            {'regions': ['sub_top'],
             'epsilon_r': epsilon_r_Si,
             'final_name': 'sub_top',
             'layer_thickness': 0,
             'loss_tangent': Si_loss_tangent},

            {'regions': ['Region'],
             'epsilon_r': 1,
             'final_name': 'vac',
             'layer_thickness': 0,
             'loss_tangent': 0},
        ]
    else:
        raise Exception(f"Root of variation name: "
                        f"{root_of_variation_name} not handled ")


def get_resource_dicts(dummy_test: bool) -> Dict[str, SimulationResources]:
    """ Query different sets of resources depending on the nature of the run.
    """
    resources_script = SimulationResources(
        cores=1,
        time="0:15",
        RAM=5000,
        scratch=None)

    if dummy_test:
        resources_optimization = SimulationResources(
            cores=1,
            time="00:15",
            RAM=5000,
            scratch=1000)

        resources_sweep = SimulationResources(
            cores=1,
            time="0:15",
            RAM=5000,
            scratch=2000)

    else:
        resources_optimization = SimulationResources(
            cores=1,
            time="20:00",
            RAM=5000,
            scratch=10000)

        cores_for_sweep = 5

        resources_sweep = SimulationResources(
            cores=cores_for_sweep,
            time="10:00",
            RAM=6400,
            scratch=5000 * cores_for_sweep)

    return {"script": resources_script,
            "optimization":
                resources_optimization,
            "sweep": resources_sweep}


def get_modify_hfss_setup_args(
        dummy_test: bool) -> Dict[str, Union[int, float]]:
    if dummy_test:
        return {
            "minimum_passes": 1,
            "maximum_passes": 2,
            "sweep_points": 1,
            "minimum_converged_passes": 1}

    else:
        return {
            "sweep_start": 0.1,
            "sweep_end": 0.6,
            "sweep_points": 10,
            "minimum_passes": 5,
            "maximum_passes": 24,
            "minimum_converged_passes": 2,
            "max_relative_change": 5}


def get_designs_properties(root_of_variation_name: str) -> Dict[str, List[str]]:
    if root_of_variation_name in ['O1_GND', 'O1_no_GND',
                                  'O2_GND', 'O2_no_GND']:
        return {
            'HFSS': get_design_properties_from_text_file(
                text_file_name=f"{root_of_variation_name}_hfss_design_properties.txt",
                sub_folder="prop_files"),
            'Maxwell': get_design_properties_from_text_file(
                text_file_name=f"{root_of_variation_name}_maxwell_design_properties.txt",
                sub_folder="prop_files")}
    else:
        raise Exception(f"Root of variation name: "
                        f"{root_of_variation_name} not handled ")


def get_optimization_variables(root_of_variation_name: str) -> List[OptimizationVariable]:
    """ Set the optimization variable for the Maxwell optimization.
    """

    cp_alpha = OptimizationVariable(
        name='cp_alpha',
        units='',
        Min=0.2,
        Max=0.8,
        MinStep=0.008,
        MaxStep=0.08,
        MinFocus=0.2,
        MaxFocus=0.8,
        starting_point=0.5)

    cp_angle = OptimizationVariable(
        name='cp_angle',
        units='deg',
        Min=30,
        Max=60,
        MinStep=0.5,
        MaxStep=4,
        MinFocus=30,
        MaxFocus=60,
        starting_point=45)

    qb_r_delta = OptimizationVariable(
        name='qb_r_delta',
        units='um',
        Min=40,
        Max=300,
        MinStep=1,
        MaxStep=30,
        MinFocus=40,
        MaxFocus=300,
        starting_point=150)

    ro_r = OptimizationVariable(
        name='ro_r',
        units='um',
        Min=20,
        Max=80,
        MinStep=0.5,
        MaxStep=30,
        MinFocus=20,
        MaxFocus=80,
        starting_point=30)
    if root_of_variation_name in ['O1_GND', 'O1_no_GND']:
        return [cp_alpha, qb_r_delta, ro_r]
    elif root_of_variation_name in ['O2_GND', 'O2_no_GND']:
        return [cp_alpha, cp_angle, qb_r_delta]
    else:
        raise Exception(f"Root of variation name: "
                        f"{root_of_variation_name} not handled ")


def get_optimization_targets(root_of_variation_name: str) -> List[CMatrixTarget]:
    """ Set to objectives of the Maxwell optimization.
    """
    c_sum = CMatrixTarget(v1='V_qb',
                          v2='V_qb',
                          value='1.1e-13')
    c_coupler = CMatrixTarget(v1='V_qb',
                              v2='V_cp1',
                              value='-1e-14')
    c_ro = CMatrixTarget(v1='V_qb',
                         v2='V_ro',
                         value='-1e-14')

    if root_of_variation_name in ['O1_GND', 'O1_no_GND']:
        return [c_sum, c_coupler, c_ro]
    elif root_of_variation_name in ['O2_GND', 'O2_no_GND']:
        return [c_sum, c_coupler]
    else:
        raise Exception(f"Root of variation name: "
                        f"{root_of_variation_name} not handled ")


def get_c_matrix_cache_variables(
        root_of_variation_name: str) -> List[CMatrixCacheVariable]:
    """ Defines the capacitance matrix to be used as cache variables in the
    Maxwell setup."""

    if root_of_variation_name in ['O1_GND', 'O1_no_GND',
                                  'O2_GND', 'O2_no_GND']:
        qb_qb = CMatrixCacheVariable(v1='V_qb', v2='V_qb')
        qb_cp1 = CMatrixCacheVariable(v1='V_qb', v2='V_cp1')
        qb_cp2 = CMatrixCacheVariable(v1='V_qb', v2='V_cp2')
        qb_cp3 = CMatrixCacheVariable(v1='V_qb', v2='V_cp3')
        qb_cp4 = CMatrixCacheVariable(v1='V_qb', v2='V_cp4')
        qb_ro = CMatrixCacheVariable(v1='V_qb', v2='V_ro')
        return [qb_qb, qb_cp1, qb_cp2, qb_cp3, qb_cp4, qb_ro]
    else:
        raise Exception(f"Root of variation name: "
                        f"{root_of_variation_name} not handled ")
