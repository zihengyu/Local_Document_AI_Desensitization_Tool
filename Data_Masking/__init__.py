# Data_Masking 包初始化文件

# 导入脱敏相关功能（轻量路径默认可用）
from .masking import (
    MaskingStrategy, ReplacementStrategy, HashStrategy, TypeBasedStrategy,
    DataMasker, DocumentMasker
)

# 导出模块内容
__all__ = [
    'MaskingStrategy', 'ReplacementStrategy', 'HashStrategy', 'TypeBasedStrategy',
    'DataMasker', 'DocumentMasker'
]
