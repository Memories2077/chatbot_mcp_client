"use client";

import * as React from 'react';
import { useState, useEffect } from 'react';
import { cn } from '@/lib/utils';
import { fetchMcpServers, submitMcpServerFeedback, type McpServerApi } from '@/lib/mcp-server-api';
import { ThumbsUp, ThumbsDown, RefreshCw, AlertCircle } from 'lucide-react';
import { Button } from '@/components/ui/button';

interface McpServerFeedbackListProps {
  className?: string;
}

export function McpServerFeedbackList({ className }: McpServerFeedbackListProps) {
  const [servers, setServers] = useState<McpServerApi[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [feedbackSubmitting, setFeedbackSubmitting] = useState<Set<string>>(new Set());

  const loadServers = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await fetchMcpServers();
      setServers(data);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load MCP servers');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadServers();
  }, []);

  const handleFeedback = async (serverId: string, type: 'like' | 'dislike') => {
    // Optimistic update
    setServers(prev =>
      prev.map(server => {
        if (server.serverId !== serverId) return server;
        const currentLike = server.likeCount ?? 0;
        const currentDislike = server.dislikeCount ?? 0;
        return {
          ...server,
          likeCount: type === 'like' ? currentLike + 1 : currentLike,
          dislikeCount: type === 'dislike' ? currentDislike + 1 : currentDislike,
        };
      })
    );

    setFeedbackSubmitting(prev => new Set(prev).add(serverId));

    try {
      await submitMcpServerFeedback(serverId, type);
      // Success - keep optimistic update
    } catch (err) {
      // Revert on error
      setServers(prev =>
        prev.map(server => {
          if (server.serverId !== serverId) return server;
          const currentLike = server.likeCount ?? 0;
          const currentDislike = server.dislikeCount ?? 0;
          return {
            ...server,
            likeCount: type === 'like' ? currentLike - 1 : currentLike,
            dislikeCount: type === 'dislike' ? currentDislike - 1 : currentDislike,
          };
        })
      );
      setError(err instanceof Error ? err.message : 'Failed to submit feedback');
    } finally {
      setFeedbackSubmitting(prev => {
        const next = new Set(prev);
        next.delete(serverId);
        return next;
      });
    }
  };

  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleDateString(undefined, {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'running':
        return 'text-emerald-400';
      case 'created':
      case 'started':
        return 'text-blue-400';
      case 'building':
        return 'text-amber-400';
      case 'error':
      case 'deleted':
        return 'text-red-400';
      default:
        return 'text-on-surface-variant';
    }
  };

  if (loading) {
    return (
      <div className={cn("flex items-center justify-center py-8", className)}>
        <RefreshCw className="w-5 h-5 animate-spin text-primary mr-2" />
        <span className="text-sm text-on-surface-variant">Loading MCP servers...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className={cn("p-4 rounded-lg border border-red-500/20 bg-red-500/5", className)}>
        <div className="flex items-center gap-2 text-red-400 mb-2">
          <AlertCircle className="w-4 h-4" />
          <span className="text-sm font-medium">Error</span>
        </div>
        <p className="text-xs text-on-surface-variant mb-3">{error}</p>
        <Button size="sm" variant="outline" onClick={loadServers} className="text-xs">
          <RefreshCw className="w-3 h-3 mr-1" />
          Retry
        </Button>
      </div>
    );
  }

  if (servers.length === 0) {
    return (
      <div className={cn("text-center py-8 text-on-surface-variant", className)}>
        <p className="text-sm">No MCP servers generated yet.</p>
        <p className="text-xs opacity-70 mt-1">Servers will appear here after creation.</p>
      </div>
    );
  }

  return (
    <div className={cn("space-y-3", className)}>
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-on-surface font-headline">
          Generated MCP Servers ({servers.length})
        </h3>
        <Button
          size="sm"
          variant="ghost"
          onClick={loadServers}
          disabled={loading}
          className="h-7 px-2 text-xs"
        >
          <RefreshCw className={cn("w-3 h-3", loading && "animate-spin")} />
        </Button>
      </div>

      <div className="space-y-2">
        {servers.map(server => (
          <div
            key={server.serverId}
            className="group rounded-lg border border-outline-variant/10 bg-surface-container-low/20 p-3 hover:bg-surface-container-low/30 transition-colors"
          >
            <div className="flex items-start justify-between gap-3">
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-1">
                  <span className="text-xs font-mono font-bold text-primary/80 truncate">
                    {server.serverId}
                  </span>
                  <span className={cn("text-[10px] font-bold uppercase", getStatusColor(server.status))}>
                    {server.status}
                  </span>
                </div>

                <div className="text-[10px] text-on-surface-variant/70 mb-2">
                  Created: {formatDate(server.createdAt)}
                </div>

                {server.publicUrl && (
                  <div className="text-[10px] font-mono text-on-surface/60 truncate">
                    {server.publicUrl}
                  </div>
                )}
              </div>

              {/* Feedback buttons - always visible but subtle */}
              <div className="flex items-center gap-1 flex-shrink-0">
                <Button
                  size="sm"
                  variant="ghost"
                  onClick={() => handleFeedback(server.serverId, 'like')}
                  disabled={feedbackSubmitting.has(server.serverId)}
                  className={cn(
                    "h-8 px-2 text-xs gap-1.5",
                    "opacity-60 hover:opacity-100",
                    (server.likeCount ?? 0) > 0 && "text-emerald-500 opacity-100"
                  )}
                  title="Like this MCP server"
                >
                  <ThumbsUp className={cn("w-3.5 h-3.5", (server.likeCount ?? 0) > 0 && "fill-current")} />
                  <span className="font-mono">{server.likeCount ?? 0}</span>
                </Button>

                <Button
                  size="sm"
                  variant="ghost"
                  onClick={() => handleFeedback(server.serverId, 'dislike')}
                  disabled={feedbackSubmitting.has(server.serverId)}
                  className={cn(
                    "h-8 px-2 text-xs gap-1.5",
                    "opacity-60 hover:opacity-100",
                    (server.dislikeCount ?? 0) > 0 && "text-red-500 opacity-100"
                  )}
                  title="Dislike this MCP server"
                >
                  <ThumbsDown className={cn("w-3.5 h-3.5", (server.dislikeCount ?? 0) > 0 && "fill-current")} />
                  <span className="font-mono">{server.dislikeCount ?? 0}</span>
                </Button>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

McpServerFeedbackList.displayName = 'McpServerFeedbackList';
