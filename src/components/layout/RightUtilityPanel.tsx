"use client";

import { cn } from "@/lib/utils";
import { useChatStore } from "@/lib/hooks/use-chat-store";

export function RightUtilityPanel() {
  const { isRightPanelOpen, toggleRightPanel } = useChatStore();

  return (
    <aside 
      className={cn(
        "hidden lg:flex flex-col h-full gap-6 bg-surface-container-low/60 backdrop-blur-[32px] rounded-l-[3rem] shadow-[0_0_50px_rgba(0,0,0,0.3)] z-50 transition-all duration-500 ease-in-out overflow-hidden absolute right-0 top-0",
        isRightPanelOpen ? "w-80 opacity-100 translate-x-0 p-6" : "w-0 p-0 opacity-0 translate-x-full"
      )}
    >
      <div className="flex flex-col gap-4">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2 bg-surface-container-low px-4 py-2 rounded-full border border-outline-variant/10">
            <span className="w-2 h-2 rounded-full bg-secondary"></span>
            <span className="text-xs font-label text-on-surface-variant uppercase tracking-wider">
              System Optimal
            </span>
          </div>
          <div className="flex items-center gap-1">
            <button className="p-1.5 rounded-full hover:bg-surface-container/40 text-primary transition-all duration-200">
              <span className="material-symbols-outlined text-xl">tune</span>
            </button>
            <button 
              onClick={toggleRightPanel}
              className="p-1.5 rounded-full hover:bg-surface-container/40 text-primary transition-all duration-200"
            >
              <span className="material-symbols-outlined text-xl">close</span>
            </button>
          </div>
        </div>
        
        <h3 className="font-headline font-bold text-lg text-primary mt-2">
          Contextual Tools
        </h3>
      </div>
      
      <div className="space-y-4">
        <div className="bg-surface-container p-4 rounded-xl border border-outline-variant/10">
          <p className="text-xs font-label text-on-surface-variant mb-3 uppercase tracking-tighter font-bold">
            Current Session Token
          </p>
          <div className="h-2 w-full bg-surface-container-lowest rounded-full overflow-hidden">
            <div className="h-full bg-secondary w-[65%]"></div>
          </div>
          <p className="text-[10px] text-on-surface-variant mt-2 text-right font-medium">
            65% / 100k Tokens
          </p>
        </div>

        <div className="bg-surface-container p-4 rounded-xl border border-outline-variant/10">
          <div className="flex justify-between items-center mb-3">
            <p className="text-xs font-label text-on-surface-variant uppercase tracking-tighter font-bold">
              Active Assets
            </p>
            <span className="material-symbols-outlined text-sm text-primary cursor-pointer">
              open_in_new
            </span>
          </div>
          <div className="grid grid-cols-3 gap-2">
            {[1, 2, 3].map((i) => (
              <div
                key={i}
                className="aspect-square bg-surface-container-lowest rounded-lg border border-outline-variant/10 hover:border-secondary transition-colors cursor-pointer flex items-center justify-center text-on-surface-variant"
              >
                <span className="material-symbols-outlined">
                  {i === 1 ? "description" : i === 2 ? "palette" : "add"}
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>
    </aside>
  );
}
