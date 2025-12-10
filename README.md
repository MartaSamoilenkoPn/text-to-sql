# 📝 text-to-sql

Turn natural language into SQL queries using local LLMs. This project leverages **Ollama** and **Gradio** to provide an easy-to-use interface for SQL generation and benchmarking.

-----

## 🦙 Prerequisites: Ollama Setup

*(One-Time Setup)*

**Ollama** is the service that runs the local Large Language Model (LLM) on your machine.

1.  **Download:** Go to [ollama.com](https://ollama.com) and download the application for your OS (Mac, Windows, or Linux).
2.  **Install:** Run the installer.
3.  **Pull Model:** Open your terminal and pull the recommended model (`qwen3:4b-instruct`) to get started.

```bash
ollama pull qwen3:4b-instruct
```

> **Note:** Once installed, Ollama runs quietly in the background. You do not need to keep a separate terminal window open for it.

-----

## ⚙️ Installation

It is recommended to use a virtual environment to keep your dependencies clean.

```bash
# 1. Create a virtual environment (optional but recommended)
python3 -m venv venv

# 2. Activate the environment
# On Mac/Linux:
source venv/bin/activate
# On Windows:
# .\venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt
```

-----

## 🚀 Usage

Start the application with a single command:

```bash
python app.py
```

The Gradio interface will launch automatically. Access it in your browser at:
👉 **http://localhost:7860**

-----

## 📊 Benchmarking

This project includes tools to benchmark the model's performance against the Spider dataset.

### 1\. Setup

Prepare the environment for benchmarking:

```bash
sh ./benchmark/setup_benchmark.sh
```

### 2\. Run Benchmark

Execute the benchmark using your specified model:

```bash
python -m benchmark.benchmark_spider --model qwen3:4b-instruct
```

### 3\. Analyze Results

View the metrics and results of the benchmark run:

```bash
python -m benchmark.analyze_results --file_path ./benchmark/benchmark_results_qwen3:4b-instruct.jsonl
```