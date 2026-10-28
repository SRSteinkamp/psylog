import pytest

from psylog.log_schema import CategoryConfig, LogMode, Validator

# ─── allow_na ───────────────────────────────────────────────────────────────────


class TestValidatorAllowNA:
    def test_na_allowed_by_default(self):
        assert Validator().validate("n/a") is True

    def test_na_allowed_with_type_validator(self):
        assert Validator(int).validate("n/a") is True

    def test_na_allowed_with_iterable_validator(self):
        assert Validator([1, 2, 3]).validate("n/a") is True

    def test_na_allowed_with_callable_validator(self):
        assert Validator(lambda x: False).validate("n/a") is True

    def test_na_rejected_when_disabled(self):
        assert Validator(int, allow_na=False).validate("n/a") is False

    def test_na_rejected_when_disabled_with_type(self):
        assert Validator(int, allow_na=False).validate("n/a") is False

    def test_na_rejected_when_disabled_with_iterable(self):
        assert Validator([1, 2], allow_na=False).validate("n/a") is False

    def test_case_sensitive_na(self):
        """'N/A', 'na', etc. are NOT the same as 'n/a'."""
        assert (
            Validator(allow_na=True).validate("N/A") is True
        )  # falls through to validator=None
        assert Validator(int, allow_na=True).validate("N/A") is False


# ─── validator=None ─────────────────────────────────────────────────────────────
class TestValidatorNoValidator:
    def test_any_value_passes(self):
        v = Validator()
        assert v.validate(42) is True
        assert v.validate("hello") is True
        assert v.validate(None) is True
        assert v.validate([1, 2]) is True
        assert v.validate("n/a") is True


# ─── type validator ─────────────────────────────────────────────────────────────


class TestValidatorTypeValidator:
    def test_int_passes(self):
        assert Validator(int).validate(42) is True

    def test_int_rejects_str(self):
        assert Validator(int).validate("42") is False

    def test_str_passes(self):
        assert Validator(str).validate("hello") is True

    def test_str_rejects_int(self):
        assert Validator(str).validate(42) is False

    def test_float_accepts_int(self):
        """isinstance(42, float) is False, but isinstance(42.0, float) is True."""
        assert Validator(float).validate(42.0) is True
        assert Validator(float).validate(42) is False

    def test_bool_is_int_subclass(self):
        """bool is a subclass of int — isinstance(True, int) is True."""
        assert Validator(int).validate(True) is True

    def test_none_rejected_by_type(self):
        assert Validator(int).validate(None) is False


# ─── iterable validator ─────────────────────────────────────────────────────────


class TestValidatorIterableValidator:
    def test_list_membership(self):
        v = Validator([1, 2, 3])
        assert v.validate(2) is True
        assert v.validate(99) is False

    def test_tuple_membership(self):
        v = Validator(("a", "b", "c"))
        assert v.validate("b") is True
        assert v.validate("z") is False

    def test_set_membership(self):
        v = Validator({10, 20, 30})
        assert v.validate(20) is True
        assert v.validate(99) is False

    def test_empty_iterable_rejects_all(self):
        v = Validator([])
        assert v.validate(1) is False
        assert v.validate("n/a") is True  # allow_na still works

    def test_mixed_type_iterable(self):
        v = Validator([1, "two", 3.0])
        assert v.validate("two") is True
        assert v.validate(3.0) is True
        assert v.validate(1) is True
        assert v.validate("three") is False


# ─── callable validator ─────────────────────────────────────────────────────────


class TestValidatorCallableValidator:
    def test_lambda_positive(self):
        v = Validator(lambda x: isinstance(x, (int, float)) and x > 0)
        assert v.validate(5) is True
        assert v.validate(-1) is False
        assert v.validate("hello") is False

    def test_named_function(self):
        def is_even(x):
            return isinstance(x, int) and x % 2 == 0

        v = Validator(is_even)
        assert v.validate(4) is True
        assert v.validate(3) is False
        assert v.validate("nope") is False

    def test_callable_returning_truthy_non_bool(self):
        """validate() returns whatever the callable returns (not coerced to bool)."""
        v = Validator(lambda x: 1)
        assert v.validate("anything") == 1  # truthy, but not literally True

    def test_callable_receiving_na(self):
        """When allow_na=False, the callable DOES receive 'n/a'."""
        received = []
        v = Validator(lambda x: (received.append(x), False)[1], allow_na=False)
        v.validate("n/a")
        assert received == ["n/a"]


# ─── fallback / unexpected validator ────────────────────────────────────────────


class TestValidatorFallback:
    def test_unexpected_validator_returns_false(self):
        """An int is not a type, not an iterable, not callable → False."""
        v = Validator(42)
        assert v.validate(1) is False

    def test_unexpected_validator_na_still_works(self):
        v = Validator(42, allow_na=True)
        assert v.validate("n/a") is True


