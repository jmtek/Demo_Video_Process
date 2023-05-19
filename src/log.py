import logging
import traceback

# 创建日志器
logger = logging.getLogger('mylogger')
logger.setLevel(logging.DEBUG)

# 创建文件处理器
fh = logging.FileHandler('static/log.txt')
fh.setLevel(logging.DEBUG)

# 创建格式器
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(thread)d - %(message)s')
fh.setFormatter(formatter)

# 添加处理器
logger.addHandler(fh)


# 创建ERROR日志器
errlogger = logging.getLogger('errlogger')
errlogger.setLevel(logging.ERROR)

# 创建文件处理器
errfh = logging.FileHandler('static/err.txt')
errfh.setLevel(logging.ERROR)

# 创建格式器
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(thread)d - %(message)s')
errfh.setFormatter(formatter)

# 添加处理器
errlogger.addHandler(errfh)

def error(msg):
    errlogger.error(f"{msg}\n{traceback.format_exc()}")