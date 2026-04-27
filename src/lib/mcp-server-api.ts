/**
 * MCP Server API utilities
 * Handles communication with the mcp-gen service for server listing and feedback.
 */

const MCP_GEN_BASE_URL = process.env.NEXT_PUBLIC_MCP_GEN_URL || 'http://localhost:8080';

export interface McpServerApi {
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

export interface FeedbackResponse {
  success: boolean;
  serverId: string;
  likeCount: number;
  dislikeCount: number;
  totalFeedbacks: number;
}

/**
 * Fetch all MCP servers from mcp-gen
 */
export async function fetchMcpServers(): Promise<McpServerApi[]> {
  const response = await fetch(`${MCP_GEN_BASE_URL}/api/mcp/servers`, {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json',
    },
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ error: 'Failed to fetch MCP servers' }));
    throw new Error(error.error || `HTTP ${response.status}`);
  }

  const data = await response.json();
  return data.servers || [];
}

/**
 * Submit feedback for an MCP server
 */
export async function submitMcpServerFeedback(
  serverId: string,
  type: 'like' | 'dislike',
  userId?: string,
  comment?: string
): Promise<FeedbackResponse> {
  const response = await fetch(`${MCP_GEN_BASE_URL}/api/mcp/${serverId}/feedback`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      type,
      userId,
      comment,
    }),
  });

  if (!response.ok) {
    const error = await response.json().catch(() => ({ error: 'Failed to submit feedback' }));
    throw new Error(error.error || `HTTP ${response.status}`);
  }

  return response.json();
}
