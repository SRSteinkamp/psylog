import math
from numbers import Real
from typing import Any

from .log_schema import LogMode


def update_state_categories(info_dict: dict, categories_dict: dict) -> None:
    """
    Helper function to update state categories during a log-event.

    Parameters
    ----------
    info_dict : dict
        The new information coming in during a trial.
    categories_dict : dict
        The dictionary of the logger class containing the name: category pairs.
    """
    if info_dict is not None:
        for key, value in info_dict.items():
            category = categories_dict[key]
            if category.mode == LogMode.STATE:
                category.set_state(value)

def create_default_dictionary(categories: dict, implied_handlers: dict, na_value: str) -> dict:

    tmp_dict = {}
    for c in categories:
        if c.mode == LogMode.IMPLIED:
            handler = implied_handlers.get(c.name)
            tmp_dict[c.name] = handler() if handler else na_value
        elif c.mode in (LogMode.STATE, LogMode.STATIC):
            tmp_dict[c.name] = c.state
        else:
            tmp_dict[c.name] = na_value

    return tmp_dict


def handle_onsets(onset: float | None, tmp_dict: dict) -> dict:

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

    return tmp_dict


def add_logging_info(tmp_dict: dict, info_dict: dict, categories_dict: dict) -> dict:

    for key, value in info_dict.items():
        if value is not None:
            category = categories_dict[key]
            if not category.validator.validate(value):
                raise ValueError(f"Invalid value {value!r} for {key}")

            # For EVENT mode, use the provided value directly
            if category.mode == LogMode.EVENT:
                tmp_dict[key] = value

    return tmp_dict


def serialize_value(value: Any, na: str = "n/a") -> str:
    """Serialize a value for a BIDS-compatible TSV file."""
    if value is None:
        return na

    if isinstance(value, Real) and math.isnan(value):
        return na

    return str(value)