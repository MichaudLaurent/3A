from typing import Dict, Union, List
from .scripted_step_class import ScriptedStep
from .task_class import *
from .data_analysis_helper import *


class PRatioAnalysis(LogText):
    def __init__(
            self,
            exec_option: str,
            root_of_variation_name: str,
            reference_project_name: str,
            reference_maxwell_design_name: str,
            reference_maxwell_design_properties: List[str],
            maxwell_optimization_variables: List[OptimizationVariable],
            maxwell_target_parameters: List[CMatrixTarget],
            maxwell_cache_variables: List[CMatrixCacheVariable],
            reference_hfss_design_name: str,
            reference_hfss_design_properties: List[str],
            dielectric_materials: List[DielectricMaterial],
            resources_requested_script: SimulationResources,
            resources_requested_optimization: SimulationResources,
            resources_requested_sweep: SimulationResources,
            ansys_exec_address: str,
            list_var_param: VariationParametersListing = None,
            cartesian_var_param: List[VariationParameters] = None, ):
        """
        Parameters
        ----------
        root_of_variation_name : str
            Root used to write the ANSYS files corresponding to each variation.
        reference_project_name : str
            ANSYS reference project name.
        reference_maxwell_design_name : str
            ANSYS Maxwell reference design name, should be inside the
            reference project.
        maxwell_optimization_variables : List[OptimizationVariable]
            List of OptimizationVariable.
            Further details available in the OptimizationVariable class
            definition.
        maxwell_target_parameters : List[CMatrixTarget]
            List of capacitance matrix components to target for the optimization.
            Further details available in the CMatrixTarget class
            definition.
        maxwell_cache_variables : List[CMatrixCacheVariable]
            List of capacitance matrix elements to be added to the
            cache of the solver.
        reference_hfss_design_name : str
            ANSYS HFSS reference design name, should be inside the
            reference project.
        exec_option : str
            Type of execution, either 'local' or 'euler'.
        dielectric_materials : List[DielectricMaterial]
            List of the DielectricMaterial dictionaries linking the geometry
            of the HFSS design to the physics of the system.
            Further details available in the DielectricMaterial class
            definition. DielectricMaterial 'final_name' key has to be cautiously
            named. 'MA', 'MS', and 'SA' strings will trigger the E-field
            decomposition. Depending on the 'regions' specified, different
            variables are generated.
            Example 1: {'final_name': 'MA', 'regions': ['MA_bot', 'MA_top']} will
            generate the following variables: 'E_MA_bot_O', 'E_MA_bot_P',
            'E_MA_top_O', 'E_MA_top_P', 'E_MA_O', 'E_MA_P' and 'E_MA'.
            The last two are just the sum of each intermediate region variables.
            Example 2: {'final_name': 'MA', 'regions': ['MA_bot']} will
            generate (directly) the following variables: 'MA_O', 'MA_P' and 'E_MA'.
            In these examples, 'E_MA' is the rescaled p-ratio: It makes use of the
            entry 'epsilon_r' to adjust the E-field integral. The convention being
            that for all the HFSS design, a fake dielectric material with a relative
            permittivity of 10 is used to ease numerical convergence.
        resources_requested_script : SimulationResources
            LSF resources required to run a .vbs script.
            Further details available in the SimulationResources class
            definition.
        resources_requested_optimization : SimulationResources
            LSF resources required to run a Maxwell optimization.
            Further details available in the SimulationResources class
            definition.
        resources_requested_sweep : SimulationResources
            LSF resources required to run an HFSS sweep.
            Further details available in the SimulationResources class
            definition.
        ansys_exec_address : str
            Address of the ANSYS executable path. Required only for 'local'
            execution option.
        list_var_param: VariationParametersListing
            List of variation to generate.
        cartesian_var_param:List[VariationParameters]
            List of variable sweep. The cartesian product between the sweep
            domains is used to produce the variations.
        """
        LogText.__init__(self, f"{root_of_variation_name}_status.txt")

        self.root_of_variation_name = root_of_variation_name
        self.reference_project_name = reference_project_name
        self.reference_maxwell_design_name = reference_maxwell_design_name
        self.reference_maxwell_design_properties = \
            reference_maxwell_design_properties
        self.maxwell_cache_variables = maxwell_cache_variables
        self.maxwell_optimization_variables = maxwell_optimization_variables
        self.maxwell_target_parameters = maxwell_target_parameters
        self.maxwell_optimization_setup_name = 'OptimizationSetup1'
        self.max_optimization_iter = None
        self.reference_hfss_design_name = reference_hfss_design_name
        self.reference_hfss_design_properties = \
            reference_hfss_design_properties
        self.hfss_sweep_points = None
        self.exec_option = exec_option
        self.resources_requested_script = resources_requested_script
        self.resources_requested_optimization = resources_requested_optimization
        self.resources_requested_sweep = resources_requested_sweep
        self.ansys_exec_address = ansys_exec_address
        self.dielectric_materials = dielectric_materials
        try:
            self.hfss_setup_cache_variables: List[str] = read_json_file(
                json_name='c_target_cache_variables',
                sub_directory='json_files')
            self.write_update("HFSS cache variable obtained from c_target_cache_variables.json")
        except OSError:
            self.hfss_setup_cache_variables = None

        self.hfss_sweep_setup_name = 'ParametricSetup1'
        self.preparation_task = Task(
            project_name=self.reference_project_name,
            exec_option=self.exec_option,
            status=self,
            ansys_exec_address=self.ansys_exec_address)

        self.p_ratio_tasks: List[Task] = []

        if list_var_param is not None:
            self.variation_parameters_listing = list_var_param
        elif cartesian_var_param is not None:
            self.variation_parameters_listing = get_project_list(
                variation_parameters_dict=cartesian_var_param,
                root_of_variation_name=self.root_of_variation_name)
        else:
            raise Exception("list_var_param or cartesian_var_param have to be specified.")

        for project in self.variation_parameters_listing['project_listing']:
            path_to_directory = os.path.join(os.getcwd(), "", project)
            if not os.path.exists(path_to_directory):
                os.mkdir(path_to_directory)

    def create_hfss_setup(
            self,
            setup_name: str = "Setup1",
            parametric_setup: str = "ParametricSetup1",
            var_to_sweep: str = "lossy_layer_thickness",
            unit_of_var_to_sweep: str = "um",
            sweep_start: float = 0.2,
            sweep_end: float = 0.5,
            sweep_points: int = 5,
            max_delta_freq: float = 1,
            min_freq: float = 3,
            num_modes: int = 1,
            percent_refinement: float = 30,
            minimum_converged_passes: int = 5,
            maximum_passes: int = 40,
            minimum_passes: int = 8,
            max_relative_change: float = 2,
            smooth_e_field: bool = False) -> None:
        """

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
        smooth_e_field : bool, default is False
            Decide to smooth the simulated electric field before the
            integrations.
        Returns
        -------
        Dict[str, Union[list, str]]
            Dictionary with the keys:
            'job_id' giving the job ID if the execution option is set to 'euler'.
            'cache_variable' giving the list of all the variable name added to
            the cache of the design setup.
        """

        step = ScriptedStep(
            common_name=f"update_HFSS_setup_{self.root_of_variation_name}",
            display_name='HFSS gen',
            exec_option=self.exec_option,
            ansys_exec_address=self.ansys_exec_address,
            resources_requested=self.resources_requested_script,
            status=self)
        step.set_project('"' + self.reference_project_name + '"')
        step.set_design('"' + self.reference_hfss_design_name + '"')
        step.set_module('"FieldsReporter"')
        step.clear_fields_reporter()

        # Compute the squared norm of the electric field.
        step.load_predefined_quantity('E', smooth_e_field)
        step.calc_duplicate_last_quantity()
        step.calc_conjugate()
        step.calc_multiply_vectors()
        step.calc_real()
        step.create_quantity('E_norm')

        step.decompose_e_field(smooth_e_field)
        fct_decomposition: Dict[
            str,
            Union[step.compute_parallel_participation,
                  step.compute_orthogonal_participation]] = {
            'P': step.compute_parallel_participation,
            'O': step.compute_orthogonal_participation}

        for domain in self.dielectric_materials:
            if domain['final_name'] in ['MA', 'MS', 'SA']:
                for key in fct_decomposition.keys():
                    if len(domain['regions']) == 1:
                        # only one domain defines the thin layer
                        fct_decomposition[key](
                            dielectric_material=domain,
                            index=0,
                            new_expression_name=f"E_{domain['final_name']}_{key}")
                    else:
                        # many domains define the thin layers, we create individual
                        # variables to keep track of each contributions.
                        for i in range(len(domain['regions'])):
                            fct_decomposition[key](
                                dielectric_material=domain,
                                index=i,
                                new_expression_name=f"E_{domain['regions'][i]}_{key}")

                            step.load_named_expression(
                                f"E_{domain['regions'][i]}_{key}")

                        for i in range(len(domain['regions']) - 1):
                            step.calc_sum()

                        step.create_quantity(f"E_{domain['final_name']}_{key}")

                # Knowingly create incomplete energy variables for the
                # MS and MA thin lossy dielectric layer. The reason being that we
                # only focus on the E-field components behaving linearly
                # as the thickness of the layer changes.

                if domain['final_name'] in ['MS', 'MA']:
                    step.load_named_expression(f"E_{domain['final_name']}_O")
                    step.load_scalar(str(domain['epsilon_r'] / 10))
                    step.calc_divide_scalar()

                    step.create_quantity(f"E_{domain['final_name']}")
                else:  # SA
                    step.load_named_expression(f"E_{domain['final_name']}_O")
                    step.load_scalar(str(domain['epsilon_r'] / 10))
                    step.calc_divide_scalar()

                    step.load_named_expression(f"E_{domain['final_name']}_P")
                    step.load_scalar(str(domain['epsilon_r'] / 10))
                    step.calc_multiply_scalar()

                    step.calc_sum()
                    step.create_quantity(f"E_{domain['final_name']}")

            else:
                # With a regular domain (not nm scaled along z),
                # the norm of the electric field `E_norm` is directly used.
                if len(domain['regions']) == 1:
                    step.load_named_expression('E_norm')
                    step.load_volume(domain['regions'][0])
                    step.calc_integrate()
                    step.load_scalar(str(domain['epsilon_r']))
                    step.calc_multiply_scalar()
                    step.create_quantity(f"E_{domain['final_name']}")

                else:
                    for region in domain['regions']:
                        step.load_named_expression('E_norm')
                        step.load_volume(region)
                        step.calc_integrate()
                    for i in range(len(domain['regions']) - 1):
                        step.calc_sum()

                    step.load_scalar(str(domain['epsilon_r']))
                    step.calc_multiply_scalar()
                    step.create_quantity(f"E_{domain['final_name']}")

        # Compute the total energy
        for domain in self.dielectric_materials:
            step.load_named_expression(f"E_{domain['final_name']}")

        for i in range(len(self.dielectric_materials) - 1):
            step.calc_sum()

        step.create_quantity('E_tot')
        # Create variables to estimate the convergence of the FEM.
        # We need to use relative quantities since absolute quantities
        # tends to fluctuate more during the mesh refinement process.

        # Create p-ratios variables for the dielectric materials
        hfss_cache_variables = []
        hfss_convergence_cache_variables = []
        for domain in self.dielectric_materials:
            step.load_named_expression(f"E_{domain['final_name']}")
            hfss_cache_variables.append(f"E_{domain['final_name']}")
            step.load_named_expression('E_tot')
            step.calc_divide_scalar()
            step.create_quantity(f"p_{domain['final_name']}")
            hfss_convergence_cache_variables.append(f"p_{domain['final_name']}")

        hfss_cache_variables.append("E_tot")

        hfss_cache_variables.extend(
            hfss_convergence_cache_variables)

        self.hfss_setup_cache_variables = hfss_cache_variables

        save_list_as_json_file(list_to_save=hfss_cache_variables,
                               json_name='c_target_cache_variables',
                               sub_directory='json_files')

        step.create_hfss_setup(
            setup_name=setup_name,
            max_delta_freq=max_delta_freq,
            min_freq=min_freq,
            num_modes=num_modes,
            percent_refinement=percent_refinement,
            minimum_converged_passes=minimum_converged_passes,
            maximum_passes=maximum_passes,
            minimum_passes=minimum_passes,
            max_relative_change=max_relative_change,
            cache_variables=hfss_cache_variables,
            convergence_cache_variables=hfss_convergence_cache_variables)

        step.modify_hfss_sweep_setup(
            setup_name=setup_name,
            parametric_setup=parametric_setup,
            var_to_sweep=var_to_sweep,
            unit_of_var_to_sweep=unit_of_var_to_sweep,
            sweep_start=sweep_start,
            sweep_end=sweep_end,
            sweep_points=sweep_points)
        self.hfss_sweep_points = sweep_points
        step.save_project()
        step.close_current_project()
        step.close()
        self.preparation_task.steps.append(step)

    def create_maxwell_setup(
            self,
            opti_max_iter: int = 25,
            percent_error: float = 5,
            minimum_passes: int = 5,
            maximum_passes: int = 30,
            minimum_converged_passes: int = 1,
            percent_refinement: float = 30,
            max_relative_change: float = 1.5,
            iterative_solver: bool = True,
            relative_residual: float = 1e-6,
            non_linear_residual: float = 1e-3):
        """ Create a Maxwell analysis setup and an optimization setup.

        Parameters
        ----------
        opti_max_iter : int, default is 25
            Maximum number of iteration for the optimization setup.
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
        iterative_solver : bool, default is True
            Activate iterative solving (rather then direct solving), lowering the
            memory use of the setup.
        relative_residual : float, default is 1e-6
        non_linear_residual : float, default is 1e-3
        """
        self.max_optimization_iter = opti_max_iter
        step = ScriptedStep(
            common_name=f"update_Maxwell_setup_{self.root_of_variation_name}",
            display_name='Maxwell gen',
            exec_option=self.exec_option,
            ansys_exec_address=self.ansys_exec_address,
            resources_requested=self.resources_requested_script,
            status=self)

        step.set_project('"' + self.reference_project_name + '"')
        step.set_design('"' + self.reference_maxwell_design_name + '"')

        step.create_maxwell_setup(
            percent_error=percent_error,
            minimum_passes=minimum_passes,
            maximum_passes=maximum_passes,
            minimum_converged_passes=minimum_converged_passes,
            percent_refinement=percent_refinement,
            cache_variables=self.maxwell_cache_variables,
            max_relative_change=max_relative_change,
            iterative_solver=iterative_solver,
            relative_residual=relative_residual,
            non_linear_residual=non_linear_residual)

        step.create_maxwell_optimization_setup(
            optimization_variables=self.maxwell_optimization_variables,
            c_mat_targets=self.maxwell_target_parameters,
            max_iter=opti_max_iter,
            maxwell_design_properties=self.reference_maxwell_design_properties)

        step.save_project()
        step.close_current_project()

        step.close()
        self.preparation_task.steps.append(step)

    def create_design_variation(self) -> None:

        """ Create design variations based on a reference project.
        For the p-ratio analysis, the reference project should contain a Maxwell
        design and an HFSS design. The function write and execute a script
        copying the reference project and its associated designs. The copied
        project is modified according to list_var_param or cartesian_var_param.
        """

        step = ScriptedStep(
            common_name=f"variation_study_{self.root_of_variation_name}",
            display_name='Variation gen',
            exec_option=self.exec_option,
            resources_requested=self.resources_requested_script,
            status=self,
            ansys_exec_address=self.ansys_exec_address)

        # Initialise a .vbs array to contain the variation parameter values.
        number_of_variations = len(self.variation_parameters_listing[
                                       'project_listing'])
        number_of_variables = len(self.variation_parameters_listing[
                                      'variable_order_convention'])

        step.create_vbs_2d_array(
            vbs_array_name='var_param_listing',
            array_2d=self.variation_parameters_listing['variation_values_list'])

        step.create_vbs_1d_array(
            vbs_array_name='variable_names',
            array_1d=self.variation_parameters_listing['variable_order_convention'])

        step.create_vbs_1d_array(
            vbs_array_name='project_names',
            array_1d=self.variation_parameters_listing['project_listing'])
        # The project and the design variable are initialized outside of the loop.
        step.init_project()
        step.init_design()
        step.start_for_loop(iterator_name='i',
                            start=0,
                            end=number_of_variations - 1)
        step.set_project('"' + self.reference_project_name + '"')
        step.copy_design('"' + self.reference_maxwell_design_name + '"')

        # Place the new project within a sub folder with the same name as
        # the project.
        step.new_project(
            path_name='"' + get_path_in_ansys_convention() +
                      '/" & project_names(i) & "/" & project_names(i) & ".aedt"')

        step.paste_design()
        step.set_project('"' + self.reference_project_name + '"')
        step.copy_design('"' + self.reference_hfss_design_name + '"')
        step.set_project('project_names(i)')
        step.paste_design()

        step.set_design('"' + self.reference_maxwell_design_name + '"')
        step.start_for_loop(iterator_name='j',
                            start=0,
                            end=number_of_variables - 1)
        step.change_design_property(
            property_name='variable_names(j)',
            property_value='var_param_listing(i,j)',
            append_units=True)
        step.end_for_loop()

        step.set_design('"' + self.reference_hfss_design_name + '"')
        step.start_for_loop(iterator_name='j',
                            start=0,
                            end=number_of_variables - 1)
        step.change_design_property(
            property_name='variable_names(j)',
            property_value='var_param_listing(i,j)',
            append_units=True)
        step.end_for_loop()
        step.save_project()
        step.close_current_project()
        step.end_for_loop()
        step.close_project('"' + self.reference_project_name + '"')

        step.close()
        self.preparation_task.steps.append(step)

    def create_p_ratio_tasks(self):
        """ Create the participation ratio analysis tasks.
         Comprise:
         -optimization of the Maxwell design.
         -creation of the optimization report (to check the quality of the
          optimization).
         -transfer of the optimized Maxwell parameters to the HFSS design.
         -sweep of the thin lossy dielectric layers thickness in the HFSS design.
         -export the cache of the HFSS solver.
         """
        for project in self.variation_parameters_listing['project_listing']:
            p_ratio_task = Task(
                project_name=project,
                exec_option=self.exec_option,
                status=self,
                ansys_exec_address=self.ansys_exec_address,
                sub_folder=project)

            self.optimize_maxwell_design(project_name=project,
                                         p_ratio_task=p_ratio_task)
            self.export_maxwell_opti_data(project_name=project,
                                          p_ratio_task=p_ratio_task)
            self.export_maxwell_convergence_cache(project_name=project,
                                                  p_ratio_task=p_ratio_task)
            self.plot_optimization_report(project_name=project,
                                          p_ratio_task=p_ratio_task)
            self.maxwell_to_hfss_design_param(project_name=project,
                                              p_ratio_task=p_ratio_task)
            self.sweep_hfss_design(project_name=project,
                                   p_ratio_task=p_ratio_task)
            self.export_hfss_convergence_cache(project_name=project,
                                               p_ratio_task=p_ratio_task)

            self.p_ratio_tasks.append(p_ratio_task)

    def run_preparation_task(self):
        """ Execute the steps in the preparation p_ratio_task."""
        while not self.preparation_task.done:
            self.preparation_task.execute_step()

            task_log = LogText(name_log_text_file=f"{self.root_of_variation_name}_"
                                                  f"task_status.txt")
            task_log.write_update(self.preparation_task.report_state())
            time.sleep(2)

    def run_p_ratio_tasks(self):
        """ Run participation ratio analysis tasks."""
        while self.p_ratio_tasks:
            task_log = LogText(name_log_text_file=f"{self.root_of_variation_name}_"
                                                  f"task_status.txt")
            for task in self.p_ratio_tasks:
                if not task.done:
                    task.execute_step()
                    task_log.write_update(task.report_state())
                else:
                    self.p_ratio_tasks.remove(task)
            time.sleep(2)

    def optimize_maxwell_design(
            self,
            project_name: str,
            p_ratio_task: Task):
        """ Create an maxwell optimization step."""

        p_ratio_task.add_analysis_step(
            step_name="optimization",
            step_display_name="Opti",
            bash_file_name=f"job_Maxwell_opti_{project_name}.sh",
            resources_requested=self.resources_requested_optimization,
            log_file_name=f"job_Maxwell_opti_{project_name}.log",
            design_name=self.reference_maxwell_design_name,
            setup_to_analyse=f"Optimetrics:{self.maxwell_optimization_setup_name}")

    def sweep_hfss_design(
            self,
            project_name: str,
            p_ratio_task: Task):
        """ Create an maxwell optimization step."""

        p_ratio_task.add_analysis_step(
            step_name=f"sweep_hfss_design_{project_name}",
            step_display_name="Sweep",
            bash_file_name=f"job_HFSS_sweep_{project_name}.sh",
            resources_requested=self.resources_requested_sweep,
            log_file_name=f"job_HFSS_sweep_{project_name}.log",
            design_name=self.reference_hfss_design_name,
            setup_to_analyse=f"Optimetrics:{self.hfss_sweep_setup_name}")

    def export_maxwell_convergence_cache(
            self,
            project_name: str,
            p_ratio_task: Task):
        """ Export the convergence cache of the maxwell design."""

        step = ScriptedStep(
            common_name=f"export_maxwell_convergence_cache_{project_name}",
            display_name='Maxwell Cache Export',
            exec_option=self.exec_option,
            ansys_exec_address=self.ansys_exec_address,
            resources_requested=self.resources_requested_script,
            status=self,
            sub_folder=project_name)
        step.set_project('"' + project_name + '"')
        step.set_design('"' + self.reference_maxwell_design_name + '"')
        step.create_setup_report(
            design_type='Maxwell',
            csv_file_name=f"maxwell_cache_{project_name}.csv",
            project_properties=self.reference_maxwell_design_properties,
            cache_variables=self.maxwell_cache_variables,
            sub_folder=project_name)
        step.close()
        p_ratio_task.steps.append(step)

    def export_hfss_convergence_cache(
            self,
            project_name: str,
            p_ratio_task: Task):
        """ Export the convergence cache of the HFSS design."""

        step = ScriptedStep(
            common_name=f"export_hfss_convergence_cache_{project_name}",
            display_name='HFSS Cache Export',
            exec_option=self.exec_option,
            ansys_exec_address=self.ansys_exec_address,
            resources_requested=self.resources_requested_script,
            status=self,
            sub_folder=project_name)
        step.set_project('"' + project_name + '"')
        step.set_design('"' + self.reference_hfss_design_name + '"')
        step.create_setup_report(
            design_type='HFSS',
            csv_file_name=f"hfss_cache_{project_name}.csv",
            project_properties=self.reference_hfss_design_properties,
            cache_variables=self.hfss_setup_cache_variables,
            sub_folder=project_name)
        step.close()
        p_ratio_task.steps.append(step)

    def export_maxwell_opti_data(
            self,
            project_name: str,
            p_ratio_task):
        """ Create and export the result of the Maxwell optimization"""

        step = ScriptedStep(
            common_name=f"export_maxwell_opti_data_{project_name}",
            display_name='Maxwell opti export',
            exec_option=self.exec_option,
            resources_requested=self.resources_requested_script,
            status=self,
            ansys_exec_address=self.ansys_exec_address,
            sub_folder=project_name)

        step.set_project('"' + project_name + '"')
        step.set_design('"' + self.reference_maxwell_design_name + '"')
        step.export_optimization_results(
            sub_folder_name=project_name)
        step.close()
        p_ratio_task.steps.append(step)

    def plot_optimization_report(
            self,
            project_name: str,
            p_ratio_task: Task):
        """ Add a python step to a task.
        Uses the .csv cache and optimization reports to produce a table."""
        p_ratio_task.steps.append(Step(
            name=f"plot_optimization_results_{project_name}",
            display_name="Plot Opti",
            step_type='Python',
            func=optimization_report,
            arg_list={
                'title': f"Opti Report {project_name}",
                'png_path_name': os.path.join(os.getcwd(), "", project_name, "",
                                              f"opti_report_{project_name}.png"),
                'cache_report_path': os.path.join(os.getcwd(), "", project_name, "",
                                                  f"maxwell_cache_{project_name}.csv"),
                'opti_report_path': os.path.join(os.getcwd(), "", project_name, "",
                                                 f"opti_result_{project_name}.csv"),
                'c_target_cache_variables': self.maxwell_target_parameters,
                'optimization_variables': self.maxwell_optimization_variables,
                'solved_setup_number': self.max_optimization_iter}))

    def maxwell_to_hfss_design_param(
            self,
            project_name,
            p_ratio_task: Task):
        """ Transfer Maxwell optimized variable in the HFSS design."""

        step = ScriptedStep(
            common_name=f"maxwell_hfss_transfer_{project_name}",
            display_name='Maxwell to HFSS',
            exec_option=self.exec_option,
            ansys_exec_address=self.ansys_exec_address,
            resources_requested=self.resources_requested_script,
            status=self,
            sub_folder=project_name)

        for index in range(len(self.maxwell_optimization_variables)):
            step.create_variable(f"w{index}")

        step.set_project('"' + project_name + '"')
        step.set_design('"' + self.reference_maxwell_design_name + '"')

        for index, parameter in enumerate(self.maxwell_optimization_variables):
            step.assign_design_variable_value_to_script_variable(
                script_variable_name=f"w{index}",
                design_variable_name=parameter['name'],
                design_parameter_list=self.reference_maxwell_design_properties)

        step.set_design('"' + self.reference_hfss_design_name + '"')
        for index, parameter in enumerate(self.maxwell_optimization_variables):
            step.change_design_property(property_name='"' + parameter['name'] + '"',
                                        property_value=f"w{index}",
                                        property_unit='"' + parameter['units'] + '"',
                                        append_units=False)
        step.save_project()
        step.close_current_project()
        step.close()
        p_ratio_task.steps.append(step)
