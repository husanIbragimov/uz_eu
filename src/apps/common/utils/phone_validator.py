import re

from django.core.validators import RegexValidator

regex_pattern = r"^\+998([0-9]{2})[0-9]{7}$"

phone_validator = RegexValidator(regex=regex_pattern, message="Phone number is not correct. Example: '+998901234567'")

# E.164: "+" followed by 7-15 digits (country code included), e.g. +998901234567, +3225551234
international_regex_pattern = r"^\+[1-9][0-9]{6,14}$"

international_phone_validator = RegexValidator(
    regex=international_regex_pattern,
    message="Phone number must be in international format, e.g. '+998 90 123 45 67' or '+32 2 555 12 34'.",
)


def is_phone_number_valid(phone_number) -> bool:
    pattern = regex_pattern
    return bool(re.match(pattern, phone_number))


def normalize_phone_number(phone_number: str) -> str:
    """Strip spaces, dashes, dots and brackets so `+998 (90) 123-45-67` becomes `+998901234567`."""
    return re.sub(r"[\s\-().]", "", phone_number or "")
