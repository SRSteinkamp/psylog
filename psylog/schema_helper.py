from __future__ import annotations

from typing import Any

from .log_schema import CategoryConfig, LogMode, Validator


def validate_and_build_categories(
    categories: list[CategoryConfig],
    mandatory_categories: set[str],
) -> dict[str, CategoryConfig]:
    """Validate categories and build a category lookup dictionary."""

    names = [category.name for category in categories]

    if len(names) != len(set(names)):
        raise ValueError("Category names must be unique")

    missing = mandatory_categories - set(names)

    if missing:
        raise ValueError(
            f"Missing mandatory logging categories: {sorted(missing)}"
        )

    return {category.name: category for category in categories}


def create_static_fields(
    field_values: dict[str, Any],
    description_template: str = "Static field: {}",
    units: str = "n/a",
) -> list[CategoryConfig]:
    """
    Creates static fields using a dictionary.

    Parameters
    ----------
    field_values : Dict[str, Any]
        A classic dictionary mapping the column name and the column values.
    description_template : _type_, optional
        A template for the "description" in the json car.
        By default "Static field: {}"
    units : str, optional
       The units of the Category, by default "n/a"

    Returns
    -------
    List[CategoryConfig]
        Returns a list of Configs
    """
    return [
        CategoryConfig(
            name=name,
            default=value,
            mode=LogMode.STATIC,
            description=description_template.format(name),
            units=units,
            validator=Validator(type(value))
            if not isinstance(value, (str, int, float))
            else None,
        )
        for name, value in field_values.items()
    ]


def get_mandatory_bids_events(
    onset_units: str = "seconds",
    duration_units: str = "seconds",
    onset_description: str = "Event onset time",
    duration_description: str = "Event duration",
    trial_type_description: str = "The name of the event",
    trial_type_units: str = "n/a",
) -> list[CategoryConfig]:
    """
    Create minimal BIDS-compliant event categories with sensible defaults.

    Parameters
    ----------
    onset_units : str, optional
        Units for onset times, by default "seconds"
    duration_units : str, optional
        Units for durations, by default "seconds"
    onset_description : str, optional
        Description for onset category, by default "Event onset time"
    duration_description : str, optional
        Description for duration category, by default "Event duration"

    Returns
    -------
    List[CategoryConfig]
        List containing onset and duration categories
    """
    return [
        CategoryConfig(
            name="onset",
            default="n/a",
            mode=LogMode.IMPLIED,
            description=onset_description,
            units=onset_units,
            validator=Validator(float),
        ),
        CategoryConfig(
            name="duration",
            default="n/a",
            mode=LogMode.IMPLIED,
            description=duration_description,
            units=duration_units,
            validator=Validator(float),
        ),
        CategoryConfig(
            name="trial_type",
            default="n/a",
            mode=LogMode.EVENT,
            description=trial_type_description,
            units=trial_type_units,
            validator=Validator(str),
        ),
    ]


def get_psychopy_fields() -> list[CategoryConfig]:
    """
    Create minimal BIDS-compliant event categories with sensible defaults.

    Parameters
    ----------
    onset_units : str, optional
        Units for onset times, by default "seconds"
    duration_units : str, optional
        Units for durations, by default "seconds"
    onset_description : str, optional
        Description for onset category, by default "Event onset time"
    duration_description : str, optional
        Description for duration category, by default "Event duration"

    Returns
    -------
    List[CategoryConfig]
        List containing onset and duration categories
    """
    return [
        CategoryConfig(
            name="response_time",
            default="n/a",
            mode=LogMode.EVENT,
            description="Response time",
            units="seconds",
            validator=Validator(float),
        ),
        CategoryConfig(
            name="response_button",
            default="n/a",
            mode=LogMode.EVENT,
            description="The response button being pressed.",
            units="n/a",
            validator=None,
        ),
        CategoryConfig(
            name="trial",
            default=-1,
            mode=LogMode.STATE,
            description="The running trial number",
            units="trials",
            validator=Validator(int),
        ),
        CategoryConfig(
            name="trial_time",
            default="n/a",
            mode=LogMode.IMPLIED,
            description="The running time since trial start.",
            units="seconds",
            validator=Validator(float),
        ),
    ]
