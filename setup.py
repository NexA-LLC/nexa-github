from setuptools import setup, find_packages

setup(
    name="nexa_github",
    version="0.1.0",
    packages=find_packages(),
    install_requires=[
        "requests",
        "PyGithub",
        "python-dotenv",
    ],
    entry_points={
        'console_scripts': [
            'github-branch-cleaner=nexa_github.cleanup.branch_cleaner:main',
        ],
    },
    author="GM Pacific Limited",
    author_email="info@gmpacific.com",
    description="GitHub操作用のユーティリティパッケージ",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/GM-Pacific-Limited/nexa-github",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.8",
) 