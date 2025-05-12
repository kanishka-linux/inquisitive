# Inquisitive: A personal self-hosted knowledge base with a touch of LLM/RAG

**Inquisitive** is a fully self-hosted LLM/RAG based application that allows you to create your own personal knowledge base which you can easily search and organize.

![Inquisitive](/images/inquisitive-pdf-rendering.png)

![Inquisitive](/images/inquisitive-screenshot.png)

## Features

* Upload files of various formats and store them in vector database for Retrieval-Augmented Generation (RAG)
* Add links/urls whose contents will be fetched automatically and will be added to the vector db
* Add links in bulk
* Crawl a given link recursively (Experimental)
* Add notes in markdown format with the capability to edit/delete later on from the UI itself.
* Focussed mode prompt shortcuts: `/links, /notes, /files` - to narrow down search based on source type.
* streamlit based UI for chat interface
* JWT based auth for basic user management based on fastapi and sqlite
* Multiple vector database backend support - default is `lancedb`.
* Ability to choose between multiple locally installed ollama models from the UI itself
* Listing of reference while discussing with ollama models
* View reference sources inline in case of notes and uploaded file.
* Ability to include/exclude particular references for better focussed search and discussion.
* Ability to select different window size of references - so that one can adjust the context size which will be sent to the llm models

## Installation

### Requirements

* Python 3.11+
* streamlit (for FE UI)
* fastapi (for BE API server)
* Lancedb/ChromaDB (Vector DB)
* Sqlite (Relational DB)
* ollama (locally running ollama instance)

