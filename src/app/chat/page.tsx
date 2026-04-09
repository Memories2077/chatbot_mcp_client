"use client";

import { useEffect, useRef } from "react";
import { useChatStore } from "@/lib/hooks/use-chat-store";
import { ChatMessage } from "@/components/chat/chat-message";
import { ChatInputBar } from "@/components/chat/ChatInputBar";
import { RightUtilityPanel } from "@/components/layout/RightUtilityPanel";

export default function ChatPage() {
  const { messages, isLoading } = useChatStore();
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isLoading]);

  return (
    <div className="flex flex-1 h-full overflow-hidden">
      <div className="flex-1 flex flex-col relative overflow-hidden h-full">
        {/* Chat Area */}
        <div className="flex-1 overflow-y-auto px-6 py-8 space-y-8 max-w-4xl mx-auto w-full scroll-smooth pb-40">
          {messages.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-full opacity-20 select-none">
              <span className="material-symbols-outlined text-6xl mb-4">chat_bubble</span>
              <p className="text-xl font-headline font-bold">Start a New Conversation</p>
            </div>
          ) : (
            messages.map((message) => (
              <ChatMessage key={message.id} message={message} />
            ))
          )}
          {isLoading && <ChatMessage isLoading={true} />}
          <div ref={messagesEndRef} />
        </div>

        {/* Floating Input Area */}
        <ChatInputBar />
      </div>

      {/* Right Utility Panel */}
      <RightUtilityPanel />
    </div>
  );
}
