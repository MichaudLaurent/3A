from .specific_types import *
from .helper_functions import *
from .Execute_Script import execute_script
from .Run_Job import run_job
import os


class Step:
    def __init__(self,
                 name: str,
                 display_name: str,
                 step_type: str,
                 bash_file_name: str = None,
                 resources_requested: SimulationResources = None,
                 move_to_log_file_dir: bool = False,
                 script_name: str = None,
                 sub_folder: str = None,
                 log_file_name: str = None,
                 design_name: str = None,
                 setup_to_analyse: str = None,
                 func=None,
                 arg_list=None):
        """ Step to be performed by the p_ratio_task class.

        Parameters:
        name: str
            Name of the step.
        display_name: str
            Name to be used for status printing.
        step_type : str
            Either 'Script' or 'Analysis'
        bash_file_name : str
            Bash file name.
        resources_requested : SimulationResources
            Further details available in the SimulationResources class
            definition.
        move_to_log_file_dir : bool
            Decide if the log file has to be moved to the
            log_file directory upon successful completion.
        log_file_name : str, optional
            Name of the log file. Only has to be specified if `step_type`
            is et to 'Analysis'.
        design_name : str
            If `Step_type` is set to 'Analysis', the ANSYS design containing
            the setup to analyse has to be specified.
        setup_to_analyse : str
            If `Step_type` is set to 'Analysis', the setup name has to be
            specified.
        """

        self.name = name
        self.display_name = display_name
        self.done = False
        self.in_progress = False
        if step_type not in ['Script', 'Analysis', 'Python']:
            raise Exception(f"Step type: {step_type} not handled.")
        self.step_type = step_type
        self.move_to_log_file = move_to_log_file_dir
        self.sub_folder = sub_folder
        self.script_name = script_name
        self.resources_requested = resources_requested
        self.log_file_name = log_file_name
        self.bash_file_name = bash_file_name
        self.setup_to_analyse = setup_to_analyse
        self.design_name = design_name
        self.job_id = None
        self.func = func
        self.arg_list = arg_list


