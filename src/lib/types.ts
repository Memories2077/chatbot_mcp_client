export type ChatRole = 'user' | 'model' | 'system' | 'tool-call' | 'tool-output';

export interface ChatMessage {
  id: string;
  role: ChatRole;
  content: string;
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
  model: string;
  temperature: number;
  maxTokens: number;
  mcpServers: McpServer[];
}
