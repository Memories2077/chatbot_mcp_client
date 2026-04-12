"use client";

import { useState, useRef, useEffect } from "react";
import { useChatStore } from "@/lib/hooks/use-chat-store";
import { cn } from "@/lib/utils";

const contextChips = [
  { icon: "brush", label: "Style Guide" },
  { icon: "image", label: "Reference Images" },
  { icon: "terminal", label: "Create MCP Server", isToggle: true },
];

export function ChatInputBar() {
  const [text, setText] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const { sendMessage, isLoading, isMcpMode, toggleMcpMode } = useChatStore();
  const prevLoadingRef = useRef(isLoading);

  const handleSend = () => {
    if (text.trim() && !isLoading) {
      sendMessage(text.trim());
      setText("");
      if (textareaRef.current) {
        textareaRef.current.style.height = 'auto';
      }
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey && !e.nativeEvent.isComposing) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setText(e.target.value);
    const textarea = e.target;
    textarea.style.height = 'auto';
    const newHeight = Math.min(textarea.scrollHeight, 200);
    textarea.style.height = `${newHeight}px`;
  };

  useEffect(() => {
    if (prevLoadingRef.current && !isLoading) {
      textareaRef.current?.focus();
    }
    prevLoadingRef.current = isLoading;
  }, [isLoading]);

  useEffect(() => {
    textareaRef.current?.focus();
  }, []);

  return (
    <div className="absolute bottom-0 left-0 w-full p-6 bg-gradient-to-t from-background via-background/95 to-transparent shrink-0">
      <div className="max-w-4xl mx-auto relative group">
        <div className="flex items-end gap-2 bg-surface-container-highest/40 backdrop-blur-xl rounded-[2rem] px-4 py-3 border border-outline-variant/20 shadow-2xl focus-within:border-white/10 focus-within:shadow-[0_0_20px_rgba(255,255,255,0.05)] transition-all duration-300">
          
          {/* Attachment Button - Wrapped in fixed height div for alignment */}
          <div className="flex items-center justify-center h-12 w-12 shrink-0">
            <button className="text-on-surface-variant hover:text-secondary transition-colors p-2">
              <span className="material-symbols-outlined">attach_file</span>
            </button>
          </div>
          
          <textarea
            ref={textareaRef}
            rows={1}
            className="flex-1 bg-transparent border-none focus:outline-none focus:ring-0 text-on-surface placeholder-on-surface-variant/50 text-lg py-3 resize-none no-scrollbar max-h-[200px] leading-relaxed"
            placeholder={isMcpMode ? "Insert your API Description..." : "Design the future with Ethereal..."}
            value={text}
            onChange={handleChange}
            onKeyDown={handleKeyDown}
            disabled={isLoading}
          />

          {/* Action Buttons - Mic and Send */}
          <div className="flex items-center gap-1 h-12 shrink-0 pr-1">
            <button className="p-2 text-on-surface-variant hover:text-primary transition-colors">
              <span className="material-symbols-outlined">mic</span>
            </button>
            <button 
              onClick={handleSend}
              disabled={!text.trim() || isLoading}
              className="w-10 h-10 rounded-full bg-gradient-to-r from-primary to-primary-container text-on-primary-container flex items-center justify-center transition-all duration-300 hover:shadow-lg hover:shadow-primary/30 active:scale-90 disabled:opacity-50 disabled:grayscale disabled:cursor-not-allowed"
            >
              <span className="material-symbols-outlined text-[20px]">arrow_upward</span>
            </button>
          </div>
        </div>

        {/* Context Chips */}
        <div className="flex gap-2 mt-4 ml-6 overflow-x-auto pb-2 no-scrollbar font-label">
          {contextChips.map((chip) => {
            const isSelected = chip.isToggle && isMcpMode;
            return (
              <span
                key={chip.label}
                onClick={() => chip.isToggle && toggleMcpMode()}
                className={cn(
                  "px-3 py-1 rounded-full text-xs font-medium flex items-center gap-1 cursor-pointer transition-all duration-300 whitespace-nowrap border border-transparent",
                  isSelected
                    ? "bg-primary/20 text-primary border-primary/30 shadow-[0_0_15px_rgba(var(--primary-rgb),0.2)]"
                    : "bg-surface-container-low text-on-surface-variant hover:bg-surface-container"
                )}
              >
                <span className="material-symbols-outlined text-[14px]">{chip.icon}</span>
                {chip.label}
              </span>
            );
          })}
        </div>
      </div>
    </div>
  );
}
