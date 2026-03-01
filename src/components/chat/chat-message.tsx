"use client";

import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { cn } from '@/lib/utils';
import type { ChatMessage as ChatMessageType } from '@/lib/types';
import { Icons } from '@/components/icons';
import { Avatar, AvatarFallback } from '@/components/ui/avatar';

interface ChatMessageProps {
  message?: ChatMessageType;
  isLoading?: boolean;
}

export function ChatMessage({ message, isLoading }: ChatMessageProps) {
  const role = isLoading ? 'model' : message!.role;
  const content = isLoading ? '...' : message!.content;
  
  const avatarFallback = role === 'user' ? 'U' : 'AI';

  return (
    <div
      className={cn(
        'group flex items-start gap-4',
        role === 'user' && 'justify-end'
      )}
    >
      {role !== 'user' && (
        <Avatar className="h-8 w-8 shrink-0 border">
          <AvatarFallback>{avatarFallback}</AvatarFallback>
        </Avatar>
      )}

      <div
        className={cn(
          'flex max-w-[80%] flex-col',
          role === 'user' ? 'items-end' : 'items-start'
        )}
      >
        <div
          className={cn(
            'rounded-lg px-4 py-3 text-sm shadow-sm',
            role === 'user'
              ? 'rounded-br-none bg-primary text-primary-foreground'
              : 'rounded-bl-none bg-card'
          )}
        >
          {isLoading ? (
            <div className="flex items-center gap-2">
                <Icons.spinner className="h-4 w-4 animate-spin" />
                <span>Thinking...</span>
            </div>
          ) : (
            <ReactMarkdown
              remarkPlugins={[remarkGfm]}
              className="prose prose-sm dark:prose-invert prose-p:leading-relaxed prose-pre:p-0"
              components={{
                pre({node, ...props}) {
                    return <pre {...props} className="bg-background/50 p-3 rounded-md" />;
                },
                code({node, inline, className, children, ...props}) {
                    return !inline ? (
                        <code className={cn(className, "text-foreground/80")} {...props}>
                            {children}
                        </code>
                    ) : (
                        <code className={cn(className, "font-mono bg-muted text-accent px-1 py-0.5 rounded-sm")} {...props}>
                            {children}
                        </code>
                    );
                }
              }}
            >
              {content}
            </ReactMarkdown>
          )}
        </div>
      </div>

      {role === 'user' && (
        <Avatar className="h-8 w-8 shrink-0 border">
          <AvatarFallback>{avatarFallback}</AvatarFallback>
        </Avatar>
      )}
    </div>
  );
}
