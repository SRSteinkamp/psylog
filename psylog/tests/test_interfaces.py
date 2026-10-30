
import time
from pathlib import Path
from unittest.mock import Mock

import pytest

from psylog.interfaces import (
    LogOutput,
    FileLogOutput,
    DictLogOutput,
    ClockInterface,
    SystemClock,
)


# -------------------------------------------------------------------
# LogOutput protocol
# -------------------------------------------------------------------

def test_file_log_output_implements_protocol(tmp_path):
    output = FileLogOutput(tmp_path / "test.csv")

    assert isinstance(output, LogOutput)


def test_dict_log_output_implements_protocol():
    output = DictLogOutput()

    assert isinstance(output, LogOutput)


# -------------------------------------------------------------------
# FileLogOutput
# -------------------------------------------------------------------

def test_file_log_output_create_writes_header(tmp_path):
    file_path = tmp_path / "test.csv"
    output = FileLogOutput(file_path)

    output.create(["name", "age", "city"], ",")

    output.close()

    assert file_path.read_text(encoding="utf-8") == (
        "name,age,city\n"
    )


def test_file_log_output_write_row(tmp_path):
    file_path = tmp_path / "test.csv"
    output = FileLogOutput(file_path)

    output.create(["name", "age"], ",")
    output.write_row(["Alice", "30"], ",")
    output.write_row(["Bob", "25"], ",")
    output.close()

    assert file_path.read_text(encoding="utf-8") == (
        "name,age\n"
        "Alice,30\n"
        "Bob,25\n"
    )


def test_file_log_output_supports_custom_separator(tmp_path):
    file_path = tmp_path / "test.txt"
    output = FileLogOutput(file_path)

    output.create(["name", "age"], ";")
    output.write_row(["Alice", "30"], ";")
    output.close()

    assert file_path.read_text(encoding="utf-8") == (
        "name;age\n"
        "Alice;30\n"
    )


def test_file_log_output_write_without_create_raises(tmp_path):
    output = FileLogOutput(tmp_path / "test.csv")

    with pytest.raises(FileNotFoundError, match="File does not exist!"):
        output.write_row(["Alice", "30"], ",")


def test_file_log_output_close_without_create(tmp_path):
    output = FileLogOutput(tmp_path / "test.csv")

    # Should not raise an exception.
    output.close()


def test_file_log_output_close_twice(tmp_path):
    output = FileLogOutput(tmp_path / "test.csv")

    output.create(["name"], ",")
    output.close()

    # Closing an already closed output should be safe.
    output.close()

    assert output._file is None


def test_file_log_output_file_handle_is_closed(tmp_path):
    output = FileLogOutput(tmp_path / "test.csv")

    output.create(["name"], ",")
    file_handle = output._file

    output.close()

    assert file_handle.closed
    assert output._file is None


def test_file_log_output_accepts_path_object(tmp_path):
    file_path = tmp_path / "test.csv"
    output = FileLogOutput(file_path)

    assert output.file_name == file_path
    assert isinstance(output.file_name, Path)


def test_file_log_output_accepts_string_path(tmp_path):
    file_path = str(tmp_path / "test.csv")
    output = FileLogOutput(file_path)

    assert output.file_name == Path(file_path)


def test_file_log_output_append_mode(tmp_path):
    file_path = tmp_path / "test.csv"

    file_path.write_text("existing data\n", encoding="utf-8")

    output = FileLogOutput(file_path, mode="a")
    output.create(["name", "age"], ",")
    output.write_row(["Alice", "30"], ",")
    output.close()

    assert file_path.read_text(encoding="utf-8") == (
        "existing data\n"
        "name,age\n"
        "Alice,30\n"
    )


def test_file_log_output_empty_columns(tmp_path):
    file_path = tmp_path / "test.csv"
    output = FileLogOutput(file_path)

    output.create([], ",")
    output.close()

    assert file_path.read_text(encoding="utf-8") == "\n"


