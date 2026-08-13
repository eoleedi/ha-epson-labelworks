from epson_labelworks.protocol import CutMode
from epson_labelworks.settings import PrintSettings


def test_print_settings_defaults():
    settings = PrintSettings()

    assert settings.text_print_data("Pantry") == {
        "text": "Pantry",
        "tape_width_mm": 12,
        "font_size": 24,
        "cut": CutMode.AFTER,
        "density": 0,
        "margin_mm": 1,
    }


def test_print_settings_use_current_entity_values():
    settings = PrintSettings(tape_width_mm=18, font_size=30, cut=CutMode.NONE, density=2, margin_mm=3)

    data = settings.text_print_data("Storage")

    assert data["tape_width_mm"] == 18
    assert data["font_size"] == 30
    assert data["cut"] is CutMode.NONE
    assert data["density"] == 2
    assert data["margin_mm"] == 3
