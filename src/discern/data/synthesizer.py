"""Synthesizes realistic field values driven by the document schema."""

from __future__ import annotations

import random
from datetime import date, timedelta
from typing import Any

from faker import Faker

from discern.data.schema import FieldSpec


class ValueSynthesizer:
    """Generates fake but realistic values for each FieldSpec."""

    def __init__(self, seed: int = 42) -> None:
        self._rng = random.Random(seed)
        self._faker = Faker()
        Faker.seed(seed)

    def synthesize(self, field: FieldSpec) -> Any:
        """Return a synthetic value for the given field, or None if nullable."""
        if field.nullable and self._rng.random() < 0.1:
            return None

        match field.value_type:
            case "string":
                return self._synthesize_string(field.name)
            case "email":
                return self._faker.email()
            case "phone":
                return self._faker.numerify("(###) ###-####")
            case "date":
                delta = timedelta(days=self._rng.randint(0, 365))
                d = date.today() - delta
                return d.strftime("%m/%d/%Y")
            case "url":
                return self._faker.url()
            case "enum":
                assert field.options
                return self._rng.choice(field.options)
            case "multiselect":
                assert field.options
                k = self._rng.randint(1, max(1, len(field.options) // 2))
                return self._rng.sample(field.options, k)
            case "bool":
                return self._rng.random() > 0.4
            case "freetext":
                return self._faker.sentence(nb_words=self._rng.randint(8, 20))
            case _:
                return self._faker.word()

    def _synthesize_string(self, field_name: str) -> str:
        n = field_name.lower()
        if any(k in n for k in ("company", "vendor", "merchant", "organizer")):
            return self._faker.company()
        if "job_title" in n:
            return self._faker.job()
        if "event_name" in n:
            return self._faker.catch_phrase()
        if "form_title" in n:
            return self._faker.bs().title()
        if "invoice_number" in n:
            return self._faker.bothify("INV-####??").upper()
        if any(k in n for k in ("amount", "total", "subtotal", "tax")):
            return f"${self._rng.uniform(1.0, 999.0):.2f}"
        if "time" in n:
            hour = self._rng.randint(1, 12)
            minute = self._rng.choice(["00", "15", "30", "45"])
            period = self._rng.choice(["AM", "PM"])
            return f"{hour}:{minute} {period}"
        return self._faker.name()

    def synthesize_document(self, fields: list[FieldSpec]) -> dict[str, Any]:
        """Return a {field_name: value} dict for every field in the list."""
        return {f.name: self.synthesize(f) for f in fields}
