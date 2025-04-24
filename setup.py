from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

with open("requirements.txt", "r", encoding="utf-8") as fh:
    requirements = fh.read().splitlines()

setup(
    name="document-qa-assistant",
    version="1.0.0",
    author="Taha Almasri",
    author_email="taha.almasri@ymail.com",
    description="A hybrid RAG document Q&A system with knowledge graph capabilities",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/ttaahhaa/document-qa-assistant",
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.8",
    install_requires=requirements,
    entry_points={
        "console_scripts": [
            "document-qa=app.main:main",
        ],
    },
)
