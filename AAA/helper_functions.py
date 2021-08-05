import time
from time import (strftime,
                  gmtime)
import itertools
import os
import json
from .specific_types import (VariationParameters,
                             VariationParametersListing)
from typing import List, Union
import shutil


def remove_project_flag(flag_name) -> None:
    """ Wait until successful removal of the flag file.

    Parameters
    ----------
    flag_name : str
        Name of the flag to be found and removed.

    """
    flag_removed = False
    while flag_removed is False:
        try:
            os.remove(flag_name)
            time.sleep(1)
            flag_removed = True
        except:
            pass


def backslash(exec_option: str) -> str:
    """ Defines the correct character for file navigation
    depending on the execution option.
    Parameters
    ----------
    exec_option : str
        Type of execution, either 'local' or 'euler'.
    """
    if exec_option == 'local':
        return "\\"
    elif exec_option == 'euler':
        return "/"
    else:
        raise Exception(f"Execution option: {exec_option} not handled")


def rename_lsf_file(job_id: str,
                    proper_name: str,
                    new_directory_address: str = None) -> None:
    """ Wait for the lsf.o report and rename it.

    Parameters
    ----------
    job_id : str
        Identifier of the LSF job.
    proper_name : str
        New name of the LSF job. Extension .txt is appended
        to `proper_name`.
    new_directory_address : str, optional
        If mentioned, will use this address to look for the report file.
    """
    initial_dir = os.getcwd()
    lsf_report_file = 'lsf.o' + job_id
    if new_directory_address is not None:
        os.chdir(new_directory_address)
    while not os.path.exists(lsf_report_file):
        time.sleep(1)
    os.rename(lsf_report_file, proper_name + '.txt')
    os.chdir(initial_dir)


def convert_py_list_to_vbs_array(w):
    str_array = "Array("
    for i in range(len(w) - 1):
        str_array = str_array + '"' + str(w[i]) + '"' + ","
    str_array = str_array + '"' + str(w[-1]) + '"' + ")"
    return str_array


def write_tab(number: int) -> str:
    """ Write tabulation character to a string.

    Parameters
    ----------
    number : int
        Number of tabulation character to return
    Returns
    -------
    str
        Succession of `number` tabulation character(s).

    """
    if number > 0:
        str_res = ''
        for i in range(number):
            str_res += '\t'
        return str_res
    else:
        return ''


class LogText:
    def __init__(self,
                 name_log_text_file: str):
        """ Report the evolution of the analysis on a text file.

        Parameters
        ----------
        name_log_text_file : str
            Name of the log file.
        """
        self.name_log_text_file = name_log_text_file
        self.start_time = time.time()
        f = open(self.name_log_text_file, "w")
        f.close()

    def write_update(self, text: str) -> None:
        """ Add a line to the text file and skip line.

        Parameters
        ----------
        text : str
            Text string to be added.
        """
        f = open(self.name_log_text_file, "a")
        f.write(text)
        f.write('\n')
        f.close()

    def write_time(self) -> None:
        """ Add a line of text to display the elapsed time since the
        LogText object was created.
        """
        seconds = time.time() - self.start_time
        self.write_update(strftime("%H:%M:%S", gmtime(seconds)))

    def write_separation_line(self):
        """ Write a visual separation between different
        status reports. """
        string = ''
        for i in range(25):
            string += '-'
        self.write_update(string)


def truncate(f, n):
    """Truncates/pads a float f to n decimal places without rounding"""
    s = '{}'.format(f)
    if 'e' in s or 'E' in s:
        return '{0:.{1}f}'.format(f, n)
    i, p, d = s.partition('.')
    return '.'.join([i, (d + '0' * n)[:n]])


def test_finish(
        root_of_variation_name,
        variation_parameters_dict,
        file_extension='.aedt.q.completed'):
    finish_bool = True
    project_list = get_project_list(
        variation_parameters_dict=variation_parameters_dict,
        root_of_variation_name=root_of_variation_name
    )
    for project_name in project_list:
        if not os.path.isfile(project_name + file_extension):
            finish_bool = False

    return finish_bool


def get_first_word(line):
    res_char = ''
    for i in range(len(line)):
        if line[i] != '	':
            res_char = res_char + line[i]
        else:
            return res_char


def get_variable_names(lines):
    variables = []
    for i in range(len(lines) - 1):
        variables.append(get_first_word(lines[i + 1]))
    return variables


