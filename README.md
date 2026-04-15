# 🚀 Ethereal Intelligence: Unified MCP Ecosystem

[![Next.js](https://img.shields.io/badge/Next.js-15-black?logo=next.js)](https://nextjs.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688?logo=fastapi)](https://fastapi.tiangolo.com/)
[![Gemini](https://img.shields.io/badge/Gemini-2.0--Flash-4285F4?logo=google-gemini)](https://aistudio.google.com/)
[![MetaClaw](https://img.shields.io/badge/MetaClaw-Enabled-blueviolet)](https://github.com/metaclaw)

![Ethereal Intelligence Preview](./img/demo.gif)

---

(./img/demo.gif)

## 🧠 Architecture: Brain + Arms

Our core philosophy separates reasoning from execution to ensure maximum reliability and precision:

- **Brain (MetaClaw Proxy)**: The reasoning engine. It classifies user intent, identifies the necessary tools, and extracts high-fidelity parameters from the conversation.
- **Arms (Gemini Flash)**: The execution layer. It receives structured signals from the Brain and performs the actual tool calls—from standard RAG to complex environment mutations.
- **Orchestrator (FastAPI Backend)**: A high-performance bridge that handles SSE (Server-Sent Events) streaming, session persistence, and proxies requests to LangGraph build services.

---

## ✨ Key Features

### 📡 Unified SSE Streaming

Experience real-time AI responses with zero-latency streaming. The backend handles complex tool-calling handoffs and proxies progress logs directly from build agents to your screen.

### 🏗️ Autonomous MCP Builder

Transform conversations into code. Directly integrated with our [LangChain Backend](https://github.com/your-repo/langchain-app), you can command the AI to build, configure, and initialize new MCP servers in real-time.

### 🔌 Federated MCP Interaction

Connect to multiple MCP servers simultaneously. The system intelligently switches contexts between local environment tools, cloud APIs, and custom-built servers.

### 💎 Premium Interface

A sleek, glassmorphism-inspired UI built with Next.js. Features include:

- **Persistent Chat History**: Never lose context with our integrated storage.
- **Status Indicators**: Real-time feedback for tool execution and background tasks.
- **Dynamic Layouts**: Responsive design that adapts to complex data visualizations and code blocks.

---

## 🛠️ Technical Stack

- **Frontend**: Next.js 15, React 19, TypeScript, Tailwind CSS, Shadcn UI.
- **Backend**: FastAPI (Python), LangChain, LangGraph SDK.
- **Services**: Dockerized MongoDB, Gemini API, MetaClaw Gateway.

---

## 🚀 Getting Started

### Prerequisites

- Docker & Docker Compose
- Gemini API Key ([Get it here](https://aistudio.google.com/app/apikey))
- MetaClaw Instance (Optional but recommended for "Brain" functionality)

### Configuration

Create a `.env` file in the root directory:

```bash
# 1. Core API
GEMINI_API_KEY="your_api_key_here"

# 2. MetaClaw (Brain) Configuration
METACLAW_ENABLED=true
METACLAW_BASE_URL="http://host.docker.internal:30000/v1"
METACLAW_API_KEY="your_metaclaw_key"

# 3. Port Configuration
NEXT_PUBLIC_BACKEND_PORT=8000
```

### Installation (Docker)

```bash
docker-compose up --build -d
```

The Frontend will be available at `http://localhost:9002` and the Backend at `http://localhost:8000`.

---

## 🛠️ Development

To run the backend locally:

```bash
cd backend
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt
python main.py
```

To run the frontend locally:

```bash
npm install
npm run dev
```

---

## 📄 License

MIT License. See [LICENSE](LICENSE) for details.
