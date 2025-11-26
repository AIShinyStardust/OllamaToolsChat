from setuptools import setup, find_packages

setup(
    name="aiss_ollama_tools_chat",
    version="0.2.0",
    packages=find_packages(),
    install_requires=[
        "ollama",
        "ollama-chat"
    ],
    entry_points={
        "console_scripts": [
            "ollama-tools-chat=aiss_ollama_tools_chat.run:main",
        ],
    },
    author="Miguel Ángel Cueto Gómez-Morán",
    author_email="yosoysoloyo1991@gmail.com",
    description="Autonomous tool chatbot using Ollama",
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    url="https://github.com/MiguelAngelCGM/OllamaToolsChat",
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.7',
)
