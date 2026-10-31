def digits(value: str | None) -> str | None:
    if value is None:
        return None
    return "".join(character for character in value if character.isdigit())