# Test Validator __eq__


class TestValidatorEquality:
    def test_same_type(self):
        assert Validator(int) == Validator(int)

    def test_same_iterable(self):
        assert Validator([1, 2, 3]) == Validator([1, 2, 3])

    def test_same_tuple(self):
        assert Validator(("a", "b")) == Validator(("a", "b"))

    def test_different_type(self):
        assert Validator(int) != Validator(float)

    def test_different_allow_na(self):
        assert Validator(int, allow_na=True) != Validator(int, allow_na=False)

    def test_different_iterable(self):
        assert Validator([1, 2]) != Validator([1, 3])

    def test_none_validator(self):
        assert Validator() == Validator()

    def test_not_equal_to_non_validator(self):
        assert Validator(int) != "int"
        assert Validator(int) is not None

    def test_ne_returns_true(self):
        assert Validator(int) != Validator(str)


# ─── __repr__ ───────────────────────────────────────────────────────────────────


class TestValidatorRepr:
    def test_no_validator(self):
        assert repr(Validator()) == "Validator(allow_na=True)"

    def test_type_validator(self):
        assert (
            repr(Validator(int)) == "Validator(validator=<class 'int'>, allow_na=True)"
        )

    def test_iterable_validator(self):
        assert repr(Validator([1, 2])) == "Validator(validator=[1, 2], allow_na=True)"

    def test_callable_validator(self):
        def f(x):
            return x

        assert f"Validator(validator={f}, allow_na=True)" == repr(Validator(f))

    def test_allow_na_false_in_repr(self):
        assert (
            repr(Validator(int, allow_na=False))
            == "Validator(validator=<class 'int'>, allow_na=False)"
        )

    def test_bug_no_validator_repr_ignores_allow_na(self):
        """KNOWN BUG: repr always shows allow_na=True when validator is None."""
        v = Validator(allow_na=False)
        # This is the current (buggy) behaviour — document it.
        assert repr(v) == "Validator(allow_na=True)"


# ─── Construction / __post_init__ ──────────────────────────────────────────────


class TestCategoryConfigConstruction:
    def test_minimal_valid(self):
        c = CategoryConfig(name="trial_id", default=1)
        assert c.name == "trial_id"
        assert c.default == 1
        assert c.mode is LogMode.EVENT
        assert c.units == "n/a"
        assert c.description == ""

    def test_state_is_deepcopy_of_default(self):
        """REGRESSION: state must equal default, not None."""
        c = CategoryConfig(name="x", default=42)
        assert c.state == 42

    def test_state_is_independent_copy_for_mutable_default(self):
        c = CategoryConfig(name="x", default=[1, 2, 3])
        c.state.append(99)
        assert c.default == [1, 2, 3]  # original untouched

    def test_state_is_independent_copy_for_dict_default(self):
        c = CategoryConfig(name="x", default={"a": 1})
        c.state["a"] = 999
        assert c.default == {"a": 1}

    def test_all_fields_set(self):
        c = CategoryConfig(
            name="rt",
            default=0.5,
            mode=LogMode.STATE,
            validator=Validator(float),
            description="Reaction time",
            units="seconds",
            long_name="Reaction Time",
        )
        assert c.mode is LogMode.STATE
        assert c.units == "seconds"
        assert c.long_name == "Reaction Time"
        assert c.state == 0.5


# ─── Validation (raises on bad config) ─────────────────────────────────────────


class TestCategoryConfigValidation:
    def test_empty_name_raises(self):
        with pytest.raises(ValueError, match="non-empty string"):
            CategoryConfig(name="", default=1)

    def test_non_string_name_raises(self):
        with pytest.raises(ValueError, match="non-empty string"):
            CategoryConfig(name=123, default=1)

    def test_none_name_raises(self):
        with pytest.raises(ValueError, match="non-empty string"):
            CategoryConfig(name=None, default=1)

    def test_invalid_mode_raises(self):
        with pytest.raises(TypeError, match="Invalid mode"):
            CategoryConfig(name="x", default=1, mode="not_a_mode")

    def test_int_mode_raises(self):
        with pytest.raises(TypeError, match="Invalid mode"):
            CategoryConfig(name="x", default=1, mode=42)

    def test_default_fails_validator_raises(self):
        with pytest.raises(TypeError, match="doesn't match validator|fails validator"):
            CategoryConfig(name="x", default="hello", validator=Validator(int))

    def test_default_passes_validator_ok(self):
        c = CategoryConfig(name="x", default=3.14, validator=Validator(float))
        assert c.state == 3.14

    def test_na_default_with_allow_na(self):
        c = CategoryConfig(
            name="x", default="n/a", validator=Validator(int, allow_na=True)
        )
        assert c.state == "n/a"

    def test_na_default_without_allow_na_raises(self):
        with pytest.raises(TypeError):
            CategoryConfig(
                name="x", default="n/a", validator=Validator(int, allow_na=False)
            )


