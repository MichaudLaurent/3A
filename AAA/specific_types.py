from typing import Union, List, TypedDict


class DielectricMaterial(TypedDict):
    """ Dictionary of the dielectric properties of a material.

    Parameters:
    -----------
    regions: List[str]
        List of the regions corresponding to the material.
    epsilon_r: float
        Relative dielectric permittivity of the material.
    final_name: str
        Final name used for global properties
        like the participation ratio.
    layer_thickness: float
        Thickness in micrometers of the dielectric layer.
        Set to 0 by convention if the dielectric material
        is not a thin lossy layer.
    loss_tangent: float
        Loss tangent of the dielectric material.
    """
    regions: List[str]
    epsilon_r: float
    final_name: str
    layer_thickness: float
    loss_tangent: float


class SimulationResources(TypedDict):
    """ Dictionary specifying the resources to query for an LSF job.

    Parameters:
    -----------
    cores: int
        Core number to use for the job.
    time: str
        Duration of the job specified with the "HH:MM" format.
    RAM: int, default 1 GB.
        Cache memory required for the job.
    scratch: int, optional
        Hard drive memory required for the job (should be specified if
        the job generates more than 250 MB of cache files).
    """
    cores: int
    time: str
    RAM: int
    scratch: Union[int, None]


class VariationParameters(TypedDict):
    """ Dictionary specifying how certain design variables should be
    varied to generate the design variations from the reference project.

    Parameters:
    -----------
    var_name: str
        Name of the HFSS design variable.
    sweep: List[float]
        List specifying the sweep domain of the variable.
    """
    var_name: str
    sweep: List[float]


class VariationParametersListing(TypedDict):
    """ Dictionary containing lists to specify the variation project names,
    the naming order of the variable and the value they assume for
    each project variation.

    Parameters:
    -----------
    project_listing: List[str]
        List of the project variation names.
    variable_order_convention: List[str]
        Convention used for the naming of the project variations.
    variation_values_list: List[List[float]]
        Value assumed by each varied design parameter within each
        project variation.
    """
    project_list: List[str]
    variable_order_convention: List[str]
    variation_values_list: List[List[float]]


class OptimizationVariable(TypedDict):
    """ Optimization variable attributes

    Parameters:
    ----------
    name: str
        Variable name, should be in the design variable list.
    units: str
        Units of the variable, for dimensionless variables,
        use an empty string.
    Min: float
        Minimal value the variable can take during the optimization.
    Max: float
        Maximal value the variable can take during the optimization.
    MinStep: float, optional
        If specified the minimal step size by which the variable is changed
        between two optimization steps.
    MaxStep: float, optional
        If specified the maximal step size by which the variable is changed
        between two optimization steps.
    """
    name: str
    units: str
    Min: float
    Max: float
    MinStep: Union[None, float]
    MaxStep: Union[None, float]
    MinFocus: Union[None, float]
    MaxFocus: Union[None, float]
    starting_point: float


class CMatrixTarget:
    """ Target value for the capacitance matrix of
    an ANSYS Maxwell setup.
    Parameters:
    -----------
    v1 : str
        Name of the first voltage excitation.
    v2 : str
        Name of the second voltage excitation.
    value: str
        Target capacitance matrix value in femto Farad. Typically writen as
        a power '1e-14'. Has to be negative for non-diagonal elements.
    """

    def __init__(self, v1, v2, value):
        self.v1 = v1
        self.v2 = v2
        self.value = value
        self.name = f"Matrix1_C_{v1}_{v2}_1"
        self.displaying_name = f"({v1},{v2})"
        self.expression = f"Matrix1.C({v1},{v2})"


class CMatrixCacheVariable:
    """ Capacitance matrix element used in the Maxwell setup.
    Parameters:
    -----------
    v1 : str
        Name of the first voltage excitation.
    v2 : str
        Name of the second voltage excitation.
    """

    def __init__(self, v1, v2):
        self.v1 = v1
        self.v2 = v2
        self.name = f"Matrix1_C_{v1}_{v2}_1"
        self.expression = f"Matrix1.C({v1},{v2})"


