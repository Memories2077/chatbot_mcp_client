# **App Name**: Gemini InsightLink

## Core Features:

- Interactive Chat Interface: A modern, clean, and intuitive UI for sending messages to the LLM and displaying its responses, designed for seamless conversation flow.
- Dynamic Gemini Model Selection: Users can easily select and switch between various available Gemini models (e.g., 'gemini-pro', 'gemini-1.5-flash', etc.) from a dropdown or similar control.
- Configurable API Key Management: Provide a secure input field for the user to provide their GEMINI_API_KEY, allowing them to save or clear it as needed directly within the UI.
- Persistent Conversation Memory: Implement a mechanism to store and retrieve chat history for ongoing conversations, ensuring the LLM maintains context across turns.
- MCP Server Tool Integration: Allow users to register custom 'MCP Servers' (tool endpoints) by specifying their URLs, which the LLM agent can dynamically call as part of its agentic loop.
- Agentic Tool Execution Display: Visually represent when the LLM is using its tools (MCP Servers) and display their outputs within the chat thread to provide transparency for the agentic loop tool calls.
- Basic Model Configuration: Provide controls for essential LLM parameters like temperature or maximum output tokens, ensuring basic customization without unnecessary complexity.

## Style Guidelines:

- A sophisticated dark theme to convey intelligence and modernity. The primary color will be a rich, deep purple-indigo (#8340FF), used for interactive elements and key highlights.
- The background will be a very dark, subtly tinted gray (#201C21), providing a clean canvas that enhances readability in the dark theme.
- An accent color of vibrant sky blue (#7CA9FF) will be used for subtle contrasts, secondary actions, and visual cues to add dynamism.
- The 'Inter' sans-serif font will be used throughout for both headlines and body text, providing a modern, clean, and highly readable experience suitable for technical and conversational content.
- Utilize a set of minimalist, line-art icons that complement the clean aesthetic and improve user navigation without distracting from the content.
- A spacious and responsive layout that ensures comfortable reading and interaction across various screen sizes, focusing on a clear, organized chat history and intuitive input area.
- Subtle and smooth transitions for UI elements like model switching or message sending, providing elegant feedback without feeling sluggish or distracting.