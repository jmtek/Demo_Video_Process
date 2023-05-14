import logging

# 创建日志器
logger = logging.getLogger('mylogger')
logger.setLevel(logging.DEBUG)

# 创建文件处理器
fh = logging.FileHandler('logfile.txt')
fh.setLevel(logging.DEBUG)

# 创建格式器
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
fh.setFormatter(formatter)

# 添加处理器
logger.addHandler(fh)