def get_project_list(
        variation_parameters_dict: List[VariationParameters],
        root_of_variation_name: str) -> VariationParametersListing:
    """ Converts a list of variation_parameters into a variation_parameters_listing.

    Parameters
    ----------
    variation_parameters_dict : List[VariationParameters]
        Further details available in the variation_parameters class
        definition.
    root_of_variation_name : str
        Root of the design variations.
    Returns
    -------
    VariationParameterListing
        Further details available in the variation_parameters_listing class
        definition.
    """
    project_list = []
    variation_values_list = []
    sweep_list = []
    variable_order_convention = []
    for variation_parameter in variation_parameters_dict:
        sweep_list.append(variation_parameter['sweep'])
        variable_order_convention.append(variation_parameter['var_name'])
    for tuple_sweep in itertools.product(*sweep_list):
        project_name_str = root_of_variation_name
        variation_values = []
        for index, variation_parameter in enumerate(variation_parameters_dict):
            project_name_str = (project_name_str + '_' +
                                variation_parameter['var_name'] + '_' +
                                str(tuple_sweep[index]))
            variation_values.append(tuple_sweep[index])
        project_list.append(project_name_str)
        variation_values_list.append(variation_values)

    return VariationParametersListing(project_list=project_list,
                                      variable_order_convention=variable_order_convention,
                                      variation_values_list=variation_values_list)


def get_path_in_ansys_convention():
    return str(os.getcwd()).replace('\\', '/')


def string_to_word_list(s):
    word_list = []
    temp_word = ''
    for c in s:
        if c != ' ':
            temp_word = temp_word + c
        else:
            word_list.append(temp_word)
            temp_word = ''
    return word_list


def find_job_id_from_exec_output(output_string) -> str:
    val = f"no job id in: {output_string}"
    word_list = string_to_word_list(output_string)
    for index, item in enumerate(word_list):
        if item == 'Job':
            temp_s = ''
            for c in word_list[index + 1]:
                if c.isdigit():
                    temp_s = temp_s + c
            val = temp_s
    return val


def check_is_vbs_string(vbs_string: str):
    """ Check that a string is the the .vbs convention.

    Parameters
    ----------
    vbs_string: str
        String to check.
    """

    if vbs_string[0] != '"' or vbs_string[-1] != '"':
        return False
    else:
        return True


def get_design_properties_from_text_file(
        text_file_name,
        sub_folder: str = None):
    if sub_folder is None:
        f = open(text_file_name)
    else:
        f = open(os.path.join(os.getcwd(), "",
                              sub_folder, "",
                              text_file_name))

    lines = f.readlines()
    properties = []
    for i in range(len(lines) - 1):
        properties.append(get_first_word(lines[i + 1]))
    return properties


def find_lock_error_syndrome(job_name,
                             sub_folder: str = None):
    """ Check is a lock file prevented the normal execution of a .vbs script
    on an ANSYS project.

    Parameters
    ----------
    job_name : str
        Job name, should finish with a .log extension.
    sub_folder : str, optional


    Returns
    -------
    bool
        True if the error syndrome was detected.
    """
    if sub_folder is not None:
        f = open(os.path.join(os.getcwd(), "",
                              sub_folder, "", job_name))
    else:
        f = open(job_name)
    lines = f.readlines()
    no_errors = False
    error_syndrome = 'may be opened in another instance of the application.'
    for line in lines:
        if error_syndrome in line:
            no_errors = True
    return no_errors


def detect_errors_from_log_file(
        log_file_name: str,
        status: LogText,
        sub_folder: str = None,
        display_warnings: bool = False):
    """ Report the job log lines containing errors or warnings in the
    status.
    Parameters
    ----------
    log_file_name : str
        Log file name finishing with the proper extension.
    status : LogText
        Object used to report the progress of the analysis.
    sub_folder : str, optional
        If specified, the log file will be sought in this sub folder.
    """
    if sub_folder is None:
        f = open(log_file_name)
    else:
        f = open(os.path.join(os.getcwd(), "",
                              sub_folder, "",
                              log_file_name))
    lines = f.readlines()
    status.write_update(f"Checking for errors and warnings "
                        f"in: {log_file_name}")
    for i in range(len(lines)):
        words = string_to_word_list(lines[i])
        report_line = False
        for j in range(len(words)):
            if words[j] == '[error]':
                report_line = True
            elif words[j] == '[warning]' and display_warnings:
                report_line = True

        if report_line:
            status.write_update(lines[i])
            try:
                status.write_update(lines[i + 1])
                status.write_update(lines[i + 2])
                status.write_update(lines[i + 3])
            except IndexError:
                pass


