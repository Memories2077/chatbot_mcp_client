"use client";

import * as React from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { useChatStore } from '@/lib/hooks/use-chat-store';
import { Button } from '@/components/ui/button';
import { ChatMessage } from '@/components/chat/chat-message';
import { ChatSettings } from '@/components/chat/chat-settings';
import { Icons } from '@/components/icons';
import { Textarea } from '@/components/ui/textarea';
import { ScrollArea } from '@/components/ui/scroll-area';
import { cn } from '@/lib/utils';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '../ui/tooltip';

export function ChatLayout() {
  const {
    messages,
    sendMessage,
    isLoading,
    settings,
    setSettings,
    clearMessages,
  } = useChatStore((state) => ({
    messages: state.messages,
    sendMessage: state.sendMessage,
    isLoading: state.isLoading,
    settings: state.settings,
    setSettings: state.setSettings,
    clearMessages: state.clearMessages,
  }));

  const [input, setInput] = React.useState('');
  const inputRef = React.useRef<HTMLTextAreaElement>(null);
  const scrollAreaRef = React.useRef<React.ElementRef<typeof ScrollArea>>(null);

  React.useEffect(() => {
    // Scroll to the bottom when a new message is added
    if (scrollAreaRef.current) {
        const viewport = scrollAreaRef.current.querySelector('div[data-radix-scroll-area-viewport]');
        if (viewport) {
            viewport.scrollTop = viewport.scrollHeight;
        }
    }
  }, [messages]);
  
  const handleSubmit = (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    if (!input.trim() || isLoading) return;
    sendMessage(input);
    setInput('');
  };

  return (
    <div className="relative flex h-screen w-full flex-col">
      <header className="flex h-16 w-full shrink-0 items-center justify-between border-b bg-card/20 px-4 md:px-6">
        <div className="flex items-center gap-3">
          <Icons.bot className="h-8 w-8 text-primary" />
          <h1 className="text-lg font-semibold tracking-tight font-headline">Gemini InsightLink</h1>
        </div>
        <div className="flex items-center gap-2">
          <TooltipProvider>
            <Tooltip>
              <TooltipTrigger asChild>
                <Button variant="ghost" size="icon" onClick={clearMessages} disabled={messages.length === 0}>
                  <Icons.trash className="h-4 w-4" />
                  <span className="sr-only">Clear Chat</span>
                </Button>
              </TooltipTrigger>
              <TooltipContent>
                <p>Clear Chat</p>
              </TooltipContent>
            </Tooltip>
          </TooltipProvider>
          <ChatSettings settings={settings} setSettings={setSettings} />
        </div>
      </header>
      
      <ScrollArea className="flex-1" ref={scrollAreaRef}>
        <AnimatePresence>
            <div className="mx-auto max-w-4xl w-full p-4 md:p-6">
                {messages.map((message, index) => (
                    <motion.div
                        key={message.id}
                        layout
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        exit={{ opacity: 0, y: -20 }}
                        transition={{ duration: 0.3 }}
                        className="mb-4"
                    >
                        <ChatMessage message={message} />
                    </motion.div>
                ))}
                {isLoading && (
                    <motion.div
                        layout
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        exit={{ opacity: 0, y: -20 }}
                        transition={{ duration: 0.3 }}
                        className="mb-4"
                    >
                        <ChatMessage isLoading />
                    </motion.div>
                )}
            </div>
        </AnimatePresence>
      </ScrollArea>
      
      <div className="w-full shrink-0 border-t bg-background">
        <form
          onSubmit={handleSubmit}
          className="mx-auto flex max-w-4xl w-full items-end gap-2 p-4"
        >
          <div className="relative flex-1">
            <Textarea
              ref={inputRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault();
                  handleSubmit(e as any);
                }
              }}
              placeholder="Type your message..."
              className="min-h-[48px] resize-none pr-12"
              rows={1}
              style={{maxHeight: '200px'}}
            />
            <Button
              type="submit"
              size="icon"
              className={cn("absolute right-3 top-1/2 -translate-y-1/2", {
                "bg-primary/50": isLoading
              })}
              disabled={isLoading || !input.trim()}
              aria-label="Send message"
            >
              <Icons.send className="h-4 w-4" />
            </Button>
          </div>
        </form>
      </div>
    </div>
  );
}
