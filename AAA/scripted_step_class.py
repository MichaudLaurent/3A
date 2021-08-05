from .vbs_script_class import VBScript
import warnings
from .task_class import *


class ScriptedStep(Step):
    def __init__(self,
                 common_name,
                 display_name,
                 exec_option: str,
                 resources_requested: SimulationResources,
                 status: LogText,
                 ansys_exec_address: str = None,
                 sub_folder: str = None,
                 move_to_log_file_dir: bool = True):
        """ Class to structure the writing of visual basic script
        with ANSYS OOP convention sanity tools.

        Parameters
        ----------
        common_name : str
            Root name used to name the .vbs script and the bash file.
        exec_option : str
            Type of execution, either 'local' or 'euler'.
        resources_requested : SimulationResources
            LSF resources required to run the script.
            Further details available in the SimulationResources class
            definition.
        status : LogText
            Logger object used to keep track of the analysis progress.
        ansys_exec_address : str
            Address of the ANSYS executable path. Required only for 'local'
            execution option.
        sub_folder : str, optional
            If specified, the script is stored within this sub folder.
        """
        self.common_name = common_name
        self.script_name = f"{common_name}.vbs"
        self.bash_file_name = f"{common_name}.sh"
        self.exec_option = exec_option
        self.ansys_exec_address = ansys_exec_address
        self.resources_requested = resources_requested
        self.status = status

        if sub_folder is not None:
            self.f_stream = open(os.path.join(
                os.getcwd(), "",
                sub_folder, "",
                self.script_name), "w")
        else:
            self.f_stream = open(self.script_name, "w")
        self.indentation_level = 0

        Step.__init__(
            self,
            name=common_name,
            display_name=display_name,
            step_type='Script',
            bash_file_name=self.bash_file_name,
            resources_requested=resources_requested,
            move_to_log_file_dir=move_to_log_file_dir,
            script_name=self.script_name,
            sub_folder=sub_folder)

        self.o_project_initialized = False
        self.o_design_initialized = False
        self.o_module_initialized = False
        self.o_project_set = False
        self.o_design_set = False
        self.o_design_copied = False
        self.o_module_set = False
        self.o_project_name = None
        self.o_design_name = None
        self.o_module_name = None
        self.design_quantities = []
        self.script_variables = []
        self.loaded_quantities = 0

        self.initialize_desktop()

    def write(self, string_to_write: str) -> None:
        """Write string through the output stream.
        Parameters
        ----------
        string_to_write : str
            String added to the file.
        """
        if self.indentation_level > 0:
            for i in range(self.indentation_level):
                self.f_stream.write('\t')
        self.f_stream.write(string_to_write)

    def close(self) -> None:
        """ Close the output stream.
        """
        self.f_stream.close()

    def initialize_desktop(self) -> None:
        """ Initialize oAnsoftApp and oDesktop.

        """
        self.write('Dim oAnsoftApp\n')
        self.write('Dim oDesktop\n')
        self.write('Set oAnsoftApp = '
                   'CreateObject("Ansoft.ElectronicsDesktop")\n')
        self.write('Set oDesktop = oAnsoftApp.GetAppDesktop()\n')
        self.write('oDesktop.RestoreWindow\n')

    def init_project(self):
        """ Initialize oProject variable."""
        self.write('Dim oProject \n')
        self.o_project_initialized = True

    def set_project(
            self,
            project_name: str) -> None:
        """ Ensure oProject is initialized and link it to the specified project.

        Parameters
        ----------
        project_name: str
            Name of the ANSYS project (without .aedt extension).
        """

        if not self.o_project_initialized:
            self.init_project()

        self.check_var_or_str(project_name)

        self.write(f"Set oProject = "
                   f"oDesktop.SetActiveProject({project_name})\n")
        self.o_project_set = True
        # store the project_name without the vbs string characters.
        self.o_project_name = project_name.replace('"', '')

    def new_project(self,
                    path_name: str):
        """ Create a new project.

        Parameters
        ----------
        path_name : str
            Absolute path of the new project finishing with the desired
            new project name. Should start and finish by '"' to write a string
            in the .vbs convention.
        """
        self.check_var_or_str(path_name)

        self.write('Set oProject = oDesktop.NewProject\n')
        self.write(f"oProject.Rename {path_name}, true\n")

    def check_var_or_str(self,
                         variable_name):
        """ Check if a variable name is a vbs string or a predefined variable in
        the script.

        Parameters
        ----------
        variable_name : str
            Variable name.
        """

        if (not check_is_vbs_string(variable_name) and
                not variable_in_list(variable_name, self.script_variables)):
            raise Exception(f"Variable : {variable_name} not a vbs string "
                            f"nor a predefined variable.")

    def init_design(self):
        """ Initialize the oDesign variable"""
        self.write('Dim oDesign \n')
        self.o_design_initialized = True

    def set_design(
            self,
            design_name: str) -> None:
        """ Ensure oDesign is initialized and link it to the specified design.

        Parameters
        ----------
        design_name: str
            Name of the ANSYS design.
        """

        if not self.o_project_set:
            raise Exception("oProject not set.")

        if not self.o_design_initialized:
            self.init_design()

        self.check_var_or_str(design_name)

        self.write(f"Set oDesign = oProject.SetActiveDesign({design_name})\n")

        self.o_design_set = True

    def copy_design(self,
                    design_name: str):
        """ Copy the specified design.

        Parameters
        ----------
        design_name : str
            Name of the design to copy.
        """
        if not self.o_project_set:
            raise Exception("oProject not set")

        self.check_var_or_str(design_name)

        self.write(f"oProject.CopyDesign {design_name}\n")
        self.o_design_copied = True

    def paste_design(self,
                     multiple_copies: bool = False):
        """ Past a copied design.

        Parameters
        ----------
        multiple_copies : bool, default it False.
            If True, the past_design method can be called many times.
        """
        if not self.o_design_copied:
            raise Exception('No oDesign previously copied.')
        self.write('oProject.Paste\n')

        if not multiple_copies:
            self.o_design_copied = False

    def assign_design_variable_value_to_script_variable(
            self,
            design_variable_name: str,
            script_variable_name: str,
            design_parameter_list: List[str]):
        if script_variable_name not in self.script_variables:
            raise Exception("Script variable not initialized.")
        if design_variable_name not in design_parameter_list:
            raise Exception("Design parameter not valid.")
        self.write(script_variable_name + '= oDesign.GetVariableValue("' +
                   design_variable_name + '")\n')

    def change_design_property(self,
                               property_name,
                               property_value,
                               append_units,
                               property_unit: str = '"um"', ):
        """ Change the value of a design property.
        # TODO Make the method more robust (check property name is in design properties).
        Parameters
        ----------
        property_name : str
            Property name.
        property_value : str
            Property value.
        append_units : bool
            If true, the property units are appended to the property value.
            This value should be False if the property is obtained through the
            'assign_design_variable_value_to_script_variable' method. (ANSYS will
            automatically append the units to the value of the property).
            This value should be True if the user set manually a script
            variable to be 'x', such that the command mentions 'x [unit]'.
        property_unit : str, default is '"um"'
            Unit of the property.
        """
        self.check_var_or_str(property_name)
        self.check_var_or_str(property_value)
        self.check_var_or_str(property_unit)

        if append_units:
            unit_str = '&' + property_unit
        else:
            unit_str = ''

        self.write(
            'oDesign.ChangeProperty Array("NAME:AllTabs",' +
            ' Array("NAME:LocalVariableTab",' +
            ' Array("NAME:PropServers",  _\n')
        self.write(
            '"LocalVariables"), Array("NAME:ChangedProps",' +
            'Array("NAME:" & ' + property_name + ', ' +
            ' "Value:=", ' + property_value + unit_str + '))))\n')

    def set_module(self,
                   module_name: str) -> None:
        """ Ensure oModule is initialized and like it to a specified module.

        Parameters
        ----------
        module_name : str
            Name of the module to be set.
        """

        if not self.o_design_set:
            raise Exception("Design not set.")

        if not self.o_module_initialized:
            self.write('Dim oModule\n')
            self.o_module_initialized = True

        self.check_var_or_str(module_name)

        self.write(f"Set oModule = oDesign.GetModule({module_name})\n")

        # Store the module name without the vbs string characters.
        self.o_module_name = module_name.replace('"', '')
        self.o_module_set = True

    def delete_all_analysis_module(self):
        """ Delete all analysis module within the activated design."""
        if not self.o_module_set:
            raise Exception("Module not set.")
        self.write('oModule.DeleteSetups oModule.GetSetups()\n')

    def delete_all_optimetrics_module(self):
        """ Delete all Optimetrics module within the activated design"""
        if self.o_module_name != 'Optimetrics':
            raise Exception("Module not set to Optimetrics.")
        self.write('For each name in oModule.GetSetupNames()\n')
        self.write('\t oModule.DeleteSetups name\n')
        self.write('Next\n')

    def clear_fields_reporter(self):
        """ Clear named expression list and calculation stack.
        """
        if self.o_module_name != 'FieldsReporter':
            raise Exception("FieldsReporter not activated.")

        self.write('oModule.ClearAllNamedExpr\n')
        self.write('oModule.CalcStack "clear"\n')

    def create_setup_report(
            self,
            design_type: str,
            csv_file_name: str,
            project_properties: List[str],
            cache_variables: List[Union[CMatrixCacheVariable, str]],
            sub_folder: str,
            setup_name: str = 'Setup1') -> None:
        """ Create a CSV file with the cache variables of the setup.
        Parameters
        ----------
        design_type : str
            Either 'HFSS' or 'Maxwell'.
        setup_name : str
            Name of the setup used for the design simulation.
        csv_file_name : str
            Name of the CSV file generated to store the cache variables.
        project_properties : List[str]
            List containing the name of all design variables.
        cache_variables : List[str]
            List containing a selection of cache variables to export.
            The user should ensure that these variables were assigned to
            the setup.
        sub_folder : str
            Sub folder where the .csv file is placed.
        """

        if not self.o_design_set:
            raise Exception("oDesign has to be set "
                            "before creating a report.")

        self.set_module(module_name='"ReportSetup"')

        if design_type == 'HFSS':
            expression_cache_name = 'Eigenmode Parameters'
        elif design_type == 'Maxwell':
            expression_cache_name = 'Electrostatic'
        else:
            raise Exception(f"Design type: {design_type} not handled.")

        self.write('oModule.CreateReport ')
        self.write('"Expression Cache", '
                   '"' + expression_cache_name + '",  _\n')

        self.write('"Rectangular Plot", "' +
                   setup_name + ' : AdaptivePass", Array(), _\n')
        self.write('Array("Pass:=", Array("All"),_\n')

        # ensure that there is no duplicate in the list.
        project_properties = list(set(project_properties))

        for parameter in project_properties:
            if parameter != project_properties[-1]:
                self.write('"' + parameter + ':=", Array("All"),_\n')
            else:
                self.write('"' + parameter + ':=", Array("All")_\n')
        self.write('),_\n')
        self.write(' Array("X Component:=", "Pass",_\n')
        self.write('"Y Component:=", Array(_\n')

        for cache_variable in cache_variables:
            if isinstance(cache_variable, CMatrixCacheVariable):
                if cache_variable != cache_variables[-1]:
                    self.write('"ExprCache(' + cache_variable.name + ')",_\n')
                else:
                    self.write('"ExprCache(' + cache_variable.name + ')"_\n')
            else:
                if cache_variable != cache_variables[-1]:
                    self.write('"ExprCache(' + cache_variable + '1)",_\n')
                else:
                    self.write('"ExprCache(' + cache_variable + '1)"_\n')

        self.write(')), Array()\n')
        self.write('\n')
        self.write('oModule.ExportToFile "Expression Cache",  _\n')
        self.write('  "' + get_path_in_ansys_convention() +
                   f"/{sub_folder}/" + csv_file_name + '", false\n')

    def add_cache_item(
            self,
            design_type,
            variable_name: str = None,
            c_matrix_cache_variable: CMatrixCacheVariable = None,
            max_relative_change: float = None,
            last_item: bool = False, ) -> None:
        """ Add a cache item to an analysis setup.

        Parameters
        ----------
        design_type : str
            Design setup type where the cache item is added. Either 'Maxwell' or
            'HFSS'.
        variable_name : str
            Name of the variable to add to the cache of the design setup. Each
            time the setup is solve, the variable is evaluated and stored.
        c_matrix_cache_variable : CMatrixCacheVariable
            Cache variable linked to a Maxwell capacitance matrix.
        max_relative_change : float, optional
            If specified, the variable will be used to control the convergence of
            the setup. Mesh refinement cycle will continue until the relative
            change of this variable falls below the specified threshold.
        last_item : bool
            Indicate is this is the last cache item to be added to the setup.
        """
        if self.o_module_name != 'AnalysisSetup':
            raise Exception("AnalysisSetup module not loaded.")

        if variable_name is not None:
            title = f"{variable_name}1"
            expression = variable_name
        elif c_matrix_cache_variable is not None:
            title = c_matrix_cache_variable.name
            expression = c_matrix_cache_variable.expression
        else:
            raise Exception(f"Please specify a 'variable_name' or a"
                            f"'c_matrix_cache_variable'")

        self.write('Array("NAME:CacheItem", "Title:=", "' + title + '", _ \n')
        self.write('"Expression:=", "' + expression + '",  _ \n')

        if max_relative_change is not None:
            self.write('"Intrinsics:=", "", "IsConvergence:=", true, _ \n')
            self.write('"UseRelativeConvergence:=", 1 , _ \n')
            self.write('"MaxConvergenceDelta:=", ' +
                       str(max_relative_change) + ', _ \n')
            self.write('"MaxConvergeValue:=", "0.01", _ \n')
        else:
            self.write('"Intrinsics:=", "",_ \n')

        if design_type == 'HFSS':
            report_type = 'Fields'
        elif design_type == 'Maxwell':
            report_type = 'Electrostatic'
        else:
            raise Exception(f"Design type: {design_type} not handled.")

        self.write('"ReportType:=", "' + report_type + '", _ \n')
        if last_item:
            self.write('Array("NAME:ExpressionContext"))_ \n')
        else:
            self.write('Array("NAME:ExpressionContext")),_ \n')

    def create_hfss_setup(
            self,
            setup_name: str = "Setup1",
            max_delta_freq: float = 1,
            min_freq: float = 3,
            num_modes: int = 1,
            percent_refinement: float = 30,
            minimum_converged_passes: int = 5,
            maximum_passes: int = 40,
            minimum_passes: int = 8,
            max_relative_change: float = 2,
            cache_variables: List[str] = None,
            convergence_cache_variables: List[str] = None) -> None:
        """ Delete all preexisting setup and create an
        eigenmode HFSS analysis setup.
        Parameters
        ----------
        setup_name : str, default is "Setup1"
            Name of the design analysis setup.
        max_delta_freq : str, default is 1 (%)
            Maximum relative change of the design eigen frequency between
            two successive mesh refinement iterations.
        min_freq : float, default is 3 (GHz)
            Lower bound for the system eigen frequency in giga Hertz of the system.
            Helps ANSYS to generate a well behaving mesh. ANSYS suggests by
            default a min_freq value for the setup. The documentation does not
            recommend going below a hundredth of first estimate.
        num_modes : int, default is 1
            Number of eigen modes to consider for the simulation (and the
            estimation of the convergence criterion).
        percent_refinement : float, default is 30 (%)
            Relative amount in percent of vertices added to the mesh during a
            refinement step.
        minimum_converged_passes : int, default is 5
            Minimum amount of converged passes to consider before validating the
            convergence. Helpful against false convergence errors, the relative
            change of the eigen frequency and the cached variables are subjected
            to noise due to numerical imprecision and partial fulfillment of
            the continuity equations.
        maximum_passes : int, default is 40
            Maximum amount of mesh refinement steps. Helpful to prevent
            the solving process from exceeding to RAM limit.
        minimum_passes : int, default is 8
            Minimum amount of mesh refinement steps. Helpful against noisy
            behaviors occurring at the beginning of the mesh refinement.
        max_relative_change : float, default is 2 (%)
            Maximum relative change in percent of the cache variables.
        cache_variables : List[str]
            List of the FieldsReporter variable to add to the setup cache.
        convergence_cache_variables : List[str]
            List of FieldsReporter variables to add to the setup cache and to
            use for the convergence control.
        """

        self.set_module('"AnalysisSetup"')
        self.write('oModule.DeleteSetups oModule.GetSetups()\n')
        self.write('oModule.InsertSetup "HfssEigen", '
                   'Array("NAME:' + setup_name + '", "Enabled:=", true)\n')
        self.write('oModule.EditSetup "' + setup_name + '", _ \n')
        self.write('Array("NAME:' + setup_name + '", _ \n')
        self.write('"MinimumFrequency:=", "' + str(min_freq) + 'GHz", _\n')
        self.write('"NumModes:=",' + str(num_modes) + ', _ \n')
        self.write('"MaxDeltaFreq:=", ' + str(max_delta_freq) + ', _ \n')
        self.write('"ConvergeOnRealFreq:=", false, _ \n')
        self.write('"MaximumPasses:=", ' + str(maximum_passes) + ', _ \n')
        self.write('"MinimumPasses:=", ' + str(minimum_passes) + ', _ \n')
        self.write('"MinimumConvergedPasses:=", ' +
                   str(minimum_converged_passes) + ', _ \n')
        self.write('"PercentRefinement:=", ' + str(percent_refinement) + ', _ \n')
        self.write('"IsEnabled:=", true , _ \n')
        self.write('Array("NAME:MeshLink", "ImportMesh:=", false), _ \n')
        self.write('"BasisOrder:=", -1, "DoLambdaRefine:=", true , _ \n')
        self.write('"DoMaterialLambda:=", true, _ \n')
        self.write('"SetLambdaTarget:=", false, _ \n')
        self.write('"Target:=", 0.4, _ \n')
        self.write('"UseMaxTetIncrease:=", false, _ \n')
        self.write('Array("NAME:ExpressionCache", _ \n')

        for variable in cache_variables:
            self.add_cache_item(design_type='HFSS', variable_name=variable)
        for variable in convergence_cache_variables:
            self.add_cache_item(
                design_type='HFSS',
                variable_name=variable,
                max_relative_change=max_relative_change,
                last_item=variable == convergence_cache_variables[-1])
        self.write('))\n')

    def modify_hfss_sweep_setup(
            self,
            setup_name: str = "Setup1",
            parametric_setup: str = "ParametricSetup1",
            var_to_sweep: str = "lossy_layer_thickness",
            unit_of_var_to_sweep: str = "um",
            sweep_start: float = 0.2,
            sweep_end: float = 0.5,
            sweep_points: int = 5) -> None:
        """ Modify a preexisting HFSS ParametricSetup.

        Parameters
        ----------
        setup_name : str, default is "Setup1"
            Name of the design analysis setup.
        var_to_sweep : str, default is "lossy_layer_thickness"
            Name of the HFSS design variable used for the sweep. Should
            correspond to the thickness of the thin dielectric lossy layers.
        unit_of_var_to_sweep : str, default is "um"
            Units of the variables used for the sweep.
        sweep_start : float, default is 0.2 (um)
            Starting point of the sweep, the unit is given by unit_of_var_to_sweep.
        sweep_end : float, default is 0.5 (um)
            End point of the sweep, the unit is given by unit_of_var_to_sweep.
        sweep_points : int, default if 5
            Point number used for the sweep.
        parametric_setup : str, default is "ParametricSetup1"
            Name of the sweep parametric setup.
        """
        self.set_module('"Optimetrics"')
        self.write('oModule.EditSetup "' + parametric_setup + '", _ \n')
        self.write(
            'Array("NAME:' + parametric_setup + ' ", "IsEnabled:=",true,_\n')
        self.write('Array("NAME:ProdOptiSetupDataV2", "SaveFields:=", true, _\n')
        self.write('"CopyMesh:=", false, _ \n')
        self.write('"SolveWithCopiedMeshOnly:=",true),_\n')
        self.write('Array("NAME:StartingPoint"),_\n')
        self.write('"Sim. Setups:=", Array("' + setup_name + '"),_\n')
        self.write('Array("NAME:Sweeps",_\n')
        self.write('Array("NAME:SweepDefinition",_ \n')
        self.write('"Variable:=", "' + var_to_sweep + '", _\n')
        self.write('"Data:=", "LINC ' +
                   str(sweep_start) + unit_of_var_to_sweep + ' ' +
                   str(sweep_end) + unit_of_var_to_sweep + ' ' +
                   str(sweep_points) + '",_\n')
        self.write('"OffsetF1:=", false,_ \n')
        self.write('"Synchronize:=",0)),_ \n')
        self.write('Array("NAME:Sweep Operations"),_\n')
        self.write('Array("NAME:Goals",_ \n')
        self.write('Array("NAME:Goal", "ReportType:=","Eigenmode Parameters",_\n')
        self.write('"Solution:=", "' + setup_name + ' : LastAdaptive",_ \n')
        self.write('Array("NAME:SimValueContext"), _\n')
        self.write('"Calculation:=", "re(Mode(1))",_\n')
        self.write('"Name:=", "re(Mode(1))", _\n')
        self.write('Array("NAME:Ranges"))))\n')

    def select_variable_for_optimization(
            self,
            variable_name: str,
            for_optimization: bool):
        """ Promote design property to an optimization variable.

        Parameters
        ----------
        variable_name : str
            Variable name, should be defined in the design geometry.
        for_optimization : bool
            If true, the variable will be added to the optimization. This
            can be use to retrograde the status of an optimization variable.
        """
        if not self.o_design_set:
            raise Exception("Design not set.")
        if for_optimization:
            bool_to_str = 'true'
        else:
            bool_to_str = 'false'
        self.write(
            'oDesign.ChangeProperty Array("NAME:AllTabs",'
            ' Array("NAME:LocalVariableTab", '
            'Array("NAME:PropServers", _\n')
        self.write(
            '"LocalVariables"), Array("NAME:ChangedProps", '
            'Array("NAME:' + variable_name + '", ' +
            'Array("NAME:Optimization", "Included:=",' + bool_to_str + ')))))\n')

    def create_maxwell_setup(
            self,
            setup_name: str = 'Setup1',
            percent_error: float = 5,
            minimum_passes: int = 5,
            maximum_passes: int = 30,
            minimum_converged_passes: int = 1,
            percent_refinement: float = 30,
            cache_variables: List[CMatrixCacheVariable] = None,
            max_relative_change: float = 1.5,
            iterative_solver: bool = True,
            relative_residual: float = 1e-6,
            non_linear_residual: float = 1e-3):
        """ Remove all the preexisting setups and create a setup for a Maxwell design.

        Parameters
        ----------
        setup_name : str, default is "Setup1"
            Name of the design analysis setup.
        percent_error : float, default is 5 (%)
            Maximum energy error DeltaE in percent. DeltaE measures how the
            numerical simulation violates the Maxwell equations. An energy is associated
            to the mismatch and divided by the total energy of the system.
        minimum_converged_passes : int, default is 1
            Minimum amount of converged passes to consider before validating the
            convergence. Helpful against false convergence errors, the relative
            change of cached variables are subjected to noise.
        maximum_passes : int, default is 30
            Maximum amount of mesh refinement steps. Helpful to prevent
            the solving process from exceeding to RAM limit.
        minimum_passes : int, default is 5
            Minimum amount of mesh refinement steps. Helpful against noisy
            behaviors occurring at the beginning of the mesh refinement.
        max_relative_change : float, default is 1.5 (%)
            Maximum relative change in percent of the cache variables.
        percent_refinement : float, default is 30 (%)
            Relative amount in percent of vertices added to the mesh during a
            refinement step.
        cache_variables : List[CMatrixCacheVariable]
            List of capacitance matrix elements to be added to the
            cache of the solver.
        iterative_solver : bool, default is True
            Activate iterative solving (rather then direct solving), lowering the
            memory use of the setup.
        relative_residual : float, default is 1e-6
        non_linear_residual : float, default is 1e-3
        """

        if minimum_passes > maximum_passes:
            minimum_passes = maximum_passes
            warnings.warn("Minimum passes larger than maximum passes.")

        self.set_module('"AnalysisSetup"')
        self.delete_all_analysis_module()

        self.write('oModule.InsertSetup "Electrostatic", _\n')
        self.write('Array("NAME:' + setup_name + '", "Enabled:=", true)\n')
        self.write('oModule.EditSetup "' + setup_name + '", _ \n')
        self.write('Array("NAME:' + setup_name + '", "Enabled:=", true,_\n')
        self.write('Array("NAME:MeshLink", "ImportMesh:=", false),_\n')
        self.write('"MaximumPasses:=", ' + str(maximum_passes) + ', _\n')
        self.write('"MinimumPasses:=", ' + str(minimum_passes) + ', _\n')
        self.write('"MinimumConvergedPasses:=", ' + str(minimum_converged_passes) + ', _\n')
        self.write('"PercentRefinement:=", ' + str(percent_refinement) + ', _ \n')
        self.write('"SolveFieldOnly:=", false,_ \n')
        self.write('"PercentError:=", ' + str(percent_error) + ',_ \n')
        self.write('"SolveMatrixAtLast:=", true,_ \n')
        self.write('"PercentError:=", ' + str(percent_error) + ',_ \n')
        if cache_variables is not None:
            self.write('Array("NAME:ExpressionCache",_\n')
            for cache_variable in cache_variables:
                self.add_cache_item(
                    design_type='Maxwell',
                    c_matrix_cache_variable=cache_variable,
                    max_relative_change=max_relative_change,
                    last_item=cache_variable == cache_variables[-1])
            self.write('), ')
        if iterative_solver:
            iterative_solver_bool = 'true'
        else:
            iterative_solver_bool = 'false'

        self.write('"UseIterativeSolver:=", ' + iterative_solver_bool + ', ' +
                   '"RelativeResidual:=", ' + str(relative_residual) + ', ' +
                   '"NonLinearResidual:=", ' + str(non_linear_residual) + ')\n')

    def create_maxwell_optimization_setup(
            self,
            optimization_variables: List[OptimizationVariable],
            c_mat_targets: List[CMatrixTarget],
            maxwell_design_properties: List[str],
            setup_name: str = 'Setup1',
            optimization_setup: str = 'OptimizationSetup1',
            max_iter: int = 50):
        """ Modify a preexisting Maxwell Optimization Setup.

        Parameters
        ----------
        optimization_variables : List[OptimizationVariable]
            List of OptimizationVariable.
            Further details available in the OptimizationVariable class
            definition.
        c_mat_targets : List[CMatrixTarget]
            List of capacitance matrix components to target for the optimization.
            Further details available in the CMatrixTarget class
            definition.
        maxwell_design_properties : List[str]
            List of the properties names in the Maxwell design.
        setup_name : str, default is 'Setup1'
            Setup name.
        optimization_setup : str, default is 'OptimizationSetup1'
            Optimization setup name.
        max_iter : int
            Maximum number of iterations for the optimization.
        """
        for variable in maxwell_design_properties:
            self.select_variable_for_optimization(
                variable_name=variable,
                for_optimization=False)
        for variable in optimization_variables:
            self.select_variable_for_optimization(
                variable_name=variable['name'],
                for_optimization=True)
        self.set_module('"Optimetrics"')
        self.delete_all_optimetrics_module()
        self.write('oModule.InsertSetup "OptiOptimization",_\n')
        self.write('Array("NAME:' + optimization_setup + '", "IsEnabled:=",true, _  \n')
        self.write('Array("NAME:ProdOptiSetupDataV2", _\n')
        self.write('"SaveFields:=", false,_ \n')
        self.write('"CopyMesh:=", false,_\n')
        self.write('"SolveWithCopiedMeshOnly:=",true), _\n')
        self.write('Array("NAME:StartingPoint", _\n')
        for variable in optimization_variables:
            self.write('"' + variable['name'] + ':=", "' +
                       str(variable['starting_point']) +
                       variable['units'] + '"')
            if variable != optimization_variables[-1]:
                self.write(',_\n')
            else:
                self.write('), _\n')
        self.write('"Optimizer:=", "SNLP",_\n')
        self.write('Array("NAME:AnalysisStopOptions",_\n')
        self.write('"StopForNumIteration:=", true, _ \n')
        self.write('"StopForElapsTime:=", false, _ \n')
        self.write('"StopForSlowImprovement:=", false, _ \n')
        self.write('"StopForGrdTolerance:=", false, _\n')
        self.write('"MaxNumIteration:=", ' + str(max_iter) + ',_\n')
        self.write('"MaxSolTimeInSec:=", 3600,_\n')
        self.write('"RelGradientTolerance:=", 0,_\n')
        self.write('"MinNumIteration:=", 10),_ \n')
        self.write('"CostFuncNormType:=", "L2",_ \n')
        self.write('"PriorPSetup:=", "", _\n')
        self.write('"PreSolvePSetup:=", true,_\n')
        self.write('Array("NAME:Variables",_\n')

        for variable in optimization_variables:
            self.write('"' + variable['name'] + ':=",_\n')
            if 'MinFocus' not in variable.keys():
                variable.update({'MinFocus': variable['Min']})
            if 'MaxFocus' not in variable.keys():
                variable.update({'MaxFocus': variable['Max']})
            self.write(
                'Array("i:=", true, '
                '"int:=", false, '
                '"Min:=", "' + str(variable['Min']) + variable['units'] + '", ' +
                '"Max:=", "' + str(variable['Max']) + variable['units'] + '", _ \n ' +
                '"MinStep:=", "' + str(variable['MinStep']) + variable['units'] + '", ' +
                '"MaxStep:=", "' + str(variable['MaxStep']) + variable['units'] + '", _ \n ' +
                '"MinFocus:=", "' + str(variable['MinFocus']) + variable['units'] + '", ' +
                '"MaxFocus:=", "' + str(variable['MaxFocus']) + variable['units'] + '",_ \n' +
                '"UseManufacturableValues:=", "false", '
                '"Level:=", "[' + str(variable['Min']) + ': ' +
                str(variable['Max']) + '] ' + variable['units'] + '")_ \n')
            if variable != optimization_variables[-1]:
                self.write(',_ \n')
            else:
                self.write('), _\n')
        self.write('Array("NAME:LCS"), _ \n')
        self.write('Array("NAME:Goals", _\n')
        for c_mat_target in c_mat_targets:
            self.write('Array("NAME:Goal",_\n')
            self.write('"ReportType:=", "Electrostatic", _\n')
            self.write('"Solution:=","' + setup_name + ' : LastAdaptive", _\n')
            self.write('Array("NAME:SimValueContext"),_\n')
            self.write('"Calculation:=", "' + c_mat_target.expression + '",_\n')
            self.write('"Name:=", "' + c_mat_target.expression + '", _ \n')
            self.write('Array("NAME:Ranges"),_\n')
            self.write('"Condition:=", "==", _\n')
            self.write('Array("NAME:GoalValue", _\n')
            self.write('"GoalValueType:=", "Independent", _ \n')
            self.write('"Format:=", "Real/Imag",_\n')
            self.write('"bG:=", Array("v:=", "[' + c_mat_target.value + ';]")), _ \n')
            self.write('"Weight:=", "[1;]")_\n')
            if c_mat_target != c_mat_targets[-1]:
                self.write(',_\n')
            else:
                self.write('),_\n')
        self.write('"Acceptable_Cost:=", 0, _\n')  # TODO Investigate this setting
        self.write('"Noise:=", 0.0001,_\n')
        self.write('"UpdateDesign:=", false,_\n')
        self.write('"UpdateIteration:=", 5,_\n')
        self.write('"KeepReportAxis:=", true, _\n')
        self.write('"UpdateDesignWhenDone:=", true) \n')

    def load_predefined_quantity(self,
                                 quantity_name: str,
                                 smooth_field: bool = False) -> None:
        """ Load a predefined quantity in the FieldsReporter.
        This only works with ANSYS predefined quantities like the electric
        field 'E'.
        To load an user defined quantity, use *load_named_expression*.

        Parameters
        ----------
        quantity_name : str
            Name of the quantity to be loaded.
        smooth_field : bool, default is False
            If true, the quantity will be smoothed (only works for fields).
        """
        if not self.o_module_set:
            raise Exception("No module set.")

        if self.o_module_name != 'FieldsReporter':
            raise Exception("FieldsReporter not activated.")

        self.write('oModule.EnterQty "' + quantity_name + '"\n')
        if smooth_field:
            self.write('oModule.CalcOp "Smooth"\n')

        self.loaded_quantities += 1

    def export_optimization_results(
            self,
            sub_folder_name: str,
            optimization_setup_name: str = 'OptimizationSetup1'):
        """ Create and export an optimization report.

        Parameters
        ----------
        sub_folder_name : str
            Name of the sub folder to place the .csv report.
        optimization_setup_name : str, default is 'OptimizationSetup1'
            Name of the optimization setup.
        """

        self.write('Set oModule = oDesign.GetModule("Optimetrics")\n')

        self.write('oModule.ExportOptimetricsResult "' + optimization_setup_name + '",  _\n')

        self.write('"' + get_path_in_ansys_convention() +
                   f"/{sub_folder_name}/opti_result_" +
                   self.o_project_name + '.csv"\n')

        self.write('oDesktop.CloseProject "' + self.o_project_name + '"\n')

    def load_named_expression(self,
                              quantity_name: str) -> None:
        """ Load a user defined quantity

        Parameters
        ----------
        quantity_name : str
            Name of the quantity to be loaded.
        """

        if self.o_module_name != 'FieldsReporter':
            raise Exception("FieldsReporter not activated.")

        if quantity_name not in self.design_quantities:
            raise Exception(f"Quantity :{quantity_name} not defined")
        self.write('oModule.CopyNamedExprToStack "' + quantity_name + '"\n')

        self.loaded_quantities += 1

    def create_quantity(self,
                        quantity_name) -> None:
        """ Create a new quantity to the FieldsReporter.

        Parameters
        ----------
        quantity_name : str
            Name of the quantity to be added.
        """
        if self.o_module_name != 'FieldsReporter':
            raise Exception("FieldsReporter not activated.")

        if quantity_name in self.design_quantities:
            raise Warning(f"Quantity : {quantity_name} already added")

        self.write('oModule.AddNamedExpression "' +
                   quantity_name + '", "Fields"\n')
        self.design_quantities.append(quantity_name)
        self.loaded_quantities -= 1

    def load_scalar(self,
                    scalar_value: str):
        """ Load a scalar to the stack.
        Parameters
        ----------
        scalar_value : str
            String representing the scalar value.
        """

        self.write('oModule.EnterScalar ' + scalar_value + '\n')

        self.loaded_quantities += 1

    def load_vector(self,
                    vector_expression: str):
        """ Load a vector array to the stack.

        Parameters
        ----------
        vector_expression : str
            A string representing a vector with the convention
            '(v_0, v_1, ... , v_n)'.
        """

        if self.o_module_name != 'FieldsReporter':
            raise Exception("FieldsReporter not activated.")

        if vector_expression[0] != '(' or vector_expression[-1] != ')':
            raise Exception(f"Vector : {vector_expression} not formatted "
                            f"like this: (v_0, v_1, ... , v_n)")

        self.write('oModule.EnterVector Array' +
                   vector_expression + '\n')
        self.loaded_quantities += 1

    def load_volume(self,
                    volume_name: str):
        """ Load a volume to the stack (used for integration). The volume has
        to correspond to a region in the design.
        # TODO Add a exception if the volume name is not in the design.

        Parameters
        ----------
        volume_name : str
            Name of the design volume to be added.
        """
        if self.o_module_name != 'FieldsReporter':
            raise Exception("FieldsReporter not activated.")

        self.write('oModule.EnterVol "' + volume_name + '"\n')
        self.loaded_quantities += 1

    def calc_multiply_vectors(self) -> None:
        """ Instruct the FieldsReporter to multiply the last
        two added quantities. The quantities should be vector.
        """
        # This is a weak testing method: if the user inputs a scalar
        # and a vector, the method will write the instruction but
        # ANSYS will produce and error.
        # TODO write a better loaded quantity tracker

        if self.o_module_name != 'FieldsReporter':
            raise Exception("FieldsReporter not activated.")

        if self.loaded_quantities < 2:
            raise Exception("For the multiplication, at least two quantities "
                            "should be loaded.")

        self.write('oModule.CalcOp "Dot"\n')
        self.loaded_quantities -= 1

    def calc_multiply_scalar(self) -> None:
        """ Multiply the last two added quantities.
        The quantities should be scalar.
        """

        if self.o_module_name != 'FieldsReporter':
            raise Exception("FieldsReporter not activated.")

        if self.loaded_quantities < 2:
            raise Exception("For the multiplication, at least two quantities "
                            "should be loaded.")

        self.write('oModule.CalcOp "*"\n')
        self.loaded_quantities -= 1

    def calc_divide_scalar(self) -> None:
        """ Divide the before last added quantity by
        the last added quantity. The quantities should be scalar.
        """

        if self.o_module_name != 'FieldsReporter':
            raise Exception("FieldsReporter not activated.")

        if self.loaded_quantities < 2:
            raise Exception("For the division, at least two quantities "
                            "should be loaded.")

        self.write('oModule.CalcOp "/"\n')
        self.loaded_quantities -= 1

    def calc_conjugate(self) -> None:
        """ Conjugate the last added quantity.
        The quantity should be complex.
        """

        if self.o_module_name != 'FieldsReporter':
            raise Exception("FieldsReporter not activated.")

        if self.loaded_quantities == 0:
            raise Exception("No quantity loaded.")

        self.write('oModule.CalcOp "Conj"\n')

    def calc_real(self) -> None:
        """ Take the real part of the last added quantity.
        The quantity should be complex.
        """

        if self.o_module_name != 'FieldsReporter':
            raise Exception("FieldsReporter not activated.")

        if self.loaded_quantities == 0:
            raise Exception("No quantity loaded.")

        self.write('oModule.CalcOp "Real"\n')

    def calc_duplicate_last_quantity(self):
        """ Duplicate the last quantity.
        """

        if self.o_module_name != 'FieldsReporter':
            raise Exception("FieldsReporter not activated.")

        if self.loaded_quantities == 0:
            raise Exception("No quantity loaded.")
        self.write('oModule.CalcStack "push"\n')
        self.loaded_quantities += 1

    def calc_integrate(self):
        """ Integrate the before last added quantity over the last added
        quantity.
        """

        if self.o_module_name != 'FieldsReporter':
            raise Exception("FieldsReporter not activated.")

        self.write('oModule.CalcOp "Integrate"\n')
        self.loaded_quantities -= 1

    def calc_sum(self):
        """Sum the last two added quantities.
        """

        if self.o_module_name != 'FieldsReporter':
            raise Exception("FieldsReporter not activated.")

        if self.loaded_quantities < 2:
            raise Exception("For the addition, at least two quantities "
                            "should be loaded.")
        self.write('oModule.CalcOp "+"\n')
        self.loaded_quantities -= 1

    def decompose_e_field(
            self,
            smooth_e_field: bool = False):
        """ Decompose the electric field along X, Y, Z.
        Create three variables, each corresponding to the squared norm
        of the field projection.

        Parameters
        ----------
        smooth_e_field : bool, default is False
            If true, the electric field will be smoothed.
        """

        if self.o_module_name != 'FieldsReporter':
            raise Exception("FieldsReporter not activated.")

        e_field_decomposition = [
            ['(1,0,0)', 'X'],
            ['(0,1,0)', 'Y'],
            ['(0,0,1)', 'Z']]

        for vector_decomposition in e_field_decomposition:
            self.load_predefined_quantity('E', smooth_field=smooth_e_field)
            self.load_vector(vector_decomposition[0])
            self.calc_multiply_vectors()
            self.calc_duplicate_last_quantity()
            self.calc_conjugate()
            self.calc_multiply_scalar()
            self.calc_real()
            self.create_quantity(f"E_{vector_decomposition[1]}")

    def compute_parallel_participation(
            self,
            dielectric_material: DielectricMaterial,
            index: int,
            new_expression_name: str) -> None:
        """ Volume integral of the electric field parallel to the surface
            (orthogonal to the surface normal).

        Parameters
        ----------
        dielectric_material : DielectricMaterial
            Further details available in the DielectricMaterial class
            definition.
        index : int
            Index to decide which element of the region list should be used for
            the volume integral.
        new_expression_name : str
            Name of the expression containing the field
            integration expression.
        """
        self.load_named_expression('E_X')
        self.load_volume(dielectric_material['regions'][index])
        self.calc_integrate()

        self.load_named_expression('E_Y')
        self.load_volume(dielectric_material['regions'][index])
        self.calc_integrate()
        self.calc_sum()
        self.create_quantity(new_expression_name)

    def compute_orthogonal_participation(
            self,
            dielectric_material: DielectricMaterial,
            index: int,
            new_expression_name: str) -> None:
        """ Volume integral of the electric field orthogonal to the surface (
            parallel to the surface normal).

        Parameters
        ----------
        dielectric_material : DielectricMaterial
            Further details available in the DielectricMaterial class
            definition.
        index : int
            Index to decide which element of the region list should be used for
            the volume integral.
        new_expression_name : str
            Name of the expression containing the field
            integration expression.
        """
        self.load_named_expression('E_Z')
        self.load_volume(dielectric_material['regions'][index])
        self.calc_integrate()
        self.create_quantity(new_expression_name)

    def save_project(self):
        """ Save the currently used project.
        """

        self.write('oProject.Save\n')

    def close_current_project(self):
        """ Close the currently used project. If the project is specified with
        a vbs variables, no vbs string characters are added.
        """
        if variable_in_list(self.o_project_name, self.script_variables):
            self.write('oDesktop.CloseProject ' + self.o_project_name + '\n')
        else:
            self.write('oDesktop.CloseProject "' + self.o_project_name + '"\n')

    def close_project(self,
                      project_name: str):
        """ Close a project not currently activated.
        """
        check_is_vbs_string(project_name)
        self.write('oDesktop.CloseProject ' + project_name + '\n')

    def _add_script_variable(self,
                             variable_name: str):
        """ Add a variable to the script.
        Parameters
        ----------
        variable_name : str
            Name of the script variable.
        """
        if variable_name in self.script_variables:
            raise Exception(f"Script already contains a "
                            f"variable named {variable_name}")
        else:
            self.script_variables.append(variable_name)

    def create_variable(self,
                        var_name: str):
        """ Create a .vbs variable"""

        self._add_script_variable(var_name)
        self.write(f"Dim {var_name} \n")

    def create_vbs_2d_array(
            self,
            vbs_array_name: str,
            array_2d: List[List[Union[str, float]]]):
        """ Create a 2D array in a .vbs script based on the content of
        a python 2D array.

        Parameters
        ----------
        vbs_array_name : str
            Name of the .vbs array.
        array_2d : List[List[Union[str, float]]]
            Python array to write.
        """
        self._add_script_variable(vbs_array_name)
        array_shape = np.array(array_2d).shape
        x = array_shape[0]
        y = array_shape[1]
        self.write(f"Dim {vbs_array_name}({x},{y}) \n")
        vbs_str = '"'
        for i in range(x):
            for j in range(y):
                self.write(f"{vbs_array_name}({i},{j})="
                           f"{vbs_str}{str(array_2d[i][j])}{vbs_str}\n")

    def create_vbs_1d_array(
            self,
            vbs_array_name: str,
            array_1d: List[Union[float, str]]):
        """ Create a 1D array in a .vbs script based on the content of
        a python 1D array (list).

        Parameters
        ----------
        vbs_array_name : str
            Name of the .vbs array.
        array_1d : List[Union[str, float]]
            Python array to write.
        """

        self._add_script_variable(vbs_array_name)
        self.write(f"Dim {vbs_array_name}({len(array_1d)})\n")
        vbs_str = '"'
        for i in range(len(array_1d)):
            self.write(f"{vbs_array_name}({str(i)})="
                       f"{vbs_str}{str(array_1d[i])}{vbs_str}\n")

    def start_for_loop(self,
                       iterator_name: str,
                       start: int,
                       end: int,
                       step: int = 1):
        """ Start a For Next loop statement.

        Parameters
        ----------
        iterator_name : str
            Name of the iterator.
        start : int
            Starting point of the loop.
        end : int
            End point of the loop.
        step : int, default is 1
            Step between each loop value.
        """
        self.write(f"For {iterator_name} = "
                   f"{str(start)} To {str(end)} Step {str(step)}\n")
        self.indentation_level += 1

    def end_for_loop(self):
        """ Terminate a For Next loop statement.
        """
        self.indentation_level -= 1
        self.write("Next\n")

    def close(self) -> None:
        """ Close the stream and log the writing completion."""
        VBScript.close(self)
        self.status.write_update(f"Finished the "
                                 f"writing of {self.script_name}")
