from __future__ import annotations

import time
from pathlib import Path
from typing import Protocol, runtime_checkable


@runtime_checkable
class LogOutput(Protocol):
    """
    Protocol for output streams.
    """
    def create(self, columns: list[str], sep: str) -> None: ...

    def write_row(self, values: list[str], sep: str) -> None: ...

    def close(self) -> None: ...


class FileLogOutput(LogOutput):
    """Writes rows to a delimited text file on disk."""

    def __init__(self, file_name: str | Path, mode: str = "w"):
        self.file_name = Path(file_name)
        self.mode = mode
        self._file = None

    def create(self, columns: list[str], sep: str) -> None:
        """Open the file and write the header line."""
        self._file = self.file_name.open(self.mode, encoding="utf-8",)
        self._file.write(sep.join(columns) + "\n")

    def write_row(self, values: list[str], sep: str) -> None:
        """Append one data row."""
        if self._file is None:
            raise FileNotFoundError("File does not exist!")

        self._file.write(sep.join(values) + "\n")

    def close(self) -> None:
        """Close the file handle."""
        if self._file:
            self._file.close()
            self._file = None


class DictLogOutput(LogOutput):
    """
    Accumulates rows in memory.

    After logging, ``.data`` is ``{column_name: [value, value, ...]}``
    - one list per column, one entry per logged event.
    """

    def __init__(self):
        self.data: dict[str, list[str]] = {}

    def create(self, columns: list[str], sep: str | None = None) -> None:
        """Initialise an empty list for every column."""
        self.data = {col: [] for col in columns}

    def write_row(self, values: list[str], sep: str | None = None) -> None:
        """Append each value to its column's list."""
        for col, val in zip(self.data, values):
            self.data[col].append(val)

    def close(self) -> None:
        """Nothing to flush."""

@runtime_checkable
class ClockInterface(Protocol):
    """
    Protocol for the implementation of clocks. The logger requires as
    getTime() method for time logging. It should return a float or int.
    """

    def getTime(self) -> float | int: ...


class SystemClock(ClockInterface):
    """
    Simple Clock not really intended for use in experiments.
    But I does the trick for testing etc.
    """

    def getTime(self) -> float:
        return time.time()

