"""
命令行工具模块
"""
import warnings

# 全局过滤第三方库的已知警告
warnings.filterwarnings('ignore', message='pkg_resources is deprecated')
warnings.filterwarnings('ignore', category=SyntaxWarning, module='whoosh')

