"use client";

import * as React from 'react';
import { AnimatePresence, motion } from 'framer-motion';
import { useChatStore } from '@/lib/hooks/use-chat-store';
import { Button } from '@/components/ui/button';
import { ChatMessage } from '@/components/chat/chat-message';
import { ChatSettings } from '@/components/chat/chat-settings';
import { ChatInput } from '@/components/chat/chat-input';
import { Icons } from '@/components/icons';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '../ui/tooltip';

export function ChatLayout() {
  const {
    messages,
    isLoading,
    settings,
    setSettings,
    clearMessages,
  } = useChatStore((state) => ({
    messages: state.messages,
    isLoading: state.isLoading,
    settings: state.settings,
    setSettings: state.setSettings,
    clearMessages: state.clearMessages,
  }));

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
                {messages.map((message) => (
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
      
      <ChatInput />
    </div>
  );
}
