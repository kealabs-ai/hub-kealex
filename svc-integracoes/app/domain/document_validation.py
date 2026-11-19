import re


def _digits(value: str) -> str:
    return re.sub(r"\D", "", value or "")


def validate_cpf(value: str) -> bool:
    value = _digits(value)
    if len(value) != 11 or len(set(value)) == 1:
        return False
    digits = [int(char) for char in value]
    for position in (9, 10):
        weight = position + 1
        total = sum(digits[index] * (weight - index) for index in range(position))
        check = (total * 10 % 11) % 10
        if digits[position] != check:
            return False
    return True


def validate_cnpj(value: str) -> bool:
    value = _digits(value)
    if len(value) != 14 or len(set(value)) == 1:
        return False
    digits = [int(char) for char in value]
    for position, weights in ((12, (5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2)), (13, (6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2))):
        remainder = sum(digits[index] * weight for index, weight in enumerate(weights)) % 11
        check = 0 if remainder < 2 else 11 - remainder
        if digits[position] != check:
            return False
    return True
