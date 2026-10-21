from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, Iterable, Type, Union


class LogMode(Enum):
    """Controls how a category is handled in logging"""

    STATIC = "static"  # Always included in output, does not change during the experiment. E.g. participant id and similar.
    EVENT = "event"  # Provided by user. Otherwise defaults to NaN
    IMPLIED = "implied"  # These use specific functions, e.g. clocks of the Logger, so handle with care.
    STATE = "state"  # Takes on a state, that is being logged continuously, states can be overwritten by user.


class Validator:
    """
    Flexible validation for category values.
    Always allows "n/a" unless explicitly disabled.
    """

    def __init__(
        self,
        validator: Union[Type, Iterable, Callable, None] = None,
        allow_na: bool = True,
    ):
        """
        Parameters:
        -----------
        validator : type, iterable, callable, or None
            - type: Check if value is instance of type (int, float, str)
            - iterable: Check if value is in allowed values list
            - callable: Custom validation function
            - None: No validation (except "n/a" if allow_na=True)
        allow_na : bool
            Whether to allow "n/a" as a valid value
        """

        self.allow_na = allow_na
        self.validator = validator

    def validate(self, value: Any) -> bool:
        """Check if value is valid"""
        if value == "n/a" and self.allow_na:
            return True

        if self.validator is None:
            return True

        if isinstance(self.validator, type):
            return isinstance(value, self.validator)
        elif isinstance(self.validator, (list, tuple, set)):
            return value in self.validator
        elif callable(self.validator):
            return self.validator(value)
        return False

    def __eq__(self, other):
        if not isinstance(other, Validator):
            return NotImplemented
        return self.validator == other.validator and self.allow_na == other.allow_na

    def __repr__(self):
        if self.validator is None:
            return "Validator(allow_na=True)"
        return f"Validator(validator={self.validator}, allow_na={self.allow_na})"


@dataclass
class CategoryConfig:
    name: str
    default: Any
    mode: LogMode = LogMode.EVENT
    validator: Validator = field(default_factory=lambda: Validator(allow_na=True))
    description: str = ""
    units: str = "n/a"
    long_name: str = ""

    def __post_init__(self):
        if self.validator is None:
            self.validator = Validator(allow_na=True)

        self._validate_config()
        self.state: Any = deepcopy(self.default)

    def _validate_config(self) -> None:
        if not isinstance(self.name, str) or not self.name:
            raise ValueError(
                f"Category name must be non-empty string, got {self.name!r}"
            )
        if not isinstance(self.mode, LogMode):
            raise TypeError(f"Invalid mode {self.mode!r}, must be LogMode enum")
        if not self.validator.validate(self.default):
            raise TypeError(
                f"Default {self.default!r} fails validator {self.validator} for {self.name}"
            )

    def set_state(self, new_state: Any) -> None:
        if not self.validator.validate(new_state):
            raise ValueError(
                f"New state {new_state!r} fails validator {self.validator}  for {self.name}"
            )
        self.state = new_state

    def to_bids_dict(self) -> Dict[str, Any]:
        d: Dict[str, Any] = {
            "Description": self.description,
            "LongName": self.long_name,
            "Units": self.units,  # ← use the field the user set
        }
        v = self.validator.validator
        if isinstance(v, (list, tuple, set)):
            d["Levels"] = {str(val): "" for val in v}
        return d
