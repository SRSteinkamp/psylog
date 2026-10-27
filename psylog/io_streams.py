from typing import Dict, List


class FileLogOutput:
    """Writes rows to a delimited text file on disk."""

    def __init__(self, file_name: str, mode: str = "w"):
        self.file_name = file_name
        self.mode = mode
        self._file = None

    def create(self, columns: List[str], sep: str) -> None:
        """Open the file and write the header line."""
        self._file = open(self.file_name, self.mode)
        self._file.write(sep.join(columns) + "\n")

    def write_row(self, values: List[str], sep: str) -> None:
        """Append one data row."""
        if self._file is None:
            raise FileNotFoundError("File does not exist!")

        self._file.write(sep.join(values) + "\n")

    def close(self) -> None:
        """Close the file handle."""
        if self._file:
            self._file.close()
            self._file = None


class DictLogOutput:
    """
    Accumulates rows in memory.

    After logging, ``.data`` is ``{column_name: [value, value, ...]}``
    – one list per column, one entry per logged event.
    """

    def __init__(self):
        self.data: Dict[str, List[str]] = {}

    def create(self, columns: List[str], sep: str) -> None:
        """Initialise an empty list for every column."""
        self.data = {col: [] for col in columns}

    def write_row(self, values: List[str], sep: str) -> None:
        """Append each value to its column's list."""
        for col, val in zip(self.data, values):
            self.data[col].append(val)

    def close(self) -> None:
        """Nothing to flush."""
