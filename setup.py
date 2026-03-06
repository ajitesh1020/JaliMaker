"""
JaliMaker – CNC Jali/Grill GCode Generator
"""
from setuptools import setup, find_packages

setup(
    name="jalimaker",
    version="3.3.0",
    description="Industrial CNC Jali/Grill GCode Generator for LinuxCNC",
    author="Ajitesh Kannojia",
    author_email="aji.ajitesh1020@gmail.com",
    license="MIT",
    packages=find_packages(),
    python_requires=">=3.10",
    install_requires=[
        "PySide6>=6.4.0",
        "numpy>=1.24.0",
    ],
    entry_points={
        "console_scripts": [
            "jalimaker=main:main",
        ]
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: POSIX :: Linux",
        "Topic :: Scientific/Engineering :: Human Machine Interfaces",
    ],
)
