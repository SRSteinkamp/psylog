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
                f"Default {self.default!r} fails validator {self.validator}"
            )

    def set_state(self, new_state: Any) -> None:
        if not self.validator.validate(new_state):
            raise ValueError(
                f"New state {new_state!r} fails validator {self.validator}"
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


def get_rewardmap_defaults():
    return [
        CategoryConfig(
            "task",
            "hcp",
            mode=LogMode.STATIC,
            description="Task name",
            units="n/a",
        ),
        CategoryConfig(
            "seq_tr",
            0.752,
            mode=LogMode.EVENT,
            description="MRI sequence repetition time",
            units="seconds",
            validator=Validator(float),
        ),
        CategoryConfig(
            "response_late",
            "n/a",
            mode=LogMode.EVENT,
            description="Whether response was too late",
            units="n/a",
        ),
        CategoryConfig(
            "action",
            "n/a",
            mode=LogMode.EVENT,
            description="Action taken by participant",
            units="n/a",
        ),
        CategoryConfig(
            "reward",
            0,
            mode=LogMode.EVENT,
            description="Reward received",
            units="arbitrary unit",
            validator=Validator(float),
        ),
        CategoryConfig(
            "current_location",
            "n/a",
            mode=LogMode.STATE,
            description="Current location in environment",
            units="n/a",
        ),
        CategoryConfig(
            "total_reward",
            "n/a",
            mode=LogMode.STATE,
            description="Cumulative reward received",
            units="arbitrary unit",
            validator=Validator(float),
        ),
        CategoryConfig(
            "avail_actions",
            "n/a",
            mode=LogMode.EVENT,
            description="Available actions at this point",
            units="n/a",
        ),
        CategoryConfig(
            "misc",
            "n/a",
            mode=LogMode.STATE,
            description="Miscellaneous information",
            units="n/a",
        ),
        CategoryConfig(
            "TR",
            0,
            mode=LogMode.IMPLIED,
            description="MRI volume acquisition number",
            units="n/a",
            validator=Validator(int),
        ),
        CategoryConfig(
            "expected_duration",
            "n/a",
            mode=LogMode.EVENT,
            description="Expected duration of event",
            units="seconds",
            validator=Validator(float),
        ),
        CategoryConfig(
            "start_position",
            "n/a",
            mode=LogMode.STATE,
            description="Starting position for trial",
            units="n/a",
        ),
        CategoryConfig(
            "rl_label",
            "n/a",
            mode=LogMode.EVENT,
            description="Reinforcement learning label",
            units="n/a",
        ),
    ]


def get_logger_defaults():
    return [
        CategoryConfig(
            "participant_id",
            "n/a",
            mode=LogMode.STATIC,
            description="Participant identifier",
            units="n/a",
            validator=Validator(str),
        ),
        CategoryConfig(
            "run",
            1,
            mode=LogMode.STATIC,
            description="Run number within session",
            units="n/a",
            validator=Validator(int),
        ),
        CategoryConfig(
            "trial_type",
            "n/a",
            mode=LogMode.EVENT,
            description="BIDS is a bit weird in this regard, so this is now the specific event in the trial.",
            units="n/a",
        ),
        CategoryConfig(
            "condition",
            "n/a",
            mode=LogMode.STATE,
            description="Type of the trial, e.g., the condition in ",
            units="n/a",
        ),
        CategoryConfig(
            "response_time",
            "n/a",
            mode=LogMode.EVENT,
            description="Time between stimulus and response",
            units="seconds",
            validator=Validator(float),
        ),
        CategoryConfig(
            "response_button",
            "n/a",
            mode=LogMode.EVENT,
            description="Button pressed in response",
            units="n/a",
        ),
        CategoryConfig(
            "onset",
            None,
            mode=LogMode.IMPLIED,
            description="Event onset time",
            units="seconds",
            validator=Validator(float),
        ),
        CategoryConfig(
            "duration",
            None,
            mode=LogMode.IMPLIED,
            description="Event duration",
            units="seconds",
            validator=Validator(float),
        ),
        CategoryConfig(
            "trial_time",
            None,
            mode=LogMode.IMPLIED,
            description="Time since trial start",
            units="seconds",
            validator=Validator(float),
        ),
    ]
