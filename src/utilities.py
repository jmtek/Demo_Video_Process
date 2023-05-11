import time

def timed_func(func):
    """用于计算函数执行时间的装饰器"""
    def wrapper(*args, **kwargs):
        start = time.time()
        result = func(*args, **kwargs)
        end = time.time()
        print(func.__name__ + " took " + str((end - start)*1000) + "ms")
        return result
    return wrapper