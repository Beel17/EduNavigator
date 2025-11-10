"""Setup script for the application."""
from setuptools import setup, find_packages

setup(
    name="nigerian-grants-agent",
    version="1.0.0",
    description="AI Agent for Web-Scraping Nigerian Grants/Scholarships/Policies",
    author="Your Name",
    packages=find_packages(),
    install_requires=[
        # Dependencies will be installed from requirements.txt
    ],
    python_requires=">=3.9",
)

