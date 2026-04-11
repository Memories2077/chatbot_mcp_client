"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { useChatStore } from "@/lib/hooks/use-chat-store";

export default function Home() {
  const [prompt, setPrompt] = useState("");
  const router = useRouter();
  const { sendMessage, clearMessages } = useChatStore();

  const handleStartChat = () => {
    if (prompt.trim()) {
      // Always start a new chat from landing page by clearing previous session
      clearMessages(); 
      sendMessage(prompt.trim());
      router.push("/chat");
    } else {
      router.push("/chat");
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.nativeEvent.isComposing) {
      e.preventDefault();
      handleStartChat();
    }
  };

  return (
    <main className="flex-1 overflow-y-auto px-8 pb-12 pt-4 scroll-smooth">
      <div className="flex flex-col items-center justify-center min-h-[80vh] text-center z-10 py-12">
        <div className="mb-6 inline-flex items-center gap-2 px-4 py-2 rounded-full bg-surface-container-low/50 backdrop-blur-md border border-outline-variant/10">
          <span className="flex h-2 w-2 rounded-full bg-secondary"></span>
          <span className="text-xs font-bold tracking-widest uppercase text-on-surface-variant font-label">
            System Online
          </span>
        </div>
        
        <h1 className="display-lg font-headline text-on-surface mb-6 max-w-4xl">
          Experience the{" "}
          <span className="bg-gradient-to-r from-primary to-secondary bg-clip-text text-transparent">
            Future of Intelligence
          </span>
        </h1>
        
        <p className="body-lg text-on-surface-variant max-w-2xl mb-12 leading-relaxed font-body">
          Engage with an AI designed to amplify
          your creativity, streamline your workflow, and turn thoughts into reality.
        </p>
        
        <div className="flex flex-col sm:flex-row gap-4 mb-20">
          <button 
            onClick={handleStartChat}
            className="px-10 py-5 bg-gradient-to-r from-primary to-primary-container text-on-primary-container rounded-full font-bold text-lg shadow-[0_10px_30px_rgba(178,153,255,0.3)] hover:scale-105 active:scale-95 transition-all flex items-center justify-center"
          >
            Start Chatting Now
          </button>
          <button className="px-10 py-5 bg-surface-container/60 backdrop-blur-xl border border-outline-variant/20 text-on-surface rounded-full font-bold text-lg hover:bg-surface-bright transition-all">
            View Tutorials
          </button>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 w-full max-w-6xl px-4">
          {/* Feature 1 */}
          <div className="bg-surface-container/40 p-8 rounded-xl border border-outline-variant/10 text-left hover:bg-surface-container/60 transition-all group backdrop-blur-md">
            <div className="w-12 h-12 rounded-2xl bg-primary/10 flex items-center justify-center text-primary mb-6 group-hover:scale-110 transition-transform">
              <span className="material-symbols-outlined">psychology</span>
            </div>
            <h3 className="headline-sm font-headline text-on-surface mb-2">
              Neural Context
            </h3>
            <p className="text-sm text-on-surface-variant leading-relaxed">
              Advanced long-term memory that evolves with every conversation you have.
            </p>
          </div>

          {/* Feature 2 */}
          <div className="bg-surface-container/40 p-8 rounded-xl border border-outline-variant/10 text-left hover:bg-surface-container/60 transition-all group backdrop-blur-md">
            <div className="w-12 h-12 rounded-2xl bg-secondary/10 flex items-center justify-center text-secondary mb-6 group-hover:scale-110 transition-transform">
              <span className="material-symbols-outlined">palette</span>
            </div>
            <h3 className="headline-sm font-headline text-on-surface mb-2">
              Living Design
            </h3>
            <p className="text-sm text-on-surface-variant leading-relaxed">
              A responsive interface that adapts its mood to your creative flow.
            </p>
          </div>

          {/* Feature 3 */}
          <div className="bg-surface-container/40 p-8 rounded-xl border border-outline-variant/10 text-left hover:bg-surface-container/60 transition-all group backdrop-blur-md">
            <div className="w-12 h-12 rounded-2xl bg-tertiary/10 flex items-center justify-center text-tertiary mb-6 group-hover:scale-110 transition-transform">
              <span className="material-symbols-outlined">bolt</span>
            </div>
            <h3 className="headline-sm font-headline text-on-surface mb-2">
              Zero Latency
            </h3>
            <p className="text-sm text-on-surface-variant leading-relaxed">
              Instant responses powered by our proprietary ethereal core infrastructure.
            </p>
          </div>
        </div>

        {/* Hero-specific Floating Command */}
        <div className="mt-20 w-full max-w-3xl bg-surface-container-highest/40 backdrop-blur-xl p-2 rounded-full border border-outline-variant/20 flex items-center gap-4 shadow-2xl focus-within:border-white/20 transition-all duration-300">
          <div className="w-10 h-10 rounded-full bg-surface-container-low flex items-center justify-center text-on-surface-variant ml-2">
            <span className="material-symbols-outlined">attachment</span>
          </div>
          <input
            className="bg-transparent border-none focus:outline-none focus:ring-0 flex-1 text-on-surface placeholder:text-on-surface-variant/50"
            placeholder="Type your first command here..."
            type="text"
            value={prompt}
            onChange={(e) => setPrompt(e.target.value)}
            onKeyDown={handleKeyDown}
          />
          <button 
            onClick={handleStartChat}
            className="w-10 h-10 rounded-full bg-primary text-on-primary-container flex items-center justify-center mr-2 hover:scale-110 active:scale-90 transition-all"
          >
            <span className="material-symbols-outlined">arrow_upward</span>
          </button>
        </div>
      </div>
    </main>
  );
}
