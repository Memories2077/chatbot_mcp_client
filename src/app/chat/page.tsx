"use client";

import { useEffect, useRef } from "react";
import { useChatStore } from "@/lib/hooks/use-chat-store";
import { ChatMessage } from "@/components/chat/chat-message";
import { ChatInputBar } from "@/components/chat/ChatInputBar";
import { RightUtilityPanel } from "@/components/layout/RightUtilityPanel";

export default function ChatPage() {
  const { messages, isLoading, persistCurrentChat } = useChatStore();
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // Auto-save when leaving the page
  useEffect(() => {
    return () => {
      persistCurrentChat();
    };
  }, [persistCurrentChat]);

  return (
    <div className="flex h-full w-full overflow-hidden relative">
      <div className="flex-1 flex flex-col h-full relative overflow-hidden">
        {/* Messages Area */}
        <div className="flex-1 overflow-y-auto px-4 md:px-8 pt-20 pb-40 no-scrollbar">
          <div className="max-w-4xl mx-auto space-y-2">
            {messages.map((message) => (
              <ChatMessage key={message.id} message={message} />
            ))}
            {isLoading && <ChatMessage isLoading={true} />}
            <div ref={messagesEndRef} />
          </div>
        </div>

        {/* Floating Input Area */}
        <ChatInputBar />
      </div>

      {/* Right Utility Panel */}
      <RightUtilityPanel />
    </div>
  );
}
