"use client";

import { useChatStore } from "@/lib/hooks/use-chat-store";
import { useRouter } from "next/navigation";
import { cn } from "@/lib/utils";

const bgGradients = [
  "from-primary/20 via-transparent to-transparent",
  "from-secondary/20 via-transparent to-transparent",
  "from-tertiary/20 via-transparent to-transparent",
  "from-error/10 via-transparent to-transparent",
];

export default function HistoryPage() {
  const { history, loadHistory, deleteHistory } = useChatStore();
  const router = useRouter();

  const handleLoad = (id: string) => {
    loadHistory(id);
    router.push("/chat");
  };

  return (
    <main className="flex-1 overflow-y-auto px-8 pb-12 pt-8 scroll-smooth">
      <div className="max-w-5xl mx-auto">
        <div className="flex items-center justify-between mb-12">
          <div>
            <h1 className="display-lg font-headline text-on-surface mb-2 tracking-tight">Memory Vault</h1>
            <p className="text-on-surface-variant font-body opacity-70">Revisit and resume your past neural interactions.</p>
          </div>
          <div className="bg-surface-container-low/60 backdrop-blur-xl px-6 py-3 rounded-full border border-outline-variant/10 flex items-center gap-3 shadow-lg">
            <span className="text-xs font-bold font-label uppercase tracking-widest text-primary">{history.length}</span>
            <span className="text-[10px] font-bold font-label uppercase tracking-widest text-on-surface-variant opacity-50">Saved Sessions</span>
          </div>
        </div>

        {history.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-40 bg-surface-container/10 rounded-[3.5rem] border border-dashed border-outline-variant/20 backdrop-blur-sm">
            <span className="material-symbols-outlined text-6xl opacity-10 mb-4">history_toggle_off</span>
            <p className="text-on-surface-variant opacity-40 font-headline font-bold text-xl">Empty Vault</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {history.map((item, index) => {
              const gradient = bgGradients[index % bgGradients.length];
              return (
                <div 
                  key={item.id}
                  className="group relative bg-surface-container/30 backdrop-blur-2xl p-8 rounded-[2.5rem] border border-outline-variant/10 hover:bg-surface-container/50 transition-all duration-500 cursor-pointer overflow-hidden shadow-xl hover:shadow-primary/5"
                  onClick={() => handleLoad(item.id)}
                >
                  {/* Blurred Background Glow */}
                  <div className={cn(
                    "absolute -top-24 -left-24 w-64 h-64 bg-gradient-to-br blur-[80px] opacity-20 group-hover:opacity-40 transition-opacity duration-700",
                    gradient
                  )}></div>
                  
                  <div className="relative z-10">
                    <div className="flex justify-between items-start mb-6">
                      <div className="w-12 h-12 rounded-2xl bg-surface-container-highest/50 flex items-center justify-center text-primary border border-outline-variant/10 shadow-inner group-hover:scale-110 transition-transform duration-500">
                        <span className="material-symbols-outlined text-2xl">chat_bubble</span>
                      </div>
                      <button 
                        onClick={(e) => {
                          e.stopPropagation();
                          deleteHistory(item.id);
                        }}
                        className="p-2 opacity-0 group-hover:opacity-100 hover:text-error hover:bg-error/10 rounded-full transition-all duration-300"
                      >
                        <span className="material-symbols-outlined text-2xl">delete</span>
                      </button>
                    </div>

                    <h3 className="text-xl font-bold text-on-surface mb-2 truncate group-hover:text-primary transition-colors duration-300">
                      {item.title}
                    </h3>
                    
                    <div className="flex items-center gap-4 text-[11px] font-medium text-on-surface-variant opacity-50 group-hover:opacity-80 transition-opacity">
                      <span className="flex items-center gap-1.5">
                        <span className="material-symbols-outlined text-[16px]">calendar_today</span>
                        {new Date(item.timestamp).toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' })}
                      </span>
                      <span className="w-1 h-1 rounded-full bg-outline-variant/30"></span>
                      <span className="flex items-center gap-1.5">
                        <span className="material-symbols-outlined text-[16px]">description</span>
                        {item.messages.length} neural turns
                      </span>
                    </div>

                    <div className="mt-10 flex justify-between items-center">
                      <div className="flex -space-x-2">
                        {[1, 2].map(i => (
                          <div key={i} className="w-6 h-6 rounded-full border-2 border-surface bg-surface-container-highest flex items-center justify-center">
                             <span className="text-[8px] font-bold opacity-40">{i === 1 ? 'AI' : 'U'}</span>
                          </div>
                        ))}
                      </div>
                      <span className="text-[10px] font-bold uppercase tracking-[0.2em] text-primary opacity-0 group-hover:opacity-100 group-hover:translate-x-0 translate-x-4 transition-all duration-500 flex items-center gap-2">
                        Resume Session
                        <span className="material-symbols-outlined text-sm">arrow_forward</span>
                      </span>
                    </div>
                  </div>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </main>
  );
}
