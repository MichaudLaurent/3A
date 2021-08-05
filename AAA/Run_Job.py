import subprocess
import os
from subprocess import Popen, PIPE
from AAA.helper_functions import find_job_id_from_exec_output
from AAA.specific_types import SimulationResources


def run_job(
        setup_to_analyse: str,
        aedt_file_name: str,
        exec_option: str,
        design_name: str,
        ansys_exec_address: str = None,
        job_log_name: str = None,
        resources_requested: SimulationResources = None,
        bash_file_name: str = None,
        sub_folder: str = None):
    if exec_option == 'local':
        run_local_job(
            ansys_exec_address=ansys_exec_address,
            design_name=design_name,
            setup_to_analyse=setup_to_analyse,
            aedt_file_name=aedt_file_name,
            job_log_name=job_log_name,
            sub_folder=sub_folder)

    elif exec_option == 'euler':
        job_id = run_euler_job(
            aedt_file_name=aedt_file_name,
            name_bash_file=bash_file_name,
            setup_to_analyse=setup_to_analyse,
            resources_requested=resources_requested,
            design_name=design_name,
            job_log_name=job_log_name,
            sub_folder=sub_folder)
        return job_id


def run_local_job(
        ansys_exec_address,
        design_name,
        setup_to_analyse,
        aedt_file_name,
        job_log_name=None,
        sub_folder: str = None) -> None:
    if job_log_name is None:
        job_log_name = 'job.log'
    cmd_options = '-features=beta -ng ' + \
                  '-monitor -logfile ' + job_log_name + ' -batchsolve '

    subprocess.call(
        'cmd /c' + ' ' + ansys_exec_address + ' ' +
        cmd_options + ' ' +
        design_name + ':' +
        setup_to_analyse + ' ' +
        aedt_file_name,
        cwd=sub_folder)


def run_euler_job(
        aedt_file_name: str,
        resources_requested,
        name_bash_file: str = None,
        script_name: str = None,
        design_name: str = None,
        setup_to_analyse: str = None,
        job_log_name: str = None,
        sub_folder: str = None) -> str:
    """ Run a job on EULER.

    Can run a .vbs script or analyse a setup. The user
    has to chose between giving a script_name or a couple of
    design_name and setup_to_analyse.

    Parameters
    ----------
    aedt_file_name : str
        Name of the ANSYS Electronic Desktop file. Should contain the .aedt
        extension.
    resources_requested : SimulationResource

    name_bash_file : str, default is "temporary_bash_file.sh"
        Name of the bash file used to run the job submission command.
    script_name : str, optional
        Script name with a .vbs extension, executed on aedt_file_name.
    design_name : str, optional
        Name of the ANSYS design to analyse.
    setup_to_analyse : str, optional
        Name of the setup within "design_name" to analyse.
    job_log_name : str, default is "job.log"
        Name of the job log file used to track the progress of the run.
        Has no effect if a script is run, in this case, the log file has
        the name of the script with a .log extension.
    sub_folder : str, optional
        If specified, the execution will take place inside this folder.
    Returns
    -------
    str
        Identification index of the Euler job.
    """

    if name_bash_file is None:
        name_bash_file = "temporary_bash_file.sh"
    if job_log_name is None:
        job_log_name = 'job.log'

    if (script_name is not None and
            (setup_to_analyse is not None or
             design_name is not None)):
        raise Exception("Cannot run a script and analyse a setup "
                        "simultaneously")

    if sub_folder is not None:
        f = open(os.path.join(
            os.getcwd(), "",
            sub_folder, "",
            name_bash_file), "w")
    else:
        f = open(name_bash_file, "w")

    # load Euler's ANSYS module for the shell session
    f.write("module load ansys_em/19.5\n")
    # execution command for the .vbs script
    exec_str = 'bsub' + ' '
    exec_str += '-n ' + str(resources_requested['cores']) + ' '
    exec_str += '-W ' + str(resources_requested['time']) + ' '
    if resources_requested['RAM'] is not None:
        exec_str += ('-R "rusage[mem=' +
                     str(resources_requested['RAM']) +
                     ']"')
        exec_str += ' '

    if resources_requested['scratch'] is not None:
        exec_str += (
                '-R "rusage[scratch=' +
                str(resources_requested['scratch']) +
                ']"')
        exec_str += ' '

    if script_name is not None:
        exec_str += 'ansysedt -features=beta' + ' '
        exec_str += '-ng -runscriptandexit' + ' '
        exec_str += script_name + ' '
        exec_str += aedt_file_name + '\n'
    elif setup_to_analyse is not None and design_name is not None:
        exec_str += "'ansysedt -monitor -distributed -ng" + " "
        exec_str += "-logfile " + job_log_name + " "
        if resources_requested['cores'] > 1:
            g = open('batch.cfg ', 'w')
            g.write("$begin 'Config'\n")
            g.write("'HFSS/NumCoresPerDistributedTask'=1\n")
            g.write("'HFSS/HPCLicenseType'='pool'\n")
            g.write("$end 'Config'\n")
            g.close()
            exec_str += "-batchoptions batch.cfg" + " "
            exec_str += "-machinelist numcores=" + \
                        str(resources_requested['cores']) + " " + \
                        "-auto NumDistributedVariations=" + \
                        str(resources_requested['cores']) + " "
        exec_str += '-batchsolve "'
        exec_str += design_name + ':' + setup_to_analyse + '"' + " "
        exec_str += aedt_file_name + "'\n"

    f.write(exec_str)
    f.close()

    initial_dir = os.getcwd()
    if sub_folder is not None:
        os.chdir(os.path.join(
            os.getcwd(), "", sub_folder))

    # change bash file properties to enable its execution on EULER.
    os.system('chmod 755 ' + name_bash_file)
    os.chdir(initial_dir)

    subprocess0 = Popen('./' + name_bash_file,
                        shell=True,
                        stdout=PIPE,
                        cwd=sub_folder)
    output_string = subprocess0.stdout.read().decode('utf-8')
    job_id = find_job_id_from_exec_output(output_string)

    return job_id
