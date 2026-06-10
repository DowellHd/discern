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
                return self._faker.name()
            case "email":
                return self._faker.email()
            case "phone":
                return self._faker.numerify("(###) ###-####")
            case "date":
                delta = timedelta(days=self._rng.randint(0, 365))
                d = date.today() - delta
                return d.strftime("%m/%d/%Y")
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

    def synthesize_document(self, fields: list[FieldSpec]) -> dict[str, Any]:
        """Return a {field_name: value} dict for every field in the list."""
        return {f.name: self.synthesize(f) for f in fields}
