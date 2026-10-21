from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional

from .log_schema import LogMode
from .schema_helper import create_static_fields, get_mandatory_bids_events


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
        categories: Optional[List] = None,
        static_columns: Optional[Dict] = None,
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
        self._file = None
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

        # Create base dictionary with defaults
        tmp_dict = self._default_logging()

        # Handle onset/duration
        if onset is not None:
            tmp_dict["onset"] = onset

        # Update with provided values
        for key, value in info_dict.items():
            category = self.categories_dict[key]
            if not category.validator.validate(value):
                raise ValueError(f"Invalid value {value!r} for {key}")
            tmp_dict[key] = value

        # Write to file
        self._write_to_file(self._create_log_list(tmp_dict))

    def _default_logging(self) -> Dict:
        """Create dictionary with default values"""
        return {
            c.name: self._handle_implied_category(c.name)
            if c.mode == LogMode.IMPLIED
            else (
                c.state
                if (c.mode == LogMode.STATE or c.mode == LogMode.STATIC)
                else self.na
            )
            for c in self.categories
        }

    def _get_time(self) -> float:
        """Get current time - to be implemented by child classes."""
        raise NotImplementedError("Child classes must implement _get_time()")

    def _create_log_list(self, tmp_dict: Dict) -> List[str]:
        """Convert dictionary to list of strings in category order."""
        return [str(tmp_dict[c.name]) for c in self.categories]

    def _write_to_file(self, values: List[str]) -> None:
        """Write values to file."""
        if not self._file:
            self._file = open(self.file_name, "w")
            self._write_to_file([c.name for c in self.categories])

        self._file.write(self.sep.join(values) + "\n")

    def create(self, mode: str = "w") -> None:
        """Create/open log file."""
        if self._file:
            self._file.close()
        self._file = open(self.file_name, mode)

    def close(self) -> None:
        """Close log file."""
        if self._file:
            self._file.close()
            self._file = None

    def set_trial_time(self) -> None:
        """Set trial start time."""
        self._trial_start = self._get_time()

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
        return self._get_time()

    def _default_trial_time_handler(self) -> float:
        """Simple handler for trial time"""
        if hasattr(self, "_trial_start") and self._trial_start is not None:
            return self._get_time() - self._trial_start

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