class Task:

    def __init__(self,
                 project_name,
                 exec_option: str,
                 status: LogText,
                 sub_folder: str = None,
                 ansys_exec_address: str = None,
                 display_warnings: bool = False):
        """ A p_ratio_task is a series of step which have to be performed on the same
        ANSYS project.

        Parameters
        ----------
        project_name : str
            Name of the ANSYS project.
        exec_option : str
            Type of execution, either 'local' or 'euler'.
        status : LogText
            Report the evolution of the analysis on a text file.
        sub_folder : str, optional
            Has to be specified is the ANSYS project is located in a sub folder.
        ansys_exec_address : str, optional
            Address of the ANSYS executable path. Required only for 'local'
            execution option.
        display_warnings : bool
            Choose to display all warning from log file.

        """
        self.project_name = project_name
        self.exec_option = exec_option
        self.ansys_exec_address = ansys_exec_address
        self.status = status
        self.sub_folder = sub_folder
        self.steps: List[Step] = []
        self.step_iterator = 0
        self.done = False
        self.display_warning = display_warnings

    def next_step(self):
        if self.step_iterator + 1 == len(self.steps):
            self.done = True
        else:
            self.step_iterator += 1

    def add_python_step(self,
                        step_name,
                        step_display_name,
                        func,
                        args):
        self.steps.append(Step(name=step_name,
                               display_name=step_display_name,
                               step_type='Python',
                               func=func,
                               arg_list=args))

    def add_analysis_step(
            self,
            step_name,
            step_display_name,
            bash_file_name: str,
            resources_requested: SimulationResources = None,
            move_to_log_file_dir: bool = False,
            log_file_name: str = None,
            design_name: str = None,
            setup_to_analyse: str = None):
        """ Add a new step to the p_ratio_task's step list.

        Parameters
        ----------
        step_name : str
            Step name.
        step_display_name : str
            Step display name for the status report.
        bash_file_name : str
            Bash file name.
        resources_requested : SimulationResources, optional
            Resource to request for an execution on EULER.
            Further details available in the SimulationResources class
            definition.
        move_to_log_file_dir : bool
            Decide if the log file has to be moved to the
            log_file directory upon successful completion.
        log_file_name : str, optional
            Name of the log file.
        design_name : str
            The ANSYS design containing the setup to analyse has to be specified.
        setup_to_analyse : str
            Setup name to analyse.
        """
        self.steps.append(Step(
            name=step_name,
            display_name=step_display_name,
            bash_file_name=bash_file_name,
            resources_requested=resources_requested,
            move_to_log_file_dir=move_to_log_file_dir,
            step_type='Analysis',
            log_file_name=log_file_name,
            setup_to_analyse=setup_to_analyse,
            design_name=design_name))

    def report_state(self):
        """ Current state of the p_ratio_task
        """
        report_str = self.project_name
        for step in self.steps:
            report_str += f"|{step.display_name}|"
            if step.done:
                report_str += 'O'
            else:
                report_str += 'X'

        report_str += '|'

        return report_str

    def execute_step(self) -> None:
        """ Execute the first step from the step list.
        """
        current_step = self.steps[self.step_iterator]
        if current_step.done:
            self.next_step()
            return None
        if current_step.step_type == 'Python':

            self.status.write_update(
                f"Executing python "
                f"step: {current_step.name}")
            try:
                current_step.func(**current_step.arg_list)
            except:
                self.status.write_update("Error for optimization plotting")
            self.next_step()
            return None
        if self.sub_folder:
            root_path = os.path.join(
                os.getcwd(), "",
                self.sub_folder)
        else:
            root_path = os.getcwd()
        # If a script is executed, the log file has
        # the same name as the vbs scripts.
        if current_step.step_type == 'Script':
            log_file_name = os.path.splitext(
                current_step.script_name)[0] + '.log'
        else:
            # For a setup analysis, the user has to define
            # the log file name.
            log_file_name = current_step.log_file_name

        log_file_absolute_address = os.path.join(root_path, "",
                                                 log_file_name)
        if not current_step.in_progress:
            # Remove any residuals from previous simulations.
            if os.path.exists(log_file_absolute_address):
                os.remove(log_file_absolute_address)
                self.status.write_update("Pre existing log file removed")

            self.status.write_update(f"Executing"
                                     f" {os.path.splitext(log_file_name)[0]}")
            if current_step.step_type == 'Script':
                job_id = execute_script(
                    script_name=current_step.script_name,
                    aedt_file_name=self.project_name + '.aedt',
                    ansys_exec_address=self.ansys_exec_address,
                    exec_option=self.exec_option,
                    resources_requested=current_step.resources_requested,
                    name_bash_file=current_step.bash_file_name,
                    sub_folder=self.sub_folder)
            else:  # 'Analysis'
                job_id = run_job(
                    exec_option=self.exec_option,
                    ansys_exec_address=self.ansys_exec_address,
                    aedt_file_name=self.project_name + '.aedt',
                    resources_requested=current_step.resources_requested,
                    design_name=current_step.design_name,
                    setup_to_analyse=current_step.setup_to_analyse,
                    bash_file_name=current_step.bash_file_name,
                    job_log_name=log_file_name,
                    sub_folder=self.sub_folder)

            current_step.in_progress = True
            if self.exec_option == 'euler':
                self.status.write_update(f"Job ID: {job_id} associated to"
                                         f" the step: {current_step.name}")
                current_step.job_id = job_id

        else:  # step in progress
            if not current_step.done:
                if os.path.exists(log_file_absolute_address):
                    if not find_lock_error_syndrome(log_file_name,
                                                    sub_folder=self.sub_folder):
                        if self.exec_option == 'local':
                            self.status.write_update(f"No error lock syndrome detected")
                            # detect other source of error which can
                            # only be fixed by user
                            detect_errors_from_log_file(
                                log_file_name=log_file_name,
                                status=self.status,
                                sub_folder=self.sub_folder,
                                display_warnings=self.display_warning)

                            # clean temporary files associated to the project
                            self.status.write_update("Preventive cleaning")
                            clean_project_files(
                                project_name=self.project_name,
                                status=self.status,
                                sub_folder=self.sub_folder)

                            current_step.done = True
                        else:  # EULER
                            lsf_report_default_name = 'lsf.o' + current_step.job_id
                            lsf_report_absolute_address = os.path.join(root_path, "",
                                                                       lsf_report_default_name)
                            if os.path.exists(lsf_report_absolute_address):
                                self.status.write_update(f"No error lock syndrome detected")
                                # detect other source of error which can
                                # only be fixed by user
                                detect_errors_from_log_file(
                                    log_file_name=log_file_name,
                                    status=self.status,
                                    sub_folder=self.sub_folder,
                                    display_warnings=self.display_warning)

                                os.rename(
                                    lsf_report_absolute_address,
                                    os.path.join(
                                        root_path, "",
                                        f"lfs_{os.path.splitext(log_file_name)[0]}.txt"))
                                self.status.write_update(
                                    f" lsf.o file renamed to "
                                    f"lsf_{os.path.splitext(log_file_name)[0]}")

                                # clean temporary files associated to the project
                                self.status.write_update("Preventive cleaning")
                                clean_project_files(
                                    project_name=self.project_name,
                                    status=self.status,
                                    sub_folder=self.sub_folder)
                                self.status.write_update(f"script execution completed")
                                self.status.write_time()
                                current_step.done = True
                    else:  # there is a lock error syndrome in the log file.
                        self.status.write_update(f"Error lock syndrome detected")
                        self.status.write_update("Check and remove potential "
                                                 "completion and lock files")
                        clean_project_files(
                            project_name=self.project_name,
                            status=self.status,
                            sub_folder=self.sub_folder)
                        os.remove(log_file_absolute_address)
                        # we initiate the execution (again).
                        current_step.in_progress = False