### Ollama Installation
* Please follow the README from [Ollama github page](https://github.com/ollama/ollama)
* What Ollama models to pull?
  * If you've decent gpu consider pulling 7b models like `mistral:7b-instruct-q4_0`. I had good experience with 4b models as well like `gemma3:4b` 
  * If you don't have gpu available, consider pulling 1.5b models like `deepseek-r1:1.5b`, `qwen:1.8b` or `smollm:1.7b`
  * One can pull multiple models as needed and then can select amongst them from the UI
  * for embeddings Inquisitive uses `chroma/all-minilm-l6-v2-f32:latest` - since it is pretty fast for our usecase, but one can change the embedding model if needed from the `backend/config.py`
 

*Install Ollama, pull models and then start the ollama server*

```
$ ollama pull chroma/all-minilm-l6-v2-f32:latest
$ ollama pull mistral:7b-instruct-q4_0
$ ollama pull deepseek-r1:1.5b
$ ollama serve
```

### Install and run backend server and frontend chat interface

* Inquisitive is tested with Python 3.11, 3.12 and 3.13. Make sure any of the python version >= 3.11 is  available on the system.

* On some systems people may need to install `python-venv` package separately. Please install appopriate package on your distro/os as needed.

```
$ python3.11 -m venv venv
$ source venv/bin/activate
$ (venv) git clone https://github.com/kanishka-linux/inquisitive.git
$ (venv) cd inquisitive
$ (venv) pip install -e .
```

*Run backend and FE separately on separate terminals* - This is the preferred approach

```
Make sure you are in the same project directory and venv is activated on both the terminals 

$ (venv) inquisitive-start-backend (Terminal 1)
$ (venv) inquisitive-start-ui (Terminal 2)
```
After that UI will be available at `http://localhost:8501`

*Directly running backend and frontend servers - useful during development*

```
Make sure you are in the project directory and venv is activated

$ (venv) pip install -r requirements.txt
$ (venv) uvicorn backend.main:app --reload --port 8000 --log-level debug

Open Another terminal in the same project directory and activate venv

$ (venv) export STREAMLIT_BROWSER_GATHER_USAGE_STATS=false
$ (venv) streamlit run frontend/app.py
```

*Run both BE and FE servers using single command* - experimental

```
$ (venv) inquisitive-start (It will start both BE and FE. Starting BE may take some time on the first run)
```

## Notes on Installation and self-hosting

Inquisitive, is intended to run on your personal computer/laptop and thus it has been designed in such a way that everything can be installed locally as easily as possible. However, depending on where you want to install it some modifications maybe needed for ease of use and better security.

* For installing locally on your local network where security is not a major concern, nothing specific extra is needed and above installation instructions will work as it is, only make sure port 8000 (backend) and port 8501 (Frontend) are available. Use command `$ lsof -i :8501` and `lsof -i :8000` to re-verify nothing is running on the ports before starting the application.

* When installing on a shared network, make sure to setup https for extra layer of security. Please check documentation of uvicorn and streamlit on how to setup https certificates.

* When self-hosting on cloud or some vps provider, make sure to place reverse-proxy like nginx in front of the application and setup https certificate.

* If one wants to self-host Inquisitive for somewhat larger audience number (let's say 50+), then it may require a bit of different deployment strategy and depending on the scale some of the components may require some modifications. Please open github issue or contact via email (provided in the contacts section), in case people want to discuss how to deploy the application for a somewhat larger target audience.

## Config Directory

* When BE and FE server is started for the first time, a config directory is created in the home directory `~/.config/inquisitive`.

* The config directory will have two files `backend.env` and `frontend.env`. People can override default settings by providing new values in the respective env files.
    * For default settings values, take a look at `backend/config.py` and  `frontend/config.py`
    * If user decides to change default base directory or other directory locations using env variables then please make sure to create these directories manually.

* The directory will also have sqlite db and vector database data dir and also uploaded files as well notes. Therefore, it will be good if users can regularly backup the config directory.


## Motivation

Organizing notes and personal documents seems to be a simple task, but I myself struggled a lot with it on how to do it properly. Finally my setup was just plain text/markdown files and open the folder with vim/nvim and use fzf plugin for fuzzy search within the folder.

It served me well over the years, but since last couple of months I was mulling over integration with local LLM/RAG based system for somewhat better organization of personal knowledge base. I looked into existing solutions available, but I couldn't find integrated solutions that would combine notes/local documents/web-links. I was also interested in getting list of references along with a way to display various notes and files inline, so that it will be easier to cross-verify sources from which information is coming. I also felt, the application needs to have some basic authentication capabilities so that one can self-host it, allowing multiple users to share the instance and each having their own unique collection. So After all these requirements in mind, finally I decided to build Inquisitive.

## Technical choices and brief architecture overview

In the beginning, I wanted something simpler which could be built over a weekend, but after one feature after another, things started becoming a bit complex as well as a bit interesting also architecture wise for a self-hosted appllication. For those, who are interested in understanding tech choices and overall architecture, can go thorough the following details.

* **Choice of FE/UI:**

    * After searching the web, I found streamlit will work well for the use-case for building chat interaface and some basic UI. Initial impression about streamlit was really good, within a short time with the help of LLM, I was able to build some basic UI. It really helped me to get started with the project quickly. But as I wanted somewhat more and more features, I felt I'll need to add more components to the project. 

    * As streamlit is meant to be a stateless application and it has somewhat different design principles, it was getting harder to manage state with it for multiple users. For example, it starts new session every time whenever browser page is refreshed and it reruns the entire application once any state change in the UI component is detected. This made it a bit difficult to manage and reason about state. I've read comments in the forums that people have faced issues like  sessions intended for different users are able to see content of each other. This can easily happen, if one is not careful with session state management with streamlit.

    * So finally, I decided I'll need a dedicated backend to manage session state of a user and on the browser side let's store  token in localstorage, which will be sent to the BE for validation. This made things much more consistent and easier to reason about. So I ended up building a dedicated backend for managing auth flow and other state information. It proved to be a useful decision and made things much easier later on whenever I was adding more features.

* **Choice of Backend stack:**

    * Previously, some long time back, I built [Reminiscence](https://github.com/kanishka-linux/reminiscence) using Django. So this time also in the beginning, I was thinking about using the same stack. But then I thought, maybe let's check something leaner/minimal stack this time. I also wanted to play around with some framework that has better async support, and as I was also mainly concerned with building API server, finally decided to go with FastAPI. While using FastAPI, I was missing some of the features of Django like out of box user management/authentication and most importantly automatic database migration. However, as I was mainly looking for API server, so leaner FastAPI framework, started making more sense and I was able to add extra components as needed.

    * For ORM, I've used `sqlalchemy` to talk to sqlite database. Normally I prefer plain sql, instead of ORM, but in this case ORM provides ability to switch between multiple different database. In case someone wants to use postgres instead of sqlite, they should be able to switch to it, with some modification in configs.

* **Authentication:**

    * for user management and authentication, fastapi-users library is used
    * Backend generates JWT token for authentication.
    * People can easily change jwt algorithm, secret keys and expiry time for the token by modifying `backend/config.py`
    * At FE side, the token is saved locally in localstorage instead of cookies and FE sends this token with every API request to the BE.
    * New users can be registerd from streamlit UI itself, or this auto-register from the UI can be disabled by modifying `frontend/config.py` 

* **File Processing:**

    * Files/notes are uploaded and added to the queue for processing and immediately acknowledged after adding some metadata in sqlite db.

    * Background worker processes content of the job queue asynchronously

        * Ideally one should have used existing job queue/ worker solutions like celery backed by redis, but it would have made things a bit more complex for self-hosting purpose, so decided to write minimal job queue using `asyncio.queue` - that processes tasks in the background backed by sqlite db. It is not fast, but it is good enough for the current use-case. Currently there is no retry mechanism, but will provide some way to retry and list failed jobs later on if needed. Please make sure, not to shutdown the backend, before jobs are completed.
        * I also considered using built-in background-task available in FastAPI, but I also wanted somewhat better control over the tasks like separate queue for different types of tasks, so decided to go with custom job queue.

    * Files are chunked and then converted into embeddings and stored in vector database for efficient searching

    * Some information about files are stored sqlite db, such as their processing status.

    * Sqlite db also helps in some other basic API operations on files like list/get etc..

* **Choice of vector database**

    * Initially after some search, I decided to use chroma db as it was easy to setup locally. But after storing thousands of web-links (from my bookmark) and their content in it, I felt a bit sluggishness in the response. Inquisitive allows multiple filters based on metadata and source type, which allows to include/exclude references from the search. Therefore, it was necessary to add index on the metadata fields in case of large document collection - which chroma db didn't allow. Therefore, I had to look for some other options, and finally settled for [lancedb](https://github.com/lancedb/lancedb) as a default vector database, since it has good support for indexing metadata fields, along with very easy installation process without any client server architecture. After using `lancedb`, performance difference was noticeable.  
    * Support for chroma db is still there and people can easily switch between the two by making some changes in `backend/config.py`. There is also support for `milvus-lite` - which I wasn't able to test properly, but kept support for it also. People can check which vector database works for them best and switch to it.

* **Search and Response:**

    * A correct query is formed after applying filter and user info. The query flows through the vector database
    * After results are obtained, another layer of filtering is applied in case of links or urls, to pick up the unique urls.
    * For web-links, in order to get x set of results, inquisitive will fetch 10x relevant documents and after that unique urls will be picked up. 
    * In case of notes and files, unique links are not fetched, and one can get multiple references from the same document. Users can easily include/exclude selected document - which will be or won't be considered for next set of search based on filtering  criteria.
    * After that, Streamlit directly interacts with OLLAMA for final processing, once relevant results are obtained from vector db.

*  **Note Taking:**

    * Notes can be added via the UI in the mardkown format.
    * Some basic, Notes metadata is stored in the sqlite and the actual file in markdown format will be stored in the dedicated `upload directory`, after that content will be stored in vector db.
    * Notes can be edited and can be listed down using `/notes-list` prompt
    * After notes are edited and saved again, the content in the vector database will be refreshed accordingly
    * One can directly search within notes  with `/notes` prompt 

* **Reference section:**

    * For every search result, references are listed down
    * Reference window size can be adjusted via the UI and those many references will be picked up for discussion/QnA session.
    * There is a way to get only references, without any discussion mode.
    * References will have both include/exclude buttons and view documents button - wherever possible.
    * Locally stored documents and notes can be viewed inline, without opening them separately.
    * Ability to view local sources as it is has been added, so that one can easily cross verify the information within the application itself.

* **Basic CRUD operations on Notes/Links/Files:**

    * After adding notes, links and uploading files, I thought, it is necessary to have some basic operations on them for better management. So I've added prompts for listing these resources and also provided some operations like update/delete wherever possible. For these basic CRUD operations, having relational db like sqlite proved to be useful  - which has all the important details for these operations. Following are the prompts for listing of the respective resources.

        * `/notes-list`

        * `/files-list`

        * `/links-list`

    * Pagination value can be controlled via config `LIST_PAGE_SIZE` defined in `frontend/config.py`

    * When Deleting notes and files - only soft kind of delete will be done and entries will be removed from db (both relational and vector), but original files will be kept in the uploaded directory and won't be deleted via UI. Users will need to delete the files manually from upload directory.


## Sequence diagram for general flow

![sequence-diagram](/images/sequence-diagram.png)

* API documentation: After running the backend, API documentation can be found at `http://localhost:8000/redoc`.
* As BE is completely separated, anyone intending to build differnt UI, will be able to do it by following BE API documentation.

## So After building, is it really serving the purpose it is supposed to serve?

* **Web Links** - I fed thousands of links to Inquisitive (from my bookmark) which I've accumulated over the years. One can just export your browser bookmark in json or any format or just dump list of links in plain text format and give it to inquisitive. It will do regex and find all relevant http links from the documents. I was quite a bit surprised to find that, after using inquisitive with focussed search mode for links i.e. `/links`, I was able to get some really good recommendations from my personal collection which I might have forgotten over a period of time. And I didn't even feel like adding tags or anything extra to extract relevant results. It seems like one can even build personal search engine, in case one has lots of links in the bookmark.

* **Adding notes** - After feeding my notes to Inquisitive, retrieving relevant information was quick enough  (`/notes`). It is still early to comment about this feature. But having the ability to see notes in markdown and edit it and refresh the updated data in vector db on edit, seeing all the reference notes in the sidebar - made things lot more convenient when it came to searching and organizing notes. My only gripe is, not so good editor for markdwon. Currently I'm using Streamlit's in-built text-area component for adding notes, which could have been better.

* **Discussion/QnA session with LLM**  - Quality of this depends a lot upon the model. Models with 7B+ parameter give really good result provided the machine has dedicated gpu. For machines with only cpu, models with 1-2B+ parameters can give response a bit quickly, but they are mostly irrelevant and not upto the mark and too much hallucination. So machines with only CPU, can use Inquisitive mainly for organizing the knowledge-base and searching efficiently within it, but not for relevant discussion/QnA purpose. People can try out multiple models and see what works for them best. I tried using LLM with following different setup.

    * *Intel Based Mac (no dedicated gpu)* - Any model greater that 1.5b parameter was hardly usable. I got some good experience with `deepseek-r1:1.5b` compared to other models in similar range. But experience was still not upto the mark. I'll prefer not to use discussion mode in such cases and just use `inquisitive` for searching and organizing the personal knowledge base.

    * *AWS g4dn.xlarge instance with 1 NVIDIA gpu* (with Ubuntu 24.04 LTS) - With 7b mistral model, it felt like flying - really good speed which made local LLM actually usable. I wrote few scripts to turn the instance ON and OFF from CLI, so that I could start/shutdown the instance when not in use with just one command. I also had to setup port forwarding, so that I could use the instance without exposing it publicly for testing purpose. After writing some systemd startup scripts for starting BE/FE server, I was able to start and access the application with just one command. This AWS EC2 instance is really good if one wants to play and test around with various LLM models (that fits within the memory limits).

    * *Apple Silicon Mac (M4 with 16GB of Unified memory CPU+GPU)* - 4b models like `gemma3:4b` worked really well with it along with mistral:7b model. Any LLM model with size more than 7-8 GB, will start to feel a bit slower. But Overall experience is good, and I think one can use discussion mode regularly and can send moderate context window size to local LLM (for RAG) without impacting quality of experience.


## Some Fun Facts

* This is my first major personal project, where I've used LLM models extensively while coding. I was really surprised, how much LLM can help us get it done within a short period of time. In professional setting, I've mainly worked with `elixir` and `golang` based tech stack for building backend services. I didn't get chance to work on python based stack so far in professional setting. I have used python based stack for my personal projects and I haven't started any greenfield project in it for a long time. So, I wasn't aware of latest trends in python web frameworks. But despite  of all these, when I felt like building new project again, LLMs proved to be very helpful to get started with comparatively new frameworks like streamlit and fastapi and helped in generating good amount of boilerplate code easily. At first, I was simply amazed and understood why there is a craze for AI assisted coding.

* When I wanted to add some basic auth to streamlit app, LLM helped in generating some basic code within an hour. I thought, my work has become simpler and started daydreaming how much time I can save with LLMs if used for coding regularly. But then in the next hour, I came back to ground reality. The generated code and the approach suggested by the LLM had so many subtle bugs - which were difficult to pin-point in the beginning.

* In order to debug the code - which was generated within an hour, I had to spend next `two days` just to debug why things are not working as expected. Finally, I had to reach out to official documentation and various forums, to understand the issues in details which gave me better understanding. I prompted to LLM - `You have given me wrong answer and what you suggest is not possible for the framework`, then LLM's reply was - `You are absolutely right, you've pinpointed the root cause of the problem, now let's start digging into it in details`. And then I thought to myself - `If that was the case, why did I spend two days in the wrong direction`. I chuckled and laughed at both myself and LLM. Even in the age of AI, there seems to be no substitue for traditional way of learning by going through books, official documentation and various forum/blogs posts - to build better understanding. It was nice learning experience about what AI can do and what it can't.

* LLMs can surely boost productivity as a coding assistance, there is no denying about that. But over-reliance on them can surely backfire, if one can't understand, test and review the code written by AI. I'm hearing about AI assited code review, a lot, every now and then, but there is still need for human assisted code review of code written by AI. In this day and the age, it looks like both are complimentary to each other. However, I think, there is no substitute for checking references whenever possible when discussing with AI and ability to question AI if you can't make sense of it in rational logical manner.

* By the way this entire README is written by human not AI, you will surely find lot of grammatical mistakes and typos :)

## Some known limitations of Inquisitive

* If you want to start discussion on different topic, you'll need to clear existing chat messages

* To process thousands of links, Inquisitive will take quite a bit amount of time. During that period please don't shut-down the backend, since pending jobs won't get picked up when the backend service starts again. It is on TODO list, to allow commands to pick up pending jobs after restart.


## Copyright And License

**Inquisitive** is distributed under **AGPL v3.0** License

Copyright © 2025 Abhishek K

SPDX-License-Identifier: AGPL-3.0-or-later

For the full license text, see the LICENSE file in the repository or visit https://www.gnu.org/licenses/agpl-3.0.html.

## Contacts

* [E-mail](mailto:kanishka.linux@gmail.com)
