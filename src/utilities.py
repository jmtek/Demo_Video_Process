import time
from src.log import logger

def timed_func(func):
    """用于计算函数执行时间的装饰器"""
    def wrapper(*args, **kwargs):
        start = time.time()
        result = func(*args, **kwargs)
        end = time.time()
        duration = str((end - start)*1000)
        logger.debug(f"func: {func.__name__}, {args}, {kwargs}. duration: {duration}")
        # call_webhook("transcript", { "func": func.__name__, "args": args, "kwargs": kwargs, "result": str(result), "duration": duration })
        return result
    return wrapper