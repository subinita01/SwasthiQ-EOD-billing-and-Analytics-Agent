from __future__ import annotations

from pydantic import BaseModel


class TracedFigure(BaseModel):
    """One number the narrative cites, mapped back to its report field.

    `verified` is only True when the field exists, its value matches the
    report exactly, and the displayed text in the narrative resolves to
    that same value. `field` is the literal string "<uncited>" for numbers
    found in the narrative text that had no matching citation at all.
    """

    field: str
    value: int | None
    displayed_text: str
    verified: bool
    issues: list[str]


class NarrativeSummary(BaseModel):
    narrative: str
    traced_figures: list[TracedFigure]
    fully_verified: bool
    generation_error: str | None
