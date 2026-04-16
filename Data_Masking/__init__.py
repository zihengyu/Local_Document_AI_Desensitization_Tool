"""Data_Masking package.

通过懒加载避免在导入包时触发重依赖初始化（如 NER、tqdm 等），
保证 lite 子应用和打包应用启动稳定。
"""

from importlib import import_module

# 冲突统一版本：保留懒加载导出，避免 lite 子应用启动时拉起重依赖

__all__ = [
    'MaskingStrategy', 'ReplacementStrategy', 'HashStrategy', 'TypeBasedStrategy',
    'DataMasker', 'DocumentMasker',
    'NumpyEncoder', 'recognize_entities', 'NERModelLoader', 'batch_recognize_entities'
]

_EXPORT_MAP = {
    'MaskingStrategy': ('Data_Masking.masking', 'MaskingStrategy'),
    'ReplacementStrategy': ('Data_Masking.masking', 'ReplacementStrategy'),
    'HashStrategy': ('Data_Masking.masking', 'HashStrategy'),
    'TypeBasedStrategy': ('Data_Masking.masking', 'TypeBasedStrategy'),
    'DataMasker': ('Data_Masking.masking', 'DataMasker'),
    'DocumentMasker': ('Data_Masking.masking', 'DocumentMasker'),
    'NumpyEncoder': ('Data_Masking.NER_model', 'NumpyEncoder'),
    'recognize_entities': ('Data_Masking.NER_model', 'recognize_entities'),
    'NERModelLoader': ('Data_Masking.NER_model', 'NERModelLoader'),
    'batch_recognize_entities': ('Data_Masking.NER_model', 'batch_recognize_entities'),
}


def __getattr__(name):
    if name not in _EXPORT_MAP:
        raise AttributeError(f"module 'Data_Masking' has no attribute '{name}'")

    module_name, attr_name = _EXPORT_MAP[name]
    module = import_module(module_name)
    return getattr(module, attr_name)
