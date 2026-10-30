from __future__ import annotations

import math
from copy import deepcopy
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class LogMode(Enum):
    """Controls how a category is handled in logging"""

    STATIC = "static"  # Always included in output, does not change during the experiment. E.g. participant id and similar.
    EVENT = "event"  # Provided by user. Otherwise defaults to NaN
    IMPLIED = "implied"  # These use specific functions, e.g. clocks of the Logger, so handle with care.
    STATE = "state"  # Takes on a state, that is being logged continuously, states can be overwritten by user.


@dataclass
class CategoryConfig:
    name: str
    default: Any
    mode: LogMode = LogMode.EVENT

    # Validation
    data_type: type | tuple[type, ...] | None = None
    allow_na: bool = True

    # BIDS metadata
    description: str = ""
    units: str = "n/a"
    long_name: str = ""

    # Levels
    levels: dict[str, str] = field(default_factory=dict)
    validate_levels: bool = False
    collect_levels: bool = False


    def __post_init__(self):
        self._validate_config()
        self.state = deepcopy(self.default)


    def validate(self, value: Any) -> bool:
        if self._is_missing(value):
            return self.allow_na

        if self.data_type is not None and not isinstance(value, self.data_type):
            return False

        return not (self.validate_levels and self.levels and str(value) not in self.levels)


    def _validate_config(self) -> None:

        if self.data_type is not None:
            if not isinstance(self.data_type, (type, tuple)):
                raise TypeError("data_type must be a type, tuple of types, or None")

            if isinstance(self.data_type, tuple) and not all(
                isinstance(t, type) for t in self.data_type):
                raise TypeError("All data_type entries must be types")

        if not isinstance(self.name, str) or not self.name:
            raise ValueError("Category name must be a non-empty string")

        if not isinstance(self.mode, LogMode):
            raise TypeError("Invalid category mode")

        if not self.validate(self.default):
            raise ValueError(
                f"Default {self.default!r} is invalid for {self.name!r}"
            )

        if self.validate_levels and not self.levels:
            raise ValueError(
                "validate_levels requires at least one predefined level"
            )

    def record_value(self, value: Any) -> None:
        """Record an encountered value as a BIDS level."""
        if not self.collect_levels or self._is_missing(value):
            return

        self.levels.setdefault(str(value), "")


    def set_state(self, new_state: Any) -> None:
        if not self.validate(new_state):
            raise ValueError(
                f"Invalid state {new_state!r} for category {self.name!r}"
            )

        self.state = new_state
        self.record_value(new_state)

    def to_bids_dict(self) -> dict[str, Any]:
        result = {
            "Description": self.description,
            "LongName": self.long_name,
            "Units": self.units,
        }

        if self.levels:
            result["Levels"] = dict(sorted(self.levels.items()))

        return result


    def _is_missing(self, value: Any) -> bool:
        if value is None:
            return True

        if isinstance(value, float) and math.isnan(value):
            return True

        return isinstance(value, str) and value == "n/a"