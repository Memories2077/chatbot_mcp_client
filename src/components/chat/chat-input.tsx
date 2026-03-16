"use client";

import * as React from 'react';
import { useChatStore } from '@/lib/hooks/use-chat-store';
import { Button } from '@/components/ui/button';
import { Icons } from '@/components/icons';
import { Textarea } from '@/components/ui/textarea';
import { cn } from '@/lib/utils';

export function ChatInput() {
  const { sendMessage, isLoading, settings } = useChatStore((state) => ({
    sendMessage: state.sendMessage,
    isLoading: state.isLoading,
    settings: state.settings,
  }));

  const [input, setInput] = React.useState('');
  const [isComposing, setIsComposing] = React.useState(false);
  const inputRef = React.useRef<HTMLTextAreaElement>(null);

  // Auto-resize textarea
  React.useEffect(() => {
    if (inputRef.current) {
      inputRef.current.style.height = 'auto';
      inputRef.current.style.height = `${Math.min(inputRef.current.scrollHeight, 200)}px`;
    }
  }, [input]);

  const handleSubmit = (e?: React.FormEvent<HTMLFormElement> | React.KeyboardEvent) => {
    if (e) e.preventDefault();
    if (!input.trim() || isLoading || isComposing) return;
    sendMessage(input, settings);
    setInput('');
  };

  return (
    <div className="w-full shrink-0 border-t bg-background">
      <form
        onSubmit={(e) => handleSubmit(e)}
        className="mx-auto flex max-w-4xl w-full items-end gap-2 p-4"
      >
        <div className="relative flex-1">
          <Textarea
            ref={inputRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onCompositionStart={() => setIsComposing(true)}
            onCompositionEnd={() => setIsComposing(false)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                if (isComposing) return;
                e.preventDefault();
                handleSubmit();
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
  );
}
