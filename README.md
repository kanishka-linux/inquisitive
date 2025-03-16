# Inquisitive: A personal self-hosted knowledge base with touch of LLM/RAG

**Inquisitive** is a fully self-hosted LLM/RAG based application that allows you to create your own personal knowledge base which you can easily search and organize.

![Inquisitive](/images/inquisitive-pdf-rendering.png)

![Inquisitive](/images/inquisitive-screenshot.png)

## Features

* Upload files of various formats and store them in vector database
* Add links/urls whose contents will be fetched automatically and will be added to the vector db
* Add links in bulk or crawl a given link recursively
* Add notes in markdown format with the capability to edit later on
* Focussed mode prompt shortcuts: `/links, /notes, /files` - to narrow down search based on source type.
* streamlit based UI for chat interface
* JWT based auth for basic user management based on fastapi and sqlite
* Langchain chroma db for vector database
* Ability to choose between multiple locally installed ollama models from the UI itself
* Listing of reference while discussing with ollama models
* View reference sources inline in case of notes and uploaded file.
* Ability to include/exclude particular references for better focussed search and discussion
* Ability to select different window size of references - so that one can adjust the context size which will be sent to the llm models

## Installation

### Requirements

* Python 3.12+
* streamlit (for UI)
* fastapi   (for BE API server)
* ollama    (locally running ollama instance)

### Ollama Installation
* Please follow the README from [Ollama github page](https://github.com/ollama/ollama)
* What Ollama models to pull?
  * If you've decent gpu consider pulling 7b models like `mistral:7b-instruct-q4_0`
  * If you don't have gpu available, consider pulling 1.5b models like `deepseek-r1:1.5b`, `qwen:1.8b` or `smollm:1.7b`
  * One can pull multiple models as needed and then can select amongst them from the UI
  * for embeddings Inquisitive uses `chroma/all-minilm-l6-v2-f32:latest` - since it is pretty fast for our usecase, but one can change the embedding model if needed from the config.Settings
 

*Install Ollama, pull models and then start the ollama server*

```
$ ollama pull chroma/all-minilm-l6-v2-f32:latest
$ ollama pull mistral:7b-instruct-q4_0
$ ollama pull deepseek-r1:1.5b
$ ollama serve
```

*Install and run backend auth server and frontend chat interface*

```
$ python3.12 -m venv venv
$ source venv/bin/activate
$ git clone https://github.com/kanishka-linux/inquisitive.git
$ cd inquisitive
$ pip install -r requirements.txt
$ uvicorn backend.main:app --reload --port 8000

Open Another terminal in the same git directory

$ source ../venv/bin/activate
$ export STREAMLIT_BROWSER_GATHER_USAGE_STATS=false
$ streamlit run frontend/app.py
```

## Motivation

Organizing notes and personal documents seems to be a simple task, but I myself struggled a lot with it on how to do it properly. Finally my setup was just plain text/markdown files and open the folder with vim/nvim and use fzf plugin for fuzzy search within the folder.

It served me well over the years, but since last couple of months I was mulling over integration with local LLM/RAG based system for somewhat better organization of personal knowledge base. I looked into existing solutions available, but I couldn't find integrated solutions that would combine notes/local documents/web-links and getting list of references along with a way to display varrious notes and files inline, so that it will be easier to cross-verify sources from which information is coming. I also felt, the application needs to have some basic authentication capabilities so that one can self-host it, allowing multiple users to share the instance and each having their own unique collection. So After all these requirements in mind, finally I decided to build Inquisitive.

## Technical choices

Actually I wanted something simpler which could be built over a weekend, but after one feature after another, things became a bit complex architecture wise for a self-hosted appllication.

After searching the web, I found  streamlit will work well for the use-case for building chat interaface and some basic UI, but for anything apart from that, I had to look for somewhere else. As streamlit is meant to be a stateless application and it has somewhat different design principles, it was getting harder to manage state with it for multiple users. So I had to build a dedicated backend for managing auth flow and other state information. It required good amount of refactring and finally I was able to separate out both FE and BE completely, which proved to be useful when adding more features and made things easier to reason about.

Currently - Inquisitive has following broad components

* **Authentication:**
    * User logs in through Streamlit UI Login page
    * Backend generates JWT token
    * Token is saved locally for future authenticated requests

* **File Processing:**
    * Files/notes are uploaded and added to the queue for processing and immediately acknowledged after adding some metadata in sqlite db.
    * Background worker processes content of the job queue asynchronously
        * Ideally one should have used existing job queue/ worker solutions like celery backed redis, but it would have made things even more complex for self-hosting purpose, so decided to write minimal job queue using `asyncio.queue` - that processes tasks in the background backed by sqlite db. Currently there is no retry mechanism, but will provide some way to retry and list failed jobs later on if needed. 
    * Vector database stores processed documents for efficient searching
    * After that the record in sqlite db is marked with finished status

* **Search and Response:**
    * All search requests include the JWT token for authentication
    * A correct query is formed after applying filter and user info. The query flows through the vector database
    * After results are obtained, another layer of filtering is applied in case of links or urls, to pick up the unique urls.
    * Streamlit directly interacts with OLLAMA for final processing, once relevant results are obtained from vector db.

*  **Note Taking:**
    * Notes can be added via the UI.
    * Notes metadata is stored in the sqlite and the actual file in markdown format will be stored in the dedicated `upload directory`, after that content will be stored in vector db.
    * Notes can be edited and can be listed down using `/notes-list` prompt

* **Reference section:**
    * For every prompt, references are listed down
    * Reference window size can be adjusted via the UI and those many references will be picked up for discussion/QnA session.


## Sequence diagram for general flow

![sequence-diagram](/images/sequence-diagram.png)

## So After building, is it really serving the purpose it is supposed to serve?

* I fed thousands of links to it (from my bookmark) which I've accumulated over the years. I was quite a bit surprised to find that, after using inquisitive with focussed search mode for  links i.e. `/links`, I was able to get some really good recommendations from my personal collection which I might have forgotten over a period of time. And I didn't even feel like adding tags or anything extra to extract relevant results. It seems like one can even build personal search engine, in case one has lots of links in the bookmark.

* Adding notes - After feeding my notes to Inquisitive, retrieving relevant information was quick enough  (`/notes`). It is still early to comment about this feature. But having the ability to see notes in markdown and edit it and refresh the updated data in vector db on edit, seeing all the reference notes in the sidebar - made things lot more convenient when it came to searching and organizing notes. My only gripe is, not so good editor for markdwon. Currently I'm using Streamlit's in-built text-area component for adding notes, which could have been better.

* Discussion/QnA session with LLM  - Quality of this depends a lot upon the model. Models with 7B+ parameter give really good result provided the machine has dedicated gpu. For machines with only cpu, models with 1-2B+ parameters can give response a bit quickly, but they are mostly irrelevant and not upto the mark and too much hallucination. So machines with only CPU, can use Inquisitive mainly for searching purpose but not for relevant discussion/QnA purpose. People can try out multiple models and see what works for them best.
