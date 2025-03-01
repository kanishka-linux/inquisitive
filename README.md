# LLM/RAG based self-hosted knowledge base

**Inquisitive** is a fully self-hosted LLM/RAG based application that allows you to create your own personal knowledge base which you can easily search and organize.

## Features

* Upload files of various formats and store them in vector database
* Add links/urls whose contents will be fetched automatically and will be added to the vector db
* Add arbitrary random text as input
* streamlit based UI for chat interface
* JWT based auth for basic user management based on fastapi and sqlite
* Ability to choose between multiple locally installed ollama models from the UI itself
* Listing of reference while discussing with ollama models
* Ability to include/exclude particular references for better focussed search and discussion
* Ability to select different window size of references - so that one can adjust the context size which will be sent to the llm models

## Installation

### Requirements

* Python 3.12+
* streamlit
* fastapi
* ollama

### Ollama Installation
* Please follow the README from [Ollama github page](https://github.com/ollama/ollama)
* What Ollama models to pull?
  * If you've decent gpu consider pulling 7b models like `mistral:7b-instruct-q4_0`
  * If you don't have gpu available, consider pulling 1.5b models like `deepseek-r1:1.5b`, `qwen:1.8b` or `smollm:1.7b`
  * One can pull multiple models as needed and then can select amongst them from the UI
  * for embeddings Inquisitive uses `chroma/all-minilm-l6-v2-f32:latest` - since it is very fast works well on both cpu and gpu
 

*Install Ollama, pull models and then start the ollama server*

```
$ ollama pull chroma/all-minilm-l6-v2-f32:latest
$ ollama pull mistral:7b-instruct-q4_0
$ ollama serve
```

*Install backend auth server and frontend chat interface*

```
$ python3.12 -m venv venv
$ source venv/bin/activate
$ git clone https://github.com/kanishka-linux/inquisitive.git
$ cd inquisitive
$ pip install -r requirements.txt
$ uvicorn backend.main:app --reload --port 8000 (from one terminal)
$ streamlit run frontend/app.py (from another terminal)
```

