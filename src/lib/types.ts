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

// Active MCP server connection (for chat settings)
export interface ActiveMcpServer {
  url: string;
  name?: string;
}

// Full MCP server data from mcp-gen API (includes feedback)
export interface McpServer {
  serverId: string;
  status: string;
  publicUrl: string;
  createdAt: string;
  updatedAt?: string;
  dockerImage?: string;
  hostPort?: number;
  containerPort?: number;
  containerId?: string;
  buildLogs?: string[];
  inputContent?: string;
  action?: string;
  ragContext?: string;
  // Feedback fields
  likeCount: number;
  dislikeCount: number;
  feedbacks: Array<{
    feedbackId: string;
    type: 'like' | 'dislike';
    userId?: string;
    comment?: string;
    timestamp: string;
  }>;
}

export interface ChatSettings {
  provider: 'gemini' | 'groq';
  model: string;
  temperature: number;
  maxTokens: number;
  mcpServers: ActiveMcpServer[];
}

export interface ChatHistoryItem {
  id: string;
  title: string;
  messages: ChatMessage[];
  timestamp: string;
}
