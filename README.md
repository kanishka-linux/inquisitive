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
* Multiple vector database backend support - default is lancedb.
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
$ ./start.sh
```

*In case above startup script is not working, one can start backend and FE server separately as below:

```
$ uvicorn backend.main:app --reload --port 8000

Open Another terminal in the same project directory

$ source ../venv/bin/activate
$ export STREAMLIT_BROWSER_GATHER_USAGE_STATS=false
$ streamlit run frontend/app.py
```

## Motivation

Organizing notes and personal documents seems to be a simple task, but I myself struggled a lot with it on how to do it properly. Finally my setup was just plain text/markdown files and open the folder with vim/nvim and use fzf plugin for fuzzy search within the folder.

It served me well over the years, but since last couple of months I was mulling over integration with local LLM/RAG based system for somewhat better organization of personal knowledge base. I looked into existing solutions available, but I couldn't find integrated solutions that would combine notes/local documents/web-links and getting list of references along with a way to display varrious notes and files inline, so that it will be easier to cross-verify sources from which information is coming. I also felt, the application needs to have some basic authentication capabilities so that one can self-host it, allowing multiple users to share the instance and each having their own unique collection. So After all these requirements in mind, finally I decided to build Inquisitive.

## Technical choices

Actually I wanted something simpler which could be built over a weekend, but after one feature after another, things became a bit complex as well as a bit interesting also architecture wise for a self-hosted appllication. For those, who are interested in understanding tech choices, can go thorough the following details.

* **Choice of FE/UI:**

    * After searching the web, I found streamlit will work well for the use-case for building chat interaface and some basic UI. Initial impression about streamlit was really good, within a short time with the help of LLM, I was able to build some basic UI. It really helped me to get started with the project quickly. But as I wanted somewhat more and more features, I felt I'll need to add more components to the project. 

    * As streamlit is meant to be a stateless application and it has somewhat different design principles, it was getting harder to manage state with it for multiple users. For example, it starts new session every time whenever browser page is refreshed and it reruns the entire application once any state change in the UI is detected. This made it a bit difficult to manage and reason about state. I've read comments in the forums that people have faced issues like  sessions intended for different users are able to see content of each other. This can easily happen, if one is not careful with session state management with streamlit.

    * So finally, I decided I'll need dedicated backend to manage session state of a user and on the browser side let's store  token in localstorage, which will be sent to the BE for validation. This made things much more consistent and easier to reason about. So I had to build a dedicated backend for managing auth flow and other state information. It proved to be a useful decision and made things much easier later on whenever I was adding more features.

* **Choice of Backend stack:**

    * Previously, some long time back, I built [Reminiscence](https://github.com/kanishka-linux/reminiscence) using Django. So this time also in the beginning, I was thinking about using the same stack. But then I thought, maybe let's check something leaner/minimal stack this time. I also wanted to play around with some framework that has better async support, and as I was also mainly concerned with building API server, finally decided to go with FastAPI. While using FastAPI, I was missing some of the features of Django like out of box user management/authentication and most importantly automatic database migration. However, as I was mainly looking for API server, so leaner FastAPI framework, started making more sense and I was able to add extra components as needed.

* **Authentication:**
    * for user management and authentication, fastapi-users library is used
    * Backend generates JWT token for authentication.
    * People can easily change algorithm, keys and expiry time for the token by modifying `backend/config.py`
    * At FE side, the token is saved locally in localstorage instead of cookies and uses this token while making every API request to BE.
    * New users can be registerd from streamlit UI itself, or this auto-register from the UI can be disabled by modifying `frontend/config.py` 

* **File Processing:**
    * Files/notes are uploaded and added to the queue for processing and immediately acknowledged after adding some metadata in sqlite db.
    * Background worker processes content of the job queue asynchronously
        * Ideally one should have used existing job queue/ worker solutions like celery backed redis, but it would have made things even more complex for self-hosting purpose, so decided to write minimal job queue using `asyncio.queue` - that processes tasks in the background backed by sqlite db. It is not fast, but it is good enough for the current use-case. Currently there is no retry mechanism, but will provide some way to retry and list failed jobs later on if needed. Please make sure, not to shutdown the backend, before jobs are completed.
        * I also considered using built-in background-task available in FastAPI, but I also wanted somewhat better control over the tasks like separate queue for different types of tasks, so decided to go with custom job queue.
    * Files are chunked and then converted into embeddings and stored in vector database for efficient searching
    * Some information about files are stored sqlite db, such as their processing status.
    * Sqlite db also helps in some other basic API on files like list/get etc..

* **Choice of vector database**
    * Initially after some search, I decided to use chroma db as it was easy to setup locally. But after storing thousands of web-links (from my bookmark) and their content in it, I felt a bit sluggishness in the response. Inquisitive allows multiple filters based on metadata and source type, which allows to include/exclude references from the search. Therefore, it was necessary to add index on the metadata fields in case of large document collection - which chroma db didn't allow. Therefore, I had to look for some other options, and finally settled for `lancedb` as a default vector database, since it has good support for indexing metadata fields, along with very easy installation process without any client server architecture. Support for chroma db is still there and people can easily switch between the two by making some changes in `backend/config.py`. There is also support for `milvus-lite` - which I wasn't able to test properly, but kept support for it also. People can check which vector database works for them best and switch to it.

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
    * For every search prompt, references are listed down
    * Reference window size can be adjusted via the UI and those many references will be picked up for discussion/QnA session.
    * There is a way to get only references, without any discussion mode.
    * References will have both include/exclude buttons and view documents button - wherever possible.
    * Locally stored documents and notes can be viewed inline, without opening them separately.
    * Ability to view local sources as it is has been added, so that one can easily cross verify the information within the application itself.


## Sequence diagram for general flow

![sequence-diagram](/images/sequence-diagram.png)

## So After building, is it really serving the purpose it is supposed to serve?

* I fed thousands of links to Inquisitive (from my bookmark) which I've accumulated over the years. One can just export your browser bookmark in json or any format or just dump list of links in plain text format and give it to inquisitive. It will do regex and find all relevant http links from the documents. I was quite a bit surprised to find that, after using inquisitive with focussed search mode for links i.e. `/links`, I was able to get some really good recommendations from my personal collection which I might have forgotten over a period of time. And I didn't even feel like adding tags or anything extra to extract relevant results. It seems like one can even build personal search engine, in case one has lots of links in the bookmark.

* Adding notes - After feeding my notes to Inquisitive, retrieving relevant information was quick enough  (`/notes`). It is still early to comment about this feature. But having the ability to see notes in markdown and edit it and refresh the updated data in vector db on edit, seeing all the reference notes in the sidebar - made things lot more convenient when it came to searching and organizing notes. My only gripe is, not so good editor for markdwon. Currently I'm using Streamlit's in-built text-area component for adding notes, which could have been better.

* Discussion/QnA session with LLM  - Quality of this depends a lot upon the model. Models with 7B+ parameter give really good result provided the machine has dedicated gpu. For machines with only cpu, models with 1-2B+ parameters can give response a bit quickly, but they are mostly irrelevant and not upto the mark and too much hallucination. So machines with only CPU, can use Inquisitive mainly for organizing the knowledge-base and searching efficiently within it, but not for relevant discussion/QnA purpose. People can try out multiple models and see what works for them best.

## Some Fun Facts

* This is my first major personal project, where I've used LLM models extensively while coding. I was really surprised, how much LLM can help us get it done within a short period of time. In professional setting, I've mainly worked on `elixir and golang` based tech stack and mostly worked on the backend side of things that involved heavy usage of postgres/redis. I haven't used python so far in professional setting. I use python based stack for my personal projects and I haven't started any greenfield python project for a long time. So, I wasn't aware of latest trends in python web frameworks. But despite  of all these, when I felt like building new project again, LLMs proved to be very helpful to get started with comparatively new frameworks like streamlit and fastapi and helped in generating good amount of boilerplate code easily. At first, I was simply amazed and understood why there is a craze for AI assisted coding.

* When I wanted to add some basic auth to streamlit app, LLM helped in generating some basic code within an hour. I thought, my work has become simpler and started day-dreaming how much time I can save with LLMs if used for coding regularly. But then in the next hour, I came back to ground reality. The generated code and the approach suggested by the LLM had so many subtle bugs - which were difficult to pin-point in the beginning.

* In order to debug the code - which was generated within an hour, I had to spend next `two days` just to debug why things are not working as expected. Finally, I had to reach out to official documentation and various forums, to understand the issues in details which gave me better understanding. I prompted to LLM - `You have given me wrong answer and what you suggest is not possible for the framework`, then LLM's reply was - `You are absolutely right, you've pinpointed the root cause of the problem, now let's start digging into it in details`. And then I thought to myself - `If that was the case, why did I spend two days in the wrong direction`. I chuckled and laughed at both myself and LLM. Even in the age of AI, there seems to be no substitue for traditional way of learning by going through books, official documentation and various forum/blogs posts - to build better understanding. It was nice learning experience about what AI can do and what it can't.

* LLMs can surely boost productivity as a coding assistance, there is no denying about that. But over-reliance on them can surely backfire, if one can't understand, test and review the code written by AI. I'm hearing about AI assited code review, a lot, every now and then, but there is still need for human assisted code review of code written by AI. In this day and the age, it looks like both are complimentary to each other. However, I think, there is no substitute for checking references whenever possible when discussing with AI.

* By the way this entire README is written by human not AI, you will surely find lot of grammatical mistakes and typos :)

## Some known limitations of Inquisitive

* If you want to start discussion on different topic, you'll need to clear existing chat messages

* To process thousands of links, Inquisitive will take quite a bit amount of time. During that period please don't shut-down the backend, since pending jobs won't get picked up when the backend service starts again. It is on TODO list, to allow commands to pick up pending jobs after restart.

## Contacts

* People can contact me on the email provided on the github profile page.
