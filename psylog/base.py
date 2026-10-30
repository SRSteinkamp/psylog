from __future__ import annotations

import warnings
from pathlib import Path
from typing import Any

from .interfaces import (
    ClockInterface,
    DictLogOutput,
    FileLogOutput,
    LogOutput,
    SystemClock,
)
from .log_handler import (
    ImpliedHandler,
    default_onset_handler,
    default_trial_time_handler,
)
from .log_schema import CategoryConfig, LogMode
from .log_utils import (
    add_logging_info,
    create_default_dictionary,
    handle_onsets,
    serialize_value,
    update_state_categories,
)
from .schema_helper import (
    create_static_fields,
    get_mandatory_bids_events,
    get_psychopy_fields,
    validate_and_build_categories,
)


class BaseLogger:
    """
    BaseLogger class, should take care of most basic logging and be useful
    on its own for many kinds of studies and experiments.
    """

    def __init__(
        self,
        file_name: str | Path | None,
        sep: str = "\t",
        na: str = "n/a",
        clock: ClockInterface = None,
        trial_clock: ClockInterface = None,
        categories: list[CategoryConfig] | None = None,
        static_columns: dict[str: Any] | None = None,
        output: LogOutput | None = None,
    ):
        """
        BaseLogger Class.

        Parameters
        ----------
        file_name : str | Path | None
            The output path to the file. Can be None, then a DictLogOutput
            logger will be used, if a file_name is provided, a FileLogOutput
            instance will be create. If a LogOutput class is provided,
            file_name will be ignored.
        sep : str, optional
            Separator for the logfile, by default "\t", will be ignored when
            output is provided.
        na : str, optional
            The "na" value in the output file, by default "n/a", will be ignored
            when output is provided.
        clock : ClockInterface, optional
            The clock that is used in the experiment, can ideally be reset to the
            start of the experiment, by default None and a SystemClock will be
            created.
        trial_clock : ClockInterface, optional
            Optional clock that can be reset a trial start using set_trial_start, by default None,
            i.e. the logger clock will be used.
        categories : list[CategoryConfig] | None, optional
            List of logging categories, by default None, uses BIDS defaults
            (onset, duration, trial_type).
        static_columns : dict | None, optional
            A dictionary of columns with static values, e.g., participant_id etc. By default None
        output : LogOutput | None, optional
            A OutputLog class if provided, will overwrite file_name. By default None
        """
        self.MANDATORY_CATEGORIES = {"onset", "duration"} # I think these are used for implied calculations.

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
            self.categories.extend(create_static_fields(static_columns))

        self.categories_dict = validate_and_build_categories(categories=categories, mandatory_categories=self.MANDATORY_CATEGORIES)

        self.implied_handlers = {}
        self.add_implied_handler("onset", default_onset_handler)

        if "trial_time" in self.categories_dict:
            self.add_implied_handler("trial_time", default_trial_time_handler)

        # Initialize file state
        if output is None:
            if file_name is None:
                self._output = DictLogOutput()
            else:
                self._output = FileLogOutput(file_name=file_name)
        else:
            warnings.warn("Output has been provided. Ignoring file_name input.")
            self._output = output

        self.trial_clock = trial_clock
        self._trial_start = None

    def log_event(self, info_dict: dict, onset: float | None = None) -> None:

        """
        Log an event with proper BIDS categories.

        Parameters
        ----------
        info_dict : Dict
            Dictionary of category values
        onset : float, optional
            Event onset time (overrides automatic event and calculates duration), by default None
        """

        # Validate all keys exist
        unknown = set(info_dict) - set(self.categories_dict)
        if unknown:
            raise ValueError(f"Unknown categories: {unknown}")

        if onset is not None and "onset" in info_dict:
            warnings.warn("Onset is present in both info_dict and provided as argument. This will lead to unintended" \
            "consequences!")
        elif "onset" in info_dict:
            warnings.warn("Onset has been provided in info_dict, which will override default onset handling!")

        # Update state for STATE-mode categories BEFORE creating temp_dict
        update_state_categories(info_dict, self.categories_dict)

        # Create base dictionary with default values
        tmp_dict = create_default_dictionary(self, categories=self.categories_dict,
                                             implied_handlers=self.implied_handlers,
                                             na_value=self.na)
        # Handle custom onset and calculate duration if needed
        tmp_dict = handle_onsets(onset, tmp_dict)

        # Update with provided values - special handling for EVENT mode
        tmp_dict = add_logging_info(tmp_dict=tmp_dict, info_dict=info_dict, categories_dict=self.categories_dict)

        # Write to file
        self._output.write_row(
            [serialize_value(tmp_dict[c.name], self.na) for c in self.categories], self.sep
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


    def get_trial_time(self) -> float | None:
        if self.trial_clock is not None:
            return self.trial_clock.getTime()

        if self._trial_start is not None:
            return self.get_time() - self._trial_start

        return None

    def add_implied_handler(self, category_name: str, handler_func: ImpliedHandler) -> None:

        if category_name not in self.categories_dict:
            raise ValueError(f"{category_name} not in provided categories!")

        if self.categories_dict[category_name].mode != LogMode.IMPLIED:
            raise ValueError(f"{category_name} has mode: {self.categories_dict[category_name].mode}, it should be {LogMode.IMPLIED}")

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
            return self.implied_handlers[category_name](self, self.categories_dict[category_name])

        return self.na

    def get_bids_sidecar(self) -> dict:
        """Generate BIDS sidecar metadata."""
        return {c: cat.to_bids_dict() for c, cat in self.categories_dict.items()}


class PsychoPyLogger(BaseLogger):
    """
    PsychoPy-specific logger that extends BaseLogger with PsychoPy-specific
    functionality, including trial tracking and PsychoPy-specific categories.
    """

    def __init__(
        self,
        file_name: str | Path | None,
        sep: str = "\t",
        na: str = "n/a",
        clock: ClockInterface | None = None,
        trial_clock: ClockInterface | None = None,
        categories: list[CategoryConfig] | None = None,
        static_columns: dict[str, Any] | None = None,
        output: LogOutput | None = None,
    ) -> None:
        """
        Logger tailored (and tested) for PsychoPy. Has the same arguments
        as the BaseLogger but has a few more default categories. And has
        a start_trial method, that increases trial number and resets the
        trial clock.

        Parameters
        ----------
        file_name : str | Path | None
            The output path to the file. Can be None, then a DictLogOutput
            logger will be used, if a file_name is provided, a FileLogOutput
            instance will be create. If a LogOutput class is provided,
            file_name will be ignored.
        sep : str, optional
            Separator for the logfile, by default "\t", will be ignored when
            output is provided.
        na : str, optional
            The "na" value in the output file, by default "n/a", will be ignored
            when output is provided.
        clock : ClockInterface, optional
            The clock that is used in the experiment, can ideally be reset to the
            start of the experiment, by default None and a SystemClock will be
            created.
        trial_clock : ClockInterface, optional
            Optional clock that can be reset a trial start using set_trial_start, by default None,
            i.e. the logger clock will be used.
        categories : list[CategoryConfig] | None, optional
            List of logging categories, by default None, uses BIDS defaults
            (onset, duration, trial_type).
        static_columns : dict | None, optional
            A dictionary of columns with static values, e.g., participant_id etc. By default None
        output : LogOutput | None, optional
            A OutputLog class if provided, will overwrite file_name. By default None
        """
        if categories is None:
            categories = (
                get_mandatory_bids_events()
                + get_psychopy_fields()
            )

        super().__init__(
            file_name=file_name,
            sep=sep,
            na=na,
            clock=clock,
            trial_clock=trial_clock,
            categories=categories,
            static_columns=static_columns,
            output=output,
        )

        self.current_trial = -1
        self._trial_start = None

    def start_trial(self, trial_number: int | None = None):
        """
        Function to indicate a new trial. Also calls "set_trial_time" to reset
        internal trial clocks.

        Parameters
        ----------
        trial_number : int | None, optional
            Overwrite trial_number, otherwise it will increase by 1, by default None
        """

        if trial_number is not None:
            self.current_trial = trial_number
        else:
            self.current_trial += 1

        self.set_trial_time()

        # Update trial state category if it exists
        if "trial" in self.categories_dict:
            self.categories_dict["trial"].set_state(self.current_trial)
