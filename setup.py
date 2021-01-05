import setuptools

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setuptools.setup(
    name="createc",
    version="0.0.1",
    author="Chen Xu",
    author_email="chen.xu@aalto.fi",
    description="A python interface with Createc scanning probe microscope",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://version.aalto.fi/gitlab/xuc1/py_createc",
    packages=setuptools.find_packages(where='createc'),
    package_dir={
        '': 'createc',        
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: Windows",
    ],
    python_requires='>=3.6',
)