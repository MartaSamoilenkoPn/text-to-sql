Install Ollama (One-Time Setup)

Ollama is the service that will run the free LLM on your computer.

Go to https://ollama.com and download the application for your OS (Mac, Windows, or Linux).

Install it.

Open your terminal and pull a model. Llama 3 8B is a great default. It will download the model (it's a few GB).

```
ollama pull llama3:8b
```
Ollama is now running in the background. You don't need to do anything else with it.

Run:
```
python chat.py
```
