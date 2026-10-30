import pytest

from psylog.log_schema import CategoryConfig, LogMode


# ==================================================
# Initialization
# ==================================================

def test_category_initialization():
    category = CategoryConfig(
        name="response",
        default="n/a",
    )

    assert category.name == "response"
    assert category.default == "n/a"
    assert category.mode == LogMode.EVENT
    assert category.state == "n/a"
    assert category.data_type is None
    assert category.allow_na is True
    assert category.levels == {}


def test_category_initialization_with_custom_values():
    category = CategoryConfig(
        name="trial",
        default=1,
        mode=LogMode.STATE,
        data_type=int,
        description="Trial number",
        units="count",
        long_name="Trial Number",
    )

    assert category.mode == LogMode.STATE
    assert category.state == 1
    assert category.data_type is int
    assert category.description == "Trial number"
    assert category.units == "count"
    assert category.long_name == "Trial Number"


def test_category_state_is_deepcopied():
    default = {"response": []}

    category = CategoryConfig(
        name="response",
        default=default,
    )

    category.state["response"].append("left")

    assert default == {"response": []}


def test_category_levels_are_independent():
    first = CategoryConfig(
        name="first",
        default="n/a",
    )

    second = CategoryConfig(
        name="second",
        default="n/a",
    )

    first.levels["left"] = ""

    assert second.levels == {}


# ==================================================
# Configuration validation
# ==================================================

@pytest.mark.parametrize(
    "name",
    ["", None, 123],
)
def test_invalid_category_name(name):
    with pytest.raises(ValueError):
        CategoryConfig(
            name=name,
            default="n/a",
        )


def test_invalid_category_mode():
    with pytest.raises(TypeError):
        CategoryConfig(
            name="response",
            default="n/a",
            mode="event",
        )


def test_invalid_data_type():
    with pytest.raises(TypeError):
        CategoryConfig(
            name="trial",
            default=1,
            data_type="int",
        )


def test_invalid_data_type_tuple():
    with pytest.raises(TypeError):
        CategoryConfig(
            name="trial",
            default=1,
            data_type=(int, "float"),
        )


def test_valid_data_type_tuple():
    category = CategoryConfig(
        name="response_time",
        default=0.0,
        data_type=(int, float),
    )

    assert category.data_type == (int, float)


def test_invalid_default_datatype():
    with pytest.raises(ValueError):
        CategoryConfig(
            name="trial",
            default="one",
            data_type=int,
        )


def test_invalid_default_level():
    with pytest.raises(ValueError):
        CategoryConfig(
            name="response",
            default="other",
            levels={"left": "", "right": ""},
            validate_levels=True,
        )


def test_validate_levels_requires_predefined_levels():
    with pytest.raises(ValueError):
        CategoryConfig(
            name="response",
            default="left",
            validate_levels=True,
        )


# ==================================================
# Value validation
# ==================================================

def test_validation_without_datatype():
    category = CategoryConfig(
        name="response",
        default="n/a",
    )

    assert category.validate("left")
    assert category.validate(123)
    assert category.validate(1.5)


def test_validation_with_single_datatype():
    category = CategoryConfig(
        name="trial",
        default=1,
        data_type=int,
    )

    assert category.validate(1)
    assert not category.validate("1")
    assert not category.validate(1.5)


def test_validation_with_multiple_datatypes():
    category = CategoryConfig(
        name="response_time",
        default=0.0,
        data_type=(int, float),
    )

    assert category.validate(1)
    assert category.validate(1.5)
    assert not category.validate("1.5")


def test_na_allowed_by_default():
    category = CategoryConfig(
        name="response",
        default="n/a",
    )

    assert category.validate("n/a")


def test_na_can_be_disabled():
    category = CategoryConfig(
        name="trial",
        default=1,
        data_type=int,
        allow_na=False,
    )

    assert not category.validate("n/a")
    assert category.validate(1)


def test_levels_are_not_validated_by_default():
    category = CategoryConfig(
        name="response",
        default="left",
        levels={"left": "", "right": ""},
    )

    assert category.validate("unexpected")


def test_validate_levels():
    category = CategoryConfig(
        name="response",
        default="left",
        levels={"left": "", "right": ""},
        validate_levels=True,
    )

    assert category.validate("left")
    assert category.validate("right")
    assert not category.validate("unexpected")


def test_levels_and_datatype_validation():
    category = CategoryConfig(
        name="response",
        default="left",
        data_type=str,
        levels={"left": "", "right": ""},
        validate_levels=True,
    )

    assert category.validate("left")
    assert not category.validate("unexpected")
    assert not category.validate(1)


# ==================================================
# Missing-value handling
# ==================================================

def test_none_is_missing():
    category = CategoryConfig(
        name="response",
        default="n/a",
    )

    assert category._is_missing(None)


def test_nan_is_missing():
    category = CategoryConfig(
        name="response",
        default="n/a",
    )

    assert category._is_missing(float("nan"))


