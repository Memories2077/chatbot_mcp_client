/**
 * MCP Server API utilities
 * Handles communication with the mcp-gen service for server listing and feedback.
 */

import { BACKEND_API } from "@/lib/config";

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
    type: "like" | "dislike";
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
 * Fetch all MCP servers through FastAPI's mcp-gen proxy.
 */
export async function fetchMcpServers(): Promise<McpServerApi[]> {
  const response = await fetch(BACKEND_API.mcpServers(), {
    method: "GET",
    headers: {
      "Content-Type": "application/json",
    },
  });

  if (!response.ok) {
    const error = await response
      .json()
      .catch(() => ({ error: "Failed to fetch MCP servers" }));
    throw new Error(error.error || `HTTP ${response.status}`);
  }

  const data = await response.json();
  return data.servers || [];
}

/**
 * Submit feedback for an MCP server through FastAPI's mcp-gen proxy.
 */
export async function submitMcpServerFeedback(
  serverId: string,
  type: "like" | "dislike",
  userId?: string,
  comment?: string,
): Promise<FeedbackResponse> {
  const response = await fetch(BACKEND_API.mcpFeedback(serverId), {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      type,
      userId,
      comment,
    }),
  });

  if (!response.ok) {
    const error = await response
      .json()
      .catch(() => ({ error: "Failed to submit feedback" }));
    throw new Error(error.error || `HTTP ${response.status}`);
  }

  return response.json();
}
