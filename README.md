# Ethereal Intelligence

> A next-generation agentic chatbot platform with modern interface and unlimited extensibility through Model Context Protocol (MCP).

![Ethereal Intelligence Preview](img/demo.gif)

## Overview

Ethereal Intelligence is an advanced agentic chatbot platform that combines cutting-edge AI models with a sophisticated user interface. Built on **Model Context Protocol (MCP)**, it enables seamless integration with external tools and services, empowering the AI assistant to execute complex tasks in real-time through intelligent tool orchestration.

Powered by **Gemini 2.5 Flash** and other state-of-the-art language models, Ethereal Intelligence delivers fast, context-aware responses with the ability to dynamically discover and utilize external MCP servers for enhanced functionality.

## Key Features

### 🎨 Modern Ethereal Interface

- **Refined Design Language**: Deep Purple (#8340FF) and Dark Gray (#201C21) color scheme optimized for professional user experience
- **Smooth Animations**: Powered by Framer Motion for fluid transitions and interactions
- **Responsive Layout**: Built with accessibility and usability in mind

### 🤖 Agentic Tool Execution

- **Intelligent Agent Loop**: Leverages LangChain to create a sophisticated agentic workflow where the chatbot autonomously reasons about tool usage
- **Real-Time Tool Discovery**: Dynamically discovers and integrates with external MCP servers
- **Contextual Tool Selection**: AI-driven decision making for optimal tool utilization based on conversation context

### 🔗 Dynamic MCP Integration

- **Seamless Server Registration**: Register MCP Server endpoints directly through the settings interface
- **Automatic Metadata Detection**: Instantly recognizes available tools and connection status
- **Extensible Architecture**: Connect to file management systems, databases, external APIs, and custom tool servers

### 💬 Smart Conversation Management

- **Persistent Storage**: Automatic conversation history preservation via localStorage
- **Auto-Archive System**: Intelligent session management that archives inactive conversations after 1 hour of inactivity
- **Clean Workspace**: Maintains an organized and clutter-free conversation environment

### 🔄 Multi-Provider Support

- **Flexible Model Switching**: Seamlessly switch between Google Gemini and Groq (Llama 3, Mixtral) providers
- **Optimized Performance**: Choose the optimal model for your use case based on cost and performance requirements
- **Future-Proof Design**: Extensible architecture ready for additional model providers

## Technology Stack

### Frontend

| Component        | Technology                          |
| ---------------- | ----------------------------------- |
| Framework        | Next.js 15 (App Router), TypeScript |
| State Management | Zustand with Persist middleware     |
| Styling          | Tailwind CSS, Radix UI              |
| Icons            | Lucide Icons                        |
| Animations       | Framer Motion                       |

### Backend

| Component        | Technology                       |
| ---------------- | -------------------------------- |
| Framework        | FastAPI (Python 3.12+)           |
| AI Orchestration | LangChain, LangGraph             |
| MCP Client       | MCP SDK (HTTP/SSE communication) |
| Supported Models | Gemini 2.5 Flash, Groq API       |

## Quick Start

### Prerequisites

- Node.js 18+ and npm
- Python 3.12+
- API keys for Gemini and/or Groq (optional)

### 1. Environment Configuration

Create a `.env` file in the project root directory:

```bash
cp .env.example .env
```

Configure your environment variables:

```env
GEMINI_API_KEY="your_gemini_api_key_here"
GROQ_API_KEY="your_groq_api_key_here"  # Optional
NEXT_PUBLIC_BACKEND_PORT=8000
```

### 2. Backend Setup

Navigate to the backend directory and set up the Python environment:

```bash
cd backend
python -m venv venv

# Activate virtual environment
# Windows:
venv\Scripts\activate
# Unix/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Start the backend server
python main.py
```

The backend will be available at `http://localhost:8000`

### 3. Frontend Setup

Install dependencies and start the development server:

```bash
npm install
npm run dev
```

Access the application at: **`http://localhost:9002`**

### 4. Docker Deployment (Recommended)

For production deployment, use Docker Compose:

```bash
docker compose up --build -d
```

This will build and start both frontend and backend containers with proper networking configuration.

## MCP Server Integration

Extend Ethereal Intelligence's capabilities by connecting external MCP Servers:

### Connecting a New MCP Server

1. Navigate to **Settings** in the application
2. Enter your MCP Server URL (e.g., `http://localhost:5000/mcp`)
3. The system will automatically discover available tools and display connection status

### Example Use Cases

- **File Management**: Connect to file system servers for reading/writing operations
- **Database Queries**: Integrate database servers for real-time data retrieval
- **System Control**: Connect to servers that control external systems or services
- **Custom APIs**: Integrate any REST API or custom tool server via MCP protocol

### MCP Server Requirements

- Must implement the Model Context Protocol specification
- Accessible via HTTP or Server-Sent Events (SSE)
- Properly configured CORS for browser-based connections

## Development

### Project Structure

```
chatbot_mcp_client/
├── backend/          # FastAPI backend with LangChain integration
├── src/              # Next.js frontend application
│   ├── app/          # Next.js App Router pages
│   ├── components/   # Reusable UI components
│   ├── store/        # Zustand state management
│   └── lib/          # Utility functions and configurations
├── .env.example      # Environment variable template
└── docker-compose.yml # Docker orchestration
```

### Available Scripts

- `npm run dev` - Start frontend development server
- `npm run build` - Build frontend for production
- `npm run start` - Start frontend production server
- `npm run lint` - Run ESLint checks

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request. For major changes, please open an issue first to discuss what you would like to change.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

For issues, questions, or suggestions:

- Open an issue on GitHub
- Check the existing documentation
- Review the discussion forum

---

<p align="center">
  <strong>Ethereal Intelligence</strong> — <em>Fluid. Intelligent. Boundless.</em>
</p>