# ─── set_state / change_state ──────────────────────────────────────────────────


class TestCategoryConfigSetState:
    def test_set_state_updates(self):
        c = CategoryConfig(name="x", default=1, validator=Validator(int))
        c.set_state(99)
        assert c.state == 99

    def test_set_state_rejects_invalid(self):
        c = CategoryConfig(name="x", default=1, validator=Validator(int))
        with pytest.raises(ValueError):
            c.set_state("not_an_int")

    def test_set_state_allows_na_when_enabled(self):
        c = CategoryConfig(name="x", default=1, validator=Validator(int, allow_na=True))
        c.set_state("n/a")
        assert c.state == "n/a"

    def test_set_state_rejects_na_when_disabled(self):
        c = CategoryConfig(
            name="x", default=1, validator=Validator(int, allow_na=False)
        )
        with pytest.raises(ValueError):
            c.set_state("n/a")

    def test_set_state_with_iterable_validator(self):
        c = CategoryConfig(name="x", default="a", validator=Validator(["a", "b", "c"]))
        c.set_state("b")
        assert c.state == "b"
        with pytest.raises(ValueError):
            c.set_state("z")


# ─── to_bids_dict ──────────────────────────────────────────────────────────────


class TestCategoryConfigToBidsDict:
    def test_basic_keys(self):
        c = CategoryConfig(name="x", default=1, description="desc", long_name="Long")
        d = c.to_bids_dict()
        assert d["Description"] == "desc"
        assert d["LongName"] == "Long"

    def test_units_from_field(self):
        """The user-set `units` field should appear in output."""
        c = CategoryConfig(name="rt", default=1.0, units="seconds")
        d = c.to_bids_dict()
        assert d["Units"] == "seconds"

    def test_default_units_is_na(self):
        c = CategoryConfig(name="x", default=1)
        d = c.to_bids_dict()
        assert d["Units"] == "n/a"

    def test_int_validator_no_extra_units_override(self):
        """With the refactored version, units come from the field, not inference."""
        c = CategoryConfig(name="trial_id", default=1, validator=Validator(int))
        d = c.to_bids_dict()
        assert d["Units"] == "n/a"

    def test_iterable_validator_adds_levels(self):
        c = CategoryConfig(
            name="cond", default="a", validator=Validator(["a", "b", "c"])
        )
        d = c.to_bids_dict()
        assert "Levels" in d
        assert set(d["Levels"].keys()) == {"a", "b", "c"}

    def test_tuple_validator_adds_levels(self):
        c = CategoryConfig(name="cond", default=1, validator=Validator((1, 2, 3)))
        d = c.to_bids_dict()
        assert set(d["Levels"].keys()) == {"1", "2", "3"}

    def test_set_validator_adds_levels(self):
        c = CategoryConfig(name="cond", default=1, validator=Validator({1, 2}))
        d = c.to_bids_dict()
        assert set(d["Levels"].keys()) == {"1", "2"}

    def test_none_validator_no_levels(self):
        c = CategoryConfig(name="x", default="anything")
        d = c.to_bids_dict()
        assert "Levels" not in d

    def test_callable_validator_no_levels(self):
        c = CategoryConfig(name="x", default=1, validator=Validator(lambda v: v > 0))
        d = c.to_bids_dict()
        assert "Levels" not in d

    def test_str_validator_no_levels(self):
        c = CategoryConfig(name="x", default="hi", validator=Validator(str))
        d = c.to_bids_dict()
        assert "Levels" not in d


# ─── Equality / Hash ───────────────────────────────────────────────────────────


class TestCategoryConfigEquality:
    def test_equal_configs(self):
        a = CategoryConfig(name="x", default=1)
        b = CategoryConfig(name="x", default=1)
        assert a == b

    def test_different_name_not_equal(self):
        a = CategoryConfig(name="x", default=1)
        b = CategoryConfig(name="y", default=1)
        assert a != b

    def test_different_state_still_equal(self):
        """state is not a dataclass field → excluded from __eq__."""
        a = CategoryConfig(name="x", default=1)
        b = CategoryConfig(name="x", default=1)
        a.set_state(99)
        assert a == b  # by design (state is runtime, not config)


# ─── Repr / Repr sanity ────────────────────────────────────────────────────────


class TestCategoryConfigRepr:
    def test_repr_contains_name(self):
        c = CategoryConfig(name="trial_id", default=1)
        assert "trial_id" in repr(c)

    def test_repr_contains_mode(self):
        c = CategoryConfig(name="x", default=1, mode=LogMode.STATE)
        assert "STATE" in repr(c)
