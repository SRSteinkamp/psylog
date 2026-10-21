from __future__ import annotations

import time
from typing import Any, Callable, Dict, List, Optional

from .io_streams import FileLogOutput
from .log_schema import LogMode
from .schema_helper import (
    create_static_fields,
    get_mandatory_bids_events,
    get_psychopy_fields,
)


class SystemClock:
    """Default clock using Python's time module"""

    def getTime(self) -> float:
        return time.time()


class ParentLogger:
    """
    Minimal BIDS-compliant logger parent class.
    Contains only the essential categories required by BIDS specification.
    """

    def __init__(
        self,
        file_name: str,
        sep: str = "\t",
        na: str = "n/a",
        clock=None,
        categories: Optional[List] = None,
        static_columns: Optional[Dict] = None,
        output=None,
    ):
        """
        Initialize minimal BIDS-compliant logger.

        Parameters
        ----------
        file_name : str
            Output file name
        sep : str, optional
            Column separator, by default "\t"
        na : str, optional
            Missing value representation, by default "n/a"
        """
        self.file_name = file_name
        self.sep = sep
        self.na = na

        self.clock = clock if clock is not None else SystemClock()
        # Create minimal required categories (BIDS specification)
        if categories is None:
            self.categories = get_mandatory_bids_events()
        else:
            self.categories = categories

        if static_columns is not None:
            self.categories = self.categories + create_static_fields(static_columns)

        self.categories_dict = {c.name: c for c in self.categories}

        # Create nan dictionary
        self.nan_dict = {c.name: self.na for c in self.categories}

        self.implied_handlers = {
            "onset": self._default_onset_handler,
            "trial_time": self._default_trial_time_handler,
        }

        # Initialize file state
        self._output = output if output is not None else FileLogOutput(file_name)

        self._trial_start = None

    def log_event(self, info_dict: Dict, onset: float = None) -> None:
        """
        Log an event with proper BIDS categories.

        Parameters
        ----------
        info_dict : Dict
            Dictionary of category values
        onset : float, optional
            Event onset time (overrides automatic), by default None
        """
        # Validate all keys exist
        unknown = set(info_dict) - set(self.categories_dict)
        if unknown:
            raise ValueError(f"Unknown categories: {unknown}")

        # Update state for STATE-mode categories BEFORE creating temp_dict
        if info_dict is not None:
            for key, value in info_dict.items():
                category = self.categories_dict[key]
                if category.mode == LogMode.STATE:
                    category.set_state(value)

        # Create base dictionary with default values
        tmp_dict = {}
        for c in self.categories:
            if c.mode == LogMode.IMPLIED:
                handler = self.implied_handlers.get(c.name)
                tmp_dict[c.name] = handler() if handler else self.na
            elif c.mode in (LogMode.STATE, LogMode.STATIC):
                tmp_dict[c.name] = c.state
            else:
                tmp_dict[c.name] = self.na

        # Handle custom onset and calculate duration if needed
        if onset is not None:
            if onset <= tmp_dict.get("onset", float("inf")):
                # Calculate duration if we're overriding onset
                if "onset" in tmp_dict and "duration" in tmp_dict:
                    tmp_dict["duration"] = tmp_dict["onset"] - onset
                tmp_dict["onset"] = onset
            else:
                raise ValueError(
                    "User defined onset needs to be before automatic onset!"
                )

        # Update with provided values - special handling for EVENT mode
        for key, value in info_dict.items():
            if value is not None:
                category = self.categories_dict[key]
                if not category.validator.validate(value):
                    raise ValueError(f"Invalid value {value!r} for {key}")

                # For EVENT mode, use the provided value directly
                if category.mode == LogMode.EVENT:
                    tmp_dict[key] = value
        # Write to file
        self._output.write_row(
            [str(tmp_dict[c.name]) for c in self.categories], self.sep
        )

    def get_time(self) -> float:
        """Get current time from clock object"""
        return self.clock.getTime()

    def create(self) -> None:
        """Open the output backend and write the column header."""
        self._output.create([c.name for c in self.categories], self.sep)

    def close(self) -> None:
        """Close the output backend."""
        self._output.close()

    def set_trial_time(self) -> None:
        """Set trial start time."""
        self._trial_start = self.get_time()

    def get_bids_sidecar(self) -> Dict:
        """Generate BIDS sidecar metadata."""
        return {
            c.name: {
                "Description": c.description,
                "LongName": c.long_name,
                "Units": c.units,
                **(
                    {
                        "Levels": {str(v): "" for v in c.validator.validator}
                        if isinstance(c.validator.validator, (list, tuple, set))
                        else {}
                    }
                ),
            }
            for c in self.categories
        }

    def _default_onset_handler(self) -> float:
        """Simple handler for onset times"""
        return self.get_time()

    def _default_trial_time_handler(self) -> float:
        """Simple handler for trial time"""
        if hasattr(self, "_trial_start") and self._trial_start is not None:
            return self.get_time() - self._trial_start

        return self.na

    def add_implied_handler(
        self, category_name: str, handler_func: Callable[[], Any]
    ) -> None:
        """
        Add a simple handler for an IMPLIED category.

        Parameters
        ----------
        category_name : str
            Name of the category to handle
        category_handler : Callable[[], Any]
            Function that returns the value (takes no arguments)
        """
        self.implied_handlers[category_name] = handler_func

    def _handle_implied_category(self, category_name: str) -> Any:
        """
        Get value for an IMPLIED category using its handler.

        Parameters
        ----------
        category_name : str
            Name of the category

        Returns
        -------
        Any
            The computed value or na
        """
        if category_name in self.implied_handlers:
            return self.implied_handlers[category_name]()
        return self.na


class PsychoPyLogger(ParentLogger):
    """
    PsychoPy-specific logger that extends ParentLogger with PsychoPy-specific functionality.
    Tracks trial number, trial onsets, and integrates with PsychoPy's Clock.
    """

    def __init__(
        self,
        file_name: str,
        global_clock,
        sep: str = "\t",
        na: str = "n/a",
        categories: Optional[List] = None,
        static_columns: Optional[Dict] = None,
    ):
        if categories is None:
            self.categories = get_mandatory_bids_events()
            self.categories += get_psychopy_fields()

        # Initialize ParentLogger
        super().__init__(
            file_name=file_name,
            sep=sep,
            na=na,
            categories=categories,
            static_columns=static_columns,
            clock=global_clock,
        )

        # Experiment parameters
        self.current_trial = -1
        self._trial_start = None

        # Create the file (writes header)
        self.create()

    def start_trial(self, trial_number: int = None):
        """
        Start a new trial.

        Parameters
        ----------
        trial_number : int, optional
            Trial number to set, by default increments current trial
        """
        if trial_number is not None:
            self.current_trial = trial_number
        else:
            self.current_trial += 1

        self._trial_start = self.get_time()

        # Update trial state category if it exists
        if "trial" in self.categories_dict:
            self.categories_dict["trial"].set_state(self.current_trial)