def test_file_log_output_empty_row(tmp_path):
    file_path = tmp_path / "test.csv"
    output = FileLogOutput(file_path)

    output.create(["name"], ",")
    output.write_row([], ",")
    output.close()

    assert file_path.read_text(encoding="utf-8") == "name\n\n"


# -------------------------------------------------------------------
# DictLogOutput
# -------------------------------------------------------------------

def test_dict_log_output_create_initialises_columns():
    output = DictLogOutput()

    output.create(["name", "age", "city"])

    assert output.data == {
        "name": [],
        "age": [],
        "city": [],
    }


def test_dict_log_output_write_row():
    output = DictLogOutput()

    output.create(["name", "age"])
    output.write_row(["Alice", "30"])

    assert output.data == {
        "name": ["Alice"],
        "age": ["30"],
    }


def test_dict_log_output_write_multiple_rows():
    output = DictLogOutput()

    output.create(["name", "age"])
    output.write_row(["Alice", "30"])
    output.write_row(["Bob", "25"])
    output.write_row(["Charlie", "40"])

    assert output.data == {
        "name": ["Alice", "Bob", "Charlie"],
        "age": ["30", "25", "40"],
    }


def test_dict_log_output_create_resets_data():
    output = DictLogOutput()

    output.create(["name", "age"])
    output.write_row(["Alice", "30"])

    output.create(["city"])

    assert output.data == {
        "city": [],
    }


def test_dict_log_output_empty_columns():
    output = DictLogOutput()

    output.create([])

    assert output.data == {}


def test_dict_log_output_empty_row():
    output = DictLogOutput()

    output.create(["name", "age"])
    output.write_row([])

    assert output.data == {
        "name": [],
        "age": [],
    }


def test_dict_log_output_fewer_values_than_columns():
    output = DictLogOutput()

    output.create(["name", "age", "city"])
    output.write_row(["Alice", "30"])

    assert output.data == {
        "name": ["Alice"],
        "age": ["30"],
        "city": [],
    }


def test_dict_log_output_more_values_than_columns():
    output = DictLogOutput()

    output.create(["name", "age"])
    output.write_row(["Alice", "30", "Berlin"])

    assert output.data == {
        "name": ["Alice"],
        "age": ["30"],
    }


def test_dict_log_output_close_does_nothing():
    output = DictLogOutput()

    output.create(["name"])
    output.write_row(["Alice"])

    output.close()

    assert output.data == {
        "name": ["Alice"],
    }


def test_dict_log_output_accepts_separator_argument():
    output = DictLogOutput()

    output.create(["name", "age"], ",")
    output.write_row(["Alice", "30"], ",")

    assert output.data == {
        "name": ["Alice"],
        "age": ["30"],
    }


# -------------------------------------------------------------------
# ClockInterface
# -------------------------------------------------------------------

def test_system_clock_implements_clock_interface():
    clock = SystemClock()

    assert isinstance(clock, ClockInterface)


def test_system_clock_returns_float():
    clock = SystemClock()

    result = clock.getTime()

    assert isinstance(result, float)


def test_system_clock_returns_current_time(monkeypatch):
    expected_time = 1234567890.5

    monkeypatch.setattr(time, "time", lambda: expected_time)

    clock = SystemClock()

    assert clock.getTime() == expected_time


def test_system_clock_calls_time_each_invocation(monkeypatch):
    times = iter([100.0, 200.0, 300.0])

    monkeypatch.setattr(time, "time", lambda: next(times))

    clock = SystemClock()

    assert clock.getTime() == 100.0
    assert clock.getTime() == 200.0
    assert clock.getTime() == 300.0


# -------------------------------------------------------------------
# Protocol-compatible mock clock
# -------------------------------------------------------------------

def test_mock_clock_implements_clock_interface():
    clock = Mock(spec=ClockInterface)
    clock.getTime.return_value = 123.45

    assert isinstance(clock, ClockInterface)
    assert clock.getTime() == 123.45


def test_mock_clock_can_return_integer():
    clock = Mock(spec=ClockInterface)
    clock.getTime.return_value = 42

    assert clock.getTime() == 42
    assert isinstance(clock.getTime(), int)
