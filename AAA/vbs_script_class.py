import os
from typing import IO


class VBScript:
    def __init__(self,
                 script_name: str = None,
                 sub_folder: str = None,
                 f_stream: IO = None):
        """ Helper class for .vbs script writing.

        Parameters
        ----------
        script_name : str, optional
            Script name.
        sub_folder : str, optional
            If specified, the script is stored within this sub folder.
        f_stream : IO
            The object can be initialized with another preexisting object.
            `f_stream` corresponds to an already opened output stream.
        """
        if f_stream is not None:
            self.f_stream = f_stream
        else:
            self.script_name = script_name
            if sub_folder is not None:
                self.f_stream = open(os.path.join(
                    os.getcwd(), "",
                    sub_folder, "",
                    self.script_name), "w")
            else:
                self.f_stream = open(self.script_name, "w")
        self.indentation_level = 0

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
