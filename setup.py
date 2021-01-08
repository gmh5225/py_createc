import setuptools

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setuptools.setup(
    name="createc",
    author="Chen Xu",
    author_email="chen.xu@aalto.fi",
    description="A python interface with Createc scanning probe microscope",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://version.aalto.fi/gitlab/xuc1/py_createc",
    packages=setuptools.find_packages(exclude=['scripts']),
    package_data={
        'createc': ['*.yaml'],        
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: Microsoft :: Windows",
        "Topic :: System :: Hardware :: Hardware Drivers",
        "Topic :: Scientific/Engineering :: Physics",
    ],
    python_requires='>=3.6',
)
