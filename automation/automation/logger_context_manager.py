from contextlib import contextmanager

from loguru import logger


@contextmanager
def logger_add(*args, **kwargs):
    i = logger.add(*args, **kwargs)
    try:
        yield
    finally:
        logger.remove(i)
