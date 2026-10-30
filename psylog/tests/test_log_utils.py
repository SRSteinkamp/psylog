import pytest

from psylog.log_schema import CategoryConfig, LogMode
from psylog.log_utils import (
    add_logging_info,
    create_default_dictionary,
    handle_onsets,
    serialize_value,
    update_state_categories,
)

# ======================
# Fixtures
# ======================

@pytest.fixture
def static_category():
    return CategoryConfig(
        name="subj_id",
        default="01",
        mode=LogMode.STATIC,
        description="Subject ID"
    )

@pytest.fixture
def state_category():
    return CategoryConfig(
        name="trial_counter",
        default=0,
        mode=LogMode.STATE,
        description="Trial counter"
    )

@pytest.fixture
def event_category():
    return CategoryConfig(
        name="response",
        default=None,
        mode=LogMode.EVENT,
        allow_na=True,
        description="Participant response",
        collect_levels=True
    )

@pytest.fixture
def implied_category():
    return CategoryConfig(
        name="onset",
        default=0.0,
        mode=LogMode.IMPLIED,
        description="Event onset time"
    )

@pytest.fixture
def numeric_event_category():
    return CategoryConfig(
        name="age",
        default=25,
        mode=LogMode.EVENT,
        data_type=(int),
        allow_na=False,
        description="Participant age"
    )

# ======================
# update_state_categories tests
# ======================

def test_update_state_categories_none_info(state_category):
    categories = {"trial_counter": state_category}
    update_state_categories(None, categories)
    assert categories["trial_counter"].state == 0

def test_update_state_categories_state_update(state_category):
    categories = {"trial_counter": state_category}
    info_dict = {"trial_counter": 5}
    update_state_categories(info_dict, categories)
    assert categories["trial_counter"].state == 5

def test_update_state_categories_non_state(event_category):
    categories = {"response": event_category}
    original_state = event_category.state
    info_dict = {"response": "left"}
    update_state_categories(info_dict, categories)
    assert categories["response"].state == original_state  # State shouldn't change for EVENT mode

# ======================
# create_default_dictionary tests
# ======================

def test_create_default_dictionary_static(static_category):
    result = create_default_dictionary(
        None,
        {"subj_id": static_category},
        {},
        "n/a"
    )
    assert result == {"subj_id": "01"}

def test_create_default_dictionary_state(state_category):
    result = create_default_dictionary(
        None,
        {"trial_counter": state_category},
        {},
        "n/a"
    )
    assert result == {"trial_counter": 0}

def test_create_default_dictionary_event(event_category):
    result = create_default_dictionary(
        None,
        {"response": event_category},
        {},
        "n/a"
    )
    assert result == {"response": "n/a"}

def test_create_default_dictionary_implied_with_handler(implied_category):
    implied_handlers = {
        "onset": lambda logger, cat: 1.5
    }
    result = create_default_dictionary(
        None,
        {"onset": implied_category},
        implied_handlers,
        "n/a"
    )
    assert result == {"onset": 1.5}

def test_create_default_dictionary_implied_no_handler(implied_category):
    result = create_default_dictionary(
        None,
        {"onset": implied_category},
        {},
        "n/a"
    )
    assert result == {"onset": "n/a"}

# ======================
# handle_onsets tests
# ======================

def test_handle_onsets_none():
    tmp_dict = {"onset": 1.0, "duration": 2.0}
    result = handle_onsets(None, tmp_dict)
    assert result == tmp_dict

def test_handle_onsets_update():
    tmp_dict = {"onset": 2.0, "duration": 1.0}
    result = handle_onsets(1.0, tmp_dict)
    assert result["onset"] == 1.0
    assert result["duration"] == 1.0  # 2.0 - 1.0 = 1.0

def test_handle_onsets_first_onset():
    tmp_dict = {}
    result = handle_onsets(1.0, tmp_dict)
    assert result == {"onset": 1.0}

def test_handle_onsets_update_no_duration():
    tmp_dict = {"onset": 2.0}
    result = handle_onsets(1.0, tmp_dict)
    assert result["onset"] == 1.0
    assert "duration" not in result

def test_handle_onsets_later_onset():
    tmp_dict = {"onset": 1.0}
    with pytest.raises(ValueError, match="User defined onset needs to be before automatic onset!"):
        handle_onsets(2.0, tmp_dict)

# ======================
# add_logging_info tests
# ======================

def test_add_logging_info_event(event_category):
    categories_dict = {"response": event_category}
    tmp_dict = {}
    info_dict = {"response": "left"}
    result = add_logging_info(tmp_dict, info_dict, categories_dict)
    assert result == {"response": "left"}
    assert "left" in event_category.levels

def test_add_logging_info_non_event(state_category):
    categories_dict = {"trial_counter": state_category}
    tmp_dict = {}
    info_dict = {"trial_counter": 5}
    result = add_logging_info(tmp_dict, info_dict, categories_dict)
    assert result == {}  # STATE mode not handled in this function

def test_add_logging_info_invalid_value(numeric_event_category):
    categories_dict = {"age": numeric_event_category}
    tmp_dict = {}
    info_dict = {"age": "twenty-five"}
    with pytest.raises(ValueError, match="Invalid value"):
        add_logging_info(tmp_dict, info_dict, categories_dict)

def test_add_logging_info_na_not_allowed(numeric_event_category):
    categories_dict = {"age": numeric_event_category}
    tmp_dict = {}
    info_dict = {"age": "n/a"}
    with pytest.raises(ValueError, match="Invalid value"):
        add_logging_info(tmp_dict, info_dict, categories_dict)

def test_add_logging_info_multiple_keys(event_category):
    stim_category = CategoryConfig(
        name="stimulus",
        default=None,
        mode=LogMode.EVENT,
        allow_na=True,
        description="Stimulus type",
        collect_levels=True
    )
    categories_dict = {
        "response": event_category,
        "stimulus": stim_category
    }
    tmp_dict = {}
    info_dict = {"response": "left", "stimulus": "image1"}
    result = add_logging_info(tmp_dict, info_dict, categories_dict)
    assert result == {"response": "left", "stimulus": "image1"}
    assert "left" in event_category.levels
    assert "image1" in stim_category.levels

# ======================
# serialize_value tests
# ======================

def test_serialize_value_none():
    assert serialize_value(None) == "n/a"

def test_serialize_value_nan():
    assert serialize_value(float('nan')) == "n/a"

def test_serialize_value_number():
    assert serialize_value(3.14) == "3.14"

def test_serialize_value_string():
    assert serialize_value("test") == "test"

def test_serialize_value_bool():
    assert serialize_value(True) == "True"

def test_serialize_value_custom_na():
    assert serialize_value(None, na="missing") == "missing"

def test_serialize_value_nan_custom_na():
    assert serialize_value(float('nan'), na="missing") == "missing"