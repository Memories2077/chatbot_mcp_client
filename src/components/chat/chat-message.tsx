"use client";

import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { cn } from '@/lib/utils';
import type { ChatMessage as ChatMessageType } from '@/lib/types';
import { Icons } from '@/components/icons';
import { Avatar, AvatarFallback } from '@/components/ui/avatar';
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible';
import { Button } from '@/components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

interface ChatMessageProps {
  message?: ChatMessageType;
  isLoading?: boolean;
}

export function ChatMessage({ message, isLoading }: ChatMessageProps) {
  const role = isLoading ? 'model' : message!.role;
  const content = isLoading ? '...' : message!.content;
  
  const icon =
    role === 'user' ? (
      <Icons.user className="h-6 w-6" />
    ) : (
      <Icons.bot className="h-6 w-6 text-primary" />
    );
  
  const avatarFallback = role === 'user' ? 'U' : 'AI';

  const renderToolCall = () => {
    if (!message || !message.toolCalls || message.toolCalls.length === 0) return null;

    return (
        <div className="mt-2 space-y-4">
            {message.toolCalls.map((toolCall, index) => (
                <Card key={index} className="bg-card/50 border-accent/20">
                    <CardHeader className="p-4">
                        <CardTitle className="flex items-center gap-2 text-base font-medium text-accent">
                            <Icons.tool className="h-5 w-5" />
                            <span>Using Tool: {toolCall.name}</span>
                        </CardTitle>
                    </CardHeader>
                    <Collapsible>
                        <CollapsibleContent>
                            <CardContent className="p-4 pt-0">
                                <pre className="p-3 rounded-md bg-background/50 text-xs text-foreground/80 overflow-x-auto">
                                    <code>{JSON.stringify(toolCall.args, null, 2)}</code>
                                </pre>
                            </CardContent>
                        </CollapsibleContent>
                        <div className="px-4 pb-4">
                            <CollapsibleTrigger asChild>
                                <Button variant="ghost" size="sm" className="text-accent hover:bg-accent/10 hover:text-accent">
                                    <Icons.chevronDown className="h-4 w-4 mr-2" />
                                    Show/Hide Arguments
                                </Button>
                            </CollapsibleTrigger>
                        </div>
                    </Collapsible>
                </Card>
            ))}
        </div>
    );
  };
  
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
                    const match = /language-(\w+)/.exec(className || '');
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
          {message?.role === 'tool-output' && renderToolCall()}
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
