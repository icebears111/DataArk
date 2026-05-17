# DataArk 后端包
#
# __init__.py 告诉 Python 这个目录是一个"包"（package）。
# 有了这个文件，才能用 from app.config import settings 这样导入。
#
# 这里的 import 是为了让 PyCharm 能找到子模块引用，
# 避免"在 '__init__.py' 中找不到引用 'config'"的警告。
import app.config as config
