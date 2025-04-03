from setuptools import setup, find_packages

setup(
    name='nexa-github',  # モジュール名はハイフンを使用
    version='0.0.1',
    packages=find_packages(),
    description='Nexa GitHub module',
    author='Nexa',
    author_email='support@nex-a.net',
    url='https://github.com/NexA-LLC/nexa-github',  # GitHubのURL
    install_requires=[
        'requests==2.31.0',
        'python-dotenv==1.0.1',
        'PyGithub==2.2.0',
        'jira==3.5.2',
    ],
    classifiers=[
        'Programming Language :: Python :: 3',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
    ],
    python_requires='>=3.6',
) 