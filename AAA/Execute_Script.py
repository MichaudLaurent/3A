import subprocess
from .Run_Job import run_euler_job
from AAA.helper_functions import LogText
from AAA.specific_types import SimulationResources


def execute_script(
        script_name: str,
        aedt_file_name: str,
        exec_option: str,
        ansys_exec_address: str = None,
        resources_requested: SimulationResources = None,
        name_bash_file: str = None,
        job_log_name: str = None,
        sub_folder: str = None) -> str:
    """
    Parameters
    ----------
    script_name : str
        Name of the script to execute.
    aedt_file_name : str
        Name of the ANSYS Electronic Desktop file. Should contain the .aedt
        extension.
    exec_option : str
        Type of execution, either 'local' or 'euler'.
    ansys_exec_address : str
        Address of the ANSYS executable path. Required only for 'local'
        execution option.
    resources_requested : SimulationResources
        Further details available in the DielectricMaterial class
        definition.
    name_bash_file : str, default is "temporary_bash_file.sh"
        Name of the bash file used to run the job submission command.
    job_log_name : str, default is "job.log"
        Name of the job log file used to track the progress of the run.
    sub_folder : str, optional
        If specified, the execution will take place inside this folder.
    Returns
    -------
    str 
        job id if run on EULER or "0" if run locally.
    """

    if exec_option == 'local':
        local_script_execution(
            script_name,
            aedt_file_name,
            ansys_exec_address,
            sub_folder=sub_folder)
        return "0"

    elif exec_option == 'euler':
        job_id = run_euler_job(
            script_name=script_name,
            aedt_file_name=aedt_file_name,
            resources_requested=resources_requested,
            name_bash_file=name_bash_file,
            job_log_name=job_log_name,
            sub_folder=sub_folder)
        return job_id
    else:
        raise Exception(f"execution option: {exec_option} not handled")


def local_script_execution(
        script_name,
        aedt_file_name,
        ansys_exec_address,
        sub_folder: str = None) -> None:
    """
    Parameters
    ----------
    script_name : str
        Name of the script to execute.
    aedt_file_name : str
        Name of the ANSYS Electronic Desktop file. Should contain the .aedt
        extension.
    ansys_exec_address : str
        Address of the ANSYS executable path.
    sub_folder : str, optional
        If specified, the execution will take place inside this folder.
    """
    cmd_options = '-features=beta -ng -runscriptandexit'
    subprocess.call(
        'cmd /c' + ' ' + ansys_exec_address + ' ' +
        cmd_options + ' ' +
        script_name + ' ' +
        aedt_file_name,
        cwd=sub_folder)
