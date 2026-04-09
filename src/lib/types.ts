export type ChatRole = 'user' | 'model' | 'system' | 'tool-call' | 'tool-output';

export interface ChatMessage {
  id: string;
  role: ChatRole;
  content: string;
  timestamp: string; // ISO format string
  toolCallId?: string;
  name?: string;
  toolCalls?: {
    name: string;
    args: any;
  }[];
}

export interface McpServer {
  url: string;
}

export interface ChatSettings {
  provider: 'gemini' | 'groq' | 'metaclaw';
  model: string;
  temperature: number;
  maxTokens: number;
  mcpServers: McpServer[];
}