def clean_project_files(project_name: str,
                        status: LogText,
                        clean_aedt_file: bool = False,
                        clean_aedtresults: bool = False,
                        sub_folder: str = None, ) -> None:
    """Try to remove files linked to an ANSYS project. This method checks
    the file existence before trying to delete it.

    Parameters
    ----------
    project_name : str
        Name of the ANSYS project.
    status : LogText
        Object used to report the progress of the analysis.
    clean_aedt_file : bool, default is False
        If True, the .aedt file will be deleted (if it exists).
    clean_aedtresults : bool, default is False
        If True, the .aedtresults file will be delete (if it exists).
    """
    file_to_check = [project_name + '.aedt.q.completed',
                     project_name + '.aedt.batchinfo',
                     project_name + '.aedt.lock',
                     project_name + '.aedt.temp',
                     project_name + '.aedt.auto']
    if clean_aedt_file:
        file_to_check.append(project_name + '.aedt')
    if clean_aedtresults:
        file_to_check.append(project_name + '.aedtresults')

    initial_dir = os.getcwd()
    if sub_folder is not None:
        os.chdir(sub_folder)
    for file_name in file_to_check:
        if os.path.isfile(file_name):
            os.remove(file_name)
            status.write_update(f"Removed {file_name}")
        if os.path.isdir(file_name):
            shutil.rmtree(file_name)
            status.write_update(f"Removed {file_name}")
    os.chdir(initial_dir)


def get_json_saving_path(file_name: str,
                         sub_directory: str = None):
    """Return the absolute path of a file

    Parameters
    ----------
    file_name : str
        File name with the extension.
    sub_directory : str, optional
        Sub directory where the file should be saved.
    """
    if sub_directory is None:
        return os.path.join(
            os.getcwd(), "",
            file_name)
    else:
        sub_directory_path = os.path.join(
            os.getcwd(),
            "", sub_directory)
        if not os.path.isdir(sub_directory_path):
            os.mkdir(sub_directory_path)
        return os.path.join(
            os.getcwd(), "", sub_directory, "",
            file_name)


def save_dict_as_json_file(
        dict_to_save: Union[dict, List[dict]],
        json_name: str,
        sub_directory: str = None):
    saving_path = get_json_saving_path(f"{json_name}.json",
                                       sub_directory)

    with open(saving_path, 'w') as jsonFile:
        jsonFile.write(json.dumps(dict_to_save, indent=4))


def save_list_as_json_file(
        list_to_save: Union[dict, List[str]],
        json_name: str,
        sub_directory: str = None):
    saving_path = get_json_saving_path(f"{json_name}.json",
                                       sub_directory)

    with open(saving_path, 'w') as filehandle:
        json.dump(list_to_save, filehandle)


def read_json_file(
        json_name: str,
        sub_directory: str = None):
    saving_path = get_json_saving_path(f"{json_name}.json",
                                       sub_directory)
    with open(saving_path, 'r') as filehandle:
        return json.load(filehandle)


def move_file_to_sub_folder(file_name: str,
                            sub_folder: str,
                            initial_sub_folder: str = None):
    """ Move a file to a sub folder of the main directory.

    Parameters
    ----------
    file_name : str
        Name of the file.
    sub_folder : str
        Name of the sub folder to place the file in.
    initial_sub_folder : str, optional
        If the file to be moved is already in a sub directory, it has to be
        specified with this argument.
    """
    sub_directory_path = os.path.join(
        os.getcwd(),
        "", sub_folder)
    if not os.path.isdir(sub_directory_path):
        os.mkdir(sub_directory_path)

    if initial_sub_folder is None:
        initial_path = os.path.join(
            os.getcwd(), "", file_name)
    else:
        initial_path = os.path.join(
            os.getcwd(), "", initial_sub_folder, "", file_name)

    final_path = os.path.join(
        os.getcwd(), "", sub_folder, "",
        file_name)
    if os.path.isfile(final_path):
        os.remove(final_path)
    os.rename(initial_path, final_path)


def variable_in_list(string: str,
                     variable_list: List[str]):
    """ Check if a string represents an array variable.

    Parameters
    ----------
    string : str
        Name of the string containing a potential variable.
    variable_list : List[str]
        List of the preexisting variable names

    Returns
    -------
    bool
        True if the string correspond to a variable present in `variable_list`.
    """
    variable_name = ""
    for c in string:
        if c != '(':
            variable_name += c
        else:
            break
    return variable_name in variable_list
