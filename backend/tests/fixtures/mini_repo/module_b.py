import pydantic
import module_a


def func_b(y: int) -> int:
    for i in range(y):
        if i % 2 == 0:
            return i
    return 0
