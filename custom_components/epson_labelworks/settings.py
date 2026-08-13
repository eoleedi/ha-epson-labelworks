from __future__ import annotations

from dataclasses import dataclass

from .protocol import CutMode


@dataclass
class PrintSettings:
    tape_width_mm: float = 12
    font_size: int = 24
    cut: CutMode = CutMode.AFTER
    density: int = 0
    margin_mm: float = 1

    def text_print_data(self, text: str) -> dict:
        return {
            "text": text,
            "tape_width_mm": self.tape_width_mm,
            "font_size": self.font_size,
            "cut": self.cut,
            "density": self.density,
            "margin_mm": self.margin_mm,
        }
