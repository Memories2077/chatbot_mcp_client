"use client";

import { useState } from "react";
import { useChatStore } from "@/lib/hooks/use-chat-store";

const contextChips = [
  { icon: "brush", label: "Style Guide" },
  { icon: "image", label: "Reference Images" },
  { icon: "code", label: "Export Specs" },
];

export function ChatInputBar() {
  const [text, setText] = useState("");
  const { sendMessage, isLoading } = useChatStore();

  const handleSend = () => {
    if (text.trim() && !isLoading) {
      sendMessage(text.trim());
      setText("");
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="absolute bottom-0 left-0 w-full p-6 bg-gradient-to-t from-background via-background/95 to-transparent shrink-0">
      <div className="max-w-4xl mx-auto relative group">
        <div className="flex items-center gap-4 bg-surface-container-highest/40 backdrop-blur-xl rounded-full px-6 py-4 border border-outline-variant/20 shadow-2xl focus-within:border-white/10 focus-within:shadow-[0_0_20px_rgba(255,255,255,0.05)] transition-all duration-300">
          <button className="text-on-surface-variant hover:text-secondary transition-colors p-2">
            <span className="material-symbols-outlined">attach_file</span>
          </button>
          <input
            className="flex-1 bg-transparent border-none focus:outline-none focus:ring-0 text-on-surface placeholder-on-surface-variant/50 text-lg"
            placeholder="Design the future with Ethereal..."
            type="text"
            value={text}
            onChange={(e) => setText(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={isLoading}
          />
          <div className="flex items-center gap-2">
            <button className="p-2 text-on-surface-variant hover:text-primary transition-colors">
              <span className="material-symbols-outlined">mic</span>
            </button>
            <button 
              onClick={handleSend}
              disabled={!text.trim() || isLoading}
              className="w-12 h-12 rounded-full bg-gradient-to-r from-primary to-primary-container text-on-primary-container flex items-center justify-center transition-all duration-300 hover:shadow-lg hover:shadow-primary/30 active:scale-90 disabled:opacity-50 disabled:grayscale disabled:cursor-not-allowed"
            >
              <span className="material-symbols-outlined">send</span>
            </button>
          </div>
        </div>

        {/* Context Chips */}
        <div className="flex gap-2 mt-4 ml-6 overflow-x-auto pb-2 no-scrollbar font-label">
          {contextChips.map((chip) => (
            <span
              key={chip.label}
              className="bg-surface-container-low px-3 py-1 rounded-full text-xs font-medium text-on-surface-variant flex items-center gap-1 cursor-pointer hover:bg-surface-container transition-colors whitespace-nowrap"
            >
              <span className="material-symbols-outlined text-[14px]">{chip.icon}</span>
              {chip.label}
            </span>
          ))}
        </div>
      </div>
    </div>
  );
}
