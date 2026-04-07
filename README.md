# 🔬 RTL Bug Prioritization & Impact Analyzer

An advanced, high-performance offline-capable EDA (Electronic Design Automation) intelligence tool that combines strong static analysis, graph-based dependency mapping, and Machine Learning (Random Forest) to detect, prioritize, and explain RTL (Verilog/VHDL) bugs.

This platform bridges the gap between traditional linting tools and modern ML-assisted debugging. By analyzing the structural dependencies of hardware code, the analyzer can determine whether a bug is isolated or if it will cascade and cause critical system failures.

**🌐 Access the hosted product:** [https://rtl-bug-prioritization-impact-analy.vercel.app/](https://rtl-bug-prioritization-impact-analy.vercel.app/)

---

## ✨ Key Features

- **High-Performance Static Analysis:** Uses custom parsing (via `pyverilog`/`PLY`) to extract module hierarchies, signal arrays, and logical assignments.
- **Dependency Graph Generation:** Automatically maps signals using `NetworkX` to understand how data propagates through the design.
- **ML-Powered Severity Scoring:** A trained Scikit-Learn model dynamically calculates a `severity_score` (0-100) based on graphical indicators (e.g., fan-out, critical path length, bug type frequency, and module importance). 
- **Explainable AI (XAI):** Doesn't just give you a score. Automatically generates clear, human-readable explanations detailing *why* a bug is severe and *how* it impacts the broader system.
- **Responsive HTML/JS Dashboard:** Provides a premium, dark-mode, hackathon-ready user interface powered by pure HTML, CSS, and Vanilla JavaScript, with interactive Plotly graphs.
- **API First:** Built on top of a lightning-fast `FastAPI` architecture, making it ready to be integrated into CI/CD pipelines or deployed as a microservice.
- **Serverless Deployable:** Fully optimized for zero-config deployments to platforms like Vercel, Railway, or Render.

---

## 🛠️ Technology Stack

- **Backend / API:** [FastAPI](https://fastapi.tiangolo.com/), Uvicorn
- **Frontend / Visualization:** HTML5, CSS3, Vanilla JS, [Plotly.js](https://plotly.com/javascript/)
- **Static Analysis & Parsing:** [PyVerilog](https://github.com/PyHDI/Pyverilog), PLY (Python Lex-Yacc)
- **Graph & Math:** [NetworkX](https://networkx.org/), NumPy
- **Machine Learning:** [Scikit-Learn](https://scikit-learn.org/) (Random Forest Regressor)

---

## 🚀 Getting Started

Follow these instructions to set up the analyzer locally. The system is designed to run entirely offline with no external dependencies once installed.

### 1. Prerequisites

Make sure you have **Python 3.9+** installed on your system.

### 2. Installation

Clone the repository and install the required dependencies:

```bash
# Clone the repository (if applicable)
git clone <your-repo-url>
cd rtl-bug-analyzer

# Setup a virtual environment (Recommended)
python -m venv venv

# Activate the virtual environment
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

# Install the requirements
pip install -r requirements.txt
```

### 3. Running the Analyzer Locally

You can launch both the backend API and the frontend dashboard with a single command. 

```bash
python run.py
```

`run.py` acts as a smart launcher. It kicks off the FastAPI server via Uvicorn on `http://localhost:8000` and automatically opens a new browser tab for you. 

*If your browser does not open automatically, simply navigate to `http://localhost:8000`.*

---

## 🏗️ Project Architecture

The codebase is split cleanly between the frontend and a 9-stage analysis backend pipeline:

```text
rtl-bug-analyzer/
├── backend/
│   ├── main.py                # FastAPI endpoints & application server
│   ├── pipeline.py            # Orchestrator for the 9-stage analysis
│   ├── parser/                # Stage 1: RTL lexing and syntax tree generation
│   ├── detector/              # Stage 2 & 3: Syntax and linting bug detection
│   ├── graph/                 # Stage 4 & 5: Dependency Graph & BFS Impact tracking
│   ├── scorer/                # Stage 6, 7 & 8: Feature Extraction & ML Scoring
│   └── explainer/             # Stage 9: Human-readable explanation generation
│
├── frontend/                  
│   └── app.py                 # (Legacy) Streamlit frontend application
│
├── examples/                  # Bundled .v (Verilog) code datasets to test out
├── index.html                 # Production HTML/JS frontend entry point
├── plotly.min.js              # Locally bundled Plotly for fully offline support
├── requirements.txt           # Python application dependencies
├── run.py                     # Local development launcher 
└── vercel.json                # Serverless deployment configuration
```

## 🧪 Testing the ML Capabilities

You can test the analyzer by utilizing the built-in examples. 
When the app launches, use the **"Load Example"** dropdown in the web UI sidebar to select a test dataset (e.g. `Massive Buggy Design (12 modules)`). Click **"Run Full Analysis"** to watch the analyzer:
1. Trace the signal dependencies.
2. Render an interactive Plotly propagation graph.
3. Quantify the blast radius of bugs (High, Medium, Low severity).

## ☁️ Deployment

The project is already configured for deployment on serverless platforms (e.g. Vercel) through the included `vercel.json` and the root `main.py` entry proxy. 

**For Vercel:**
Simply import the project on the Vercel dashboard and deploy. Vercel will automatically detect `fastapi` requirements, bind to the proxy `main.py`, and expose the API and UI flawlessly.

## 📄 License & Credits

Built as part of an Advanced Agentic Coding experiment demonstrating state-of-the-art bridging of electronic design automation, graphing neural systems, and modern web architectures.