def test_na_string_is_missing():
    category = CategoryConfig(
        name="response",
        default="n/a",
    )

    assert category._is_missing("n/a")


@pytest.mark.parametrize(
    "value",
    ["", "NA", "nan", "None", 0, 1.5, "left"],
)
def test_valid_values_are_not_missing(value):
    category = CategoryConfig(
        name="response",
        default="n/a",
    )

    assert not category._is_missing(value)


def test_none_validation_with_allow_na():
    category = CategoryConfig(
        name="response",
        default="n/a",
        allow_na=True,
    )

    assert category.validate(None)


def test_none_validation_without_allow_na():
    category = CategoryConfig(
        name="response",
        default=1,
        allow_na=False,
    )

    assert not category.validate(None)


def test_nan_validation_with_allow_na():
    category = CategoryConfig(
        name="response",
        default="n/a",
        allow_na=True,
    )

    assert category.validate(float("nan"))


def test_nan_validation_without_allow_na():
    category = CategoryConfig(
        name="response",
        default=1,
        allow_na=False,
    )

    assert not category.validate(float("nan"))


# ==================================================
# State management
# ==================================================

def test_set_state():
    category = CategoryConfig(
        name="response",
        default="n/a",
        data_type=str,
    )

    category.set_state("left")

    assert category.state == "left"


def test_set_invalid_state():
    category = CategoryConfig(
        name="trial",
        default=1,
        data_type=int,
    )

    with pytest.raises(ValueError):
        category.set_state("invalid")

    assert category.state == 1


def test_set_state_respects_levels():
    category = CategoryConfig(
        name="response",
        default="left",
        levels={"left": "", "right": ""},
        validate_levels=True,
    )

    category.set_state("right")

    assert category.state == "right"

    with pytest.raises(ValueError):
        category.set_state("unexpected")


def test_set_state_accepts_missing_value():
    category = CategoryConfig(
        name="response",
        default="left",
        allow_na=True,
    )

    category.set_state(None)

    assert category.state is None


# ==================================================
# Level collection
# ==================================================

def test_record_value():
    category = CategoryConfig(
        name="response",
        default="n/a",
        collect_levels=True,
    )

    category.record_value("left")

    assert category.levels == {"left": ""}


def test_record_multiple_values():
    category = CategoryConfig(
        name="response",
        default="n/a",
        collect_levels=True,
    )

    category.record_value("left")
    category.record_value("right")
    category.record_value("left")

    assert category.levels == {
        "left": "",
        "right": "",
    }


def test_record_value_preserves_existing_description():
    category = CategoryConfig(
        name="response",
        default="n/a",
        levels={"left": "Left response"},
        collect_levels=True,
    )

    category.record_value("left")
    category.record_value("right")

    assert category.levels == {
        "left": "Left response",
        "right": "",
    }


def test_record_value_ignored_when_collection_disabled():
    category = CategoryConfig(
        name="response",
        default="n/a",
        collect_levels=False,
    )

    category.record_value("left")

    assert category.levels == {}


@pytest.mark.parametrize(
    "value",
    ["n/a", None, float("nan")],
)
def test_missing_values_are_not_collected(value):
    category = CategoryConfig(
        name="response",
        default="n/a",
        collect_levels=True,
    )

    category.record_value(value)

    assert category.levels == {}


def test_set_state_collects_levels():
    category = CategoryConfig(
        name="response",
        default="n/a",
        collect_levels=True,
    )

    category.set_state("left")
    category.set_state("right")

    assert category.levels == {
        "left": "",
        "right": "",
    }


# ==================================================
# BIDS metadata
# ==================================================

def test_bids_dict_without_levels():
    category = CategoryConfig(
        name="response",
        default="n/a",
        description="Participant response",
        units="n/a",
        long_name="Response",
    )

    result = category.to_bids_dict()

    assert result == {
        "Description": "Participant response",
        "LongName": "Response",
        "Units": "n/a",
    }


def test_bids_dict_with_levels():
    category = CategoryConfig(
        name="response",
        default="left",
        levels={
            "right": "Right response",
            "left": "Left response",
        },
    )

    result = category.to_bids_dict()

    assert result["Levels"] == {
        "left": "Left response",
        "right": "Right response",
    }


def test_bids_dict_includes_collected_levels():
    category = CategoryConfig(
        name="response",
        default="n/a",
        collect_levels=True,
    )

    category.record_value("left")
    category.record_value("right")

    result = category.to_bids_dict()

    assert result["Levels"] == {
        "left": "",
        "right": "",
    }


def test_bids_dict_does_not_modify_original_levels():
    category = CategoryConfig(
        name="response",
        default="left",
        levels={"left": "Left response"},
    )

    result = category.to_bids_dict()
    result["Levels"]["left"] = "Modified"

    assert category.levels["left"] == "Left response"
