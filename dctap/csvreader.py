"""Parse DCTAP/CSV, return two-item tuple: (list of shape objects, list of warnings)."""

from collections import defaultdict
from csv import DictReader
from io import StringIO as StringBuffer
from dataclasses import asdict
from typing import Dict
from .exceptions import DctapError
from .tapclasses import TAPShape, TAPStatementConstraint


def csvreader(open_csvfile_obj, config_dict):
    """From open CSV file object, return tuple: (shapes dict, warnings dict)."""
    rows_list = _get_rows(open_csvfile_obj, config_dict)
    tapshapes = _get_tapshapes(rows_list, config_dict)[0]
    tapwarnings = _get_tapshapes(rows_list, config_dict)[1]
    return (tapshapes, tapwarnings)


def _get_rows(open_csvfile_obj, config_dict):
    """Extract from _io.TextIOWrapper object a list of CSV file rows as dicts."""
    csvfile_contents_str = open_csvfile_obj.read()
    tmp_buffer = StringBuffer(csvfile_contents_str)
    csvlines_stripped = [line.strip() for line in tmp_buffer]
    raw_header_line_list = csvlines_stripped[0].split(",")
    new_header_line_list = list()
    for header in raw_header_line_list:
        header = _lowercase_despace_depunctuate(header)
        header = _normalize_element_name(header, config_dict.get("element_aliases"))
        new_header_line_list.append(header)
    new_header_line_str = ",".join(new_header_line_list)
    csvlines_stripped[0] = new_header_line_str
    if "propertyID" not in csvlines_stripped[0]:
        raise DctapError("Valid DCTAP CSV must have a 'propertyID' column.")
    tmp_buffer2 = StringBuffer("".join([line + "\n" for line in csvlines_stripped]))
    return list(DictReader(tmp_buffer2))


def _get_tapshapes(rows, config_dict):
    """Return tuple: list of TAPShape objects and list of any warnings."""
    # pylint: disable=too-many-locals
    # pylint: disable=too-many-branches
    # pylint: disable=too-many-statements

    try:
        dshape = config_dict.get("default_shape_name")
    except KeyError:
        dshape = "default"

    if config_dict["extra_shape_elements"]:
        shape_extras = config_dict["extra_shape_elements"]
    if config_dict["extra_statement_constraint_elements"]:
        sc_extras = config_dict["extra_statement_constraint_elements"]

    # fmt: off
    shapes: Dict[str, TAPShape] = dict()            # To make dict for TAPShapes,
    first_valid_row_encountered = True              # read CSV rows as list of dicts.
    warnings = defaultdict(dict)                    # Init defaultdict for warnings.

    def set_shape_fields(shape=None, row=None):     # To set shape-related keys,
        tapshape_keys = list(asdict(TAPShape()))    # make a list of those keys,
        tapshape_keys.remove("sc_list")             # sh_warnings - not
        # TODO tapshape_keys.remove("statement_constraints") # sh_warnings - not
        tapshape_keys.remove("sh_warnings")         # shape fields.
        for key in tapshape_keys:                   # Iterate remaining keys, to
            try:                                    # populate tapshape fields
                setattr(shape, key, row[key])       # with values from row dict.
            except KeyError:                        # Keys not found in row dict,
                pass                                # are simply skipped.
        return shape                                # Return shape with fields set.

    for row in rows:                                # For each row
        if not row["propertyID"]:                   # where no propertyID be found,
            continue                                # ignore and move to next.

        if first_valid_row_encountered:             # In very "first" valid row,
            if row.get("shapeID"):                  # if truthy shapeID be found,
                sh_id = row.get("shapeID")          # use as a key for shapes dict.
            else:                                   # If no truthy shapeID be found,
                sh_id = row["shapeID"] = dshape     # use default shapeID as key.
            shape = shapes[sh_id] = TAPShape()      # Add TAPShape obj to shapes dict,
            set_shape_fields(shape, row)            # populate its shape elements, and
            first_valid_row_encountered = False     # may future rows be not "first".

        if not first_valid_row_encountered:         # In each valid row thereafter,
            if row.get("shapeID"):                  # if truthy shapeID be found,
                sh_id = row["shapeID"]              # use as a key for shapes dict.
            else:                                   # If no truthy shapeID be found,
                so_far = list(shapes)               # see list of shapeIDs used so far,
                sh_id = so_far[-1]                  # and may most recent one be key.

        if sh_id not in shapes:                     # If shape ID not in shapes dict,
            shape = shapes[sh_id] = TAPShape()      # add it with value TAPShape, and
            set_shape_fields(shape, row)            # populate its shape elements, and
            warnings[sh_id] = dict()                # use as key in warnings dict.

        shape.set_settings(config_dict)
        shape.normalize()
        shape_warnings = shape.get_warnings()

        for (elem,warn) in shape_warnings.items():  # Iterate Shape warnings.
            try:                                    # Try to add each warning to dict
                warnings[sh_id][elem].append(warn)  # of all warnings, by shape,
            except KeyError:                        # but if needed key not found,
                warnings[sh_id][elem] = list()      # set new key with value list,
                warnings[sh_id][elem].append(warn)  # and warning can now be added.

        sc = TAPStatementConstraint()               # Instantiate SC for this row.

        for key in list(asdict(sc)):                # Iterate SC fields, to
            try:                                    # populate the SC instance
                setattr(sc, key, row[key])          # with values from the row dict,
            except KeyError:                        # while fields not found in SC
                pass                                # are simply skipped (yes?).

        shapes[sh_id].sc_list.append(sc)            # Add SC to SC list in shapes dict.
# TODO sc_list => statement_constraints
#                      statement_constraints.append(sc)

        sc.set_settings(config_dict)                # SC normalizes itself, and
        sc.normalize()                              # SC normalizes itself, and
        sc_warnings = sc.get_warnings()             # emits warnings on request.

        for (elem,warn) in sc_warnings.items():     # Iterate SC instance warnings.
            try:                                    # Try to add each warning to dict
                warnings[sh_id][elem].append(warn)  # of all warnings by shape,
            except KeyError:                        # but if needed key not found,
                warnings[sh_id][elem] = list()      # set new key with value list,
                warnings[sh_id][elem].append(warn)  # and warning can now be added.

        tapshapes_dict = dict()                     # New dict to hold shapes as dicts.
        shape_list = list()                         # New list for TAPShapes objs, as
        tapshapes_dict["shapes"] = shape_list       # mutable value for key "shapes".
        for tapshape_obj in list(shapes.values()):  # For each TAPShape object in list:
            tapshape_dict = asdict(tapshape_obj)    # - convert object to pure dict,
            tapshape_dict[                          # - rename its field "sc_list" to
                "statement_constraints"             #   "statement_constraints"
            ] = tapshape_dict.pop("sc_list")        # - add that shape dict to mutable
            shape_list.append(tapshape_dict)        #   tapshapes_dict["shapes"]

        warnings_dict = dict(warnings)              # Save defaultdict warnings as dict.

    return (                                        # Return tuple:
        tapshapes_dict,                             #   Shapes dictionary
        warnings_dict                               #   Dict of warnings, by shape
    )
    # fmt: on


def _lowercase_despace_depunctuate(some_str=None):
    """For given string, delete underscores, dashes, spaces, then lowercase."""
    some_str = some_str.replace(" ", "")
    some_str = some_str.replace("_", "")
    some_str = some_str.replace("-", "")
    some_str = some_str.lower()
    return some_str


def _normalize_element_name(some_str, element_aliases_dict=None):
    """Normalize a given string (or leave unchanged)."""
    some_str = _lowercase_despace_depunctuate(some_str)
    if element_aliases_dict:
        for key in element_aliases_dict.keys():
            if key == some_str:
                some_str = element_aliases_dict[key]
    return some_str
