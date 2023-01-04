"""Get lists of shape / statement template elements from dataclasses."""

import pytest
from dataclasses import asdict
from dctap.config import _get_shems, _get_stems


@pytest.mark.skip(reason="Will remove decorator")
def test_get_TAPShape_elements_when_no_config_dict_specified():
    """List TAPShape elements (minus shape_warns and state_list)."""
    expected = ["shapeID", "shapeLabel"]
    assert _get_shems() == expected


@pytest.mark.skip(reason="Will remove decorator")
def test_get_TAPStatementTemplate_elements_when_no_config_dict_specified():
    """List TAPStatementTemplate elements (minus state_warns)."""
    expected = [
        "propertyID",
        "propertyLabel",
        "mandatory",
        "repeatable",
        "valueNodeType",
        "valueDataType",
        "valueConstraint",
        "valueConstraintType",
        "valueShape",
        "note",
    ]
    assert sorted(_get_stems()) == sorted(expected)
