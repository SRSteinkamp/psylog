from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING, Any

from .log_schema import CategoryConfig

if TYPE_CHECKING:
    # This is to provide cyclical imports.
    from .base import BaseLogger

ImpliedHandler = Callable[
    ["BaseLogger", CategoryConfig],
    Any,
]

def default_onset_handler(logger: BaseLogger, category: CategoryConfig) -> float:
    """Simple handler for onset times"""
    return logger.get_time()


def default_trial_time_handler(logger: BaseLogger, category: CategoryConfig) -> float | str:
    """Simple handler for trial time"""
    current_trial_time = logger.get_trial_time()

    if current_trial_time is None:
        return logger.na
    else:
        return current_trial_time