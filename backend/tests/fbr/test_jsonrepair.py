from app.modules.fbr.jsonrepair import loads


def test_valid_json_untouched():
    assert loads('{"a": 1, "b": [1, 2]}') == {"a": 1, "b": [1, 2]}


def test_trailing_comma_in_object():
    assert loads('{"a": 1, "b": 2,}') == {"a": 1, "b": 2}


def test_trailing_comma_in_array_and_nested():
    assert loads('{"items": [ {"x": 1,}, {"y": 2}, ] }') == {"items": [{"x": 1}, {"y": 2}]}


def test_strips_control_characters():
    assert loads('{"error": "bad\x07value",}') == {"error": "badvalue"}


def test_fbr_validation_response_with_trailing_comma():
    raw = (
        '{\n'
        '    "dated": "2026-07-25 17:45:55",\n'
        '    "validationResponse": {\n'
        '        "statusCode": "01",\n'
        '        "status": "Invalid",\n'
        '        "error": "Unauthorized access",\n'
        '    },\n'
        '}'
    )
    assert loads(raw)["validationResponse"]["status"] == "Invalid"


def test_empty_returns_none():
    assert loads("") is None
    assert loads(None) is None
