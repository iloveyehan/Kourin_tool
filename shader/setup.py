# setup.py
# python setup.py build_ext --inplace
from setuptools import setup, Extension
from Cython.Build import cythonize
import numpy as np
import sys

ext_modules = [
    Extension(
        name="render",               # 编译出的模块名 renderer.pyd
        sources=["render.pyx"],      # 或 renderer.py
        include_dirs=[np.get_include()],
        language="c",                  # 纯 C 生成；如果需要 C++，改为 "c++"
    )
]

setup(
    name="imgui_render",
    ext_modules=cythonize(ext_modules, language_level=3, annotate=False),
    zip_safe=False,
)
