"use client";

import { usePathname } from "next/navigation";
import { useSidebar } from "@/components/ui/sidebar";
import { useChatStore } from "@/lib/hooks/use-chat-store";

export function Header() {
  const pathname = usePathname();
  const { toggleSidebar } = useSidebar();
  const { toggleRightPanel } = useChatStore();

  const getTitle = () => {
    if (pathname === "/chat") return "Welcome back, Alex";
    if (pathname === "/history") return "Archives.";
    return "Ethereal Intelligence";
  };

  return (
    <header className="flex justify-between items-center px-8 py-4 w-full bg-transparent z-40 shrink-0">
      <div className="flex items-center gap-4">
        <button 
          onClick={toggleSidebar}
          className="p-2 text-on-surface hover:bg-surface-container/40 rounded-full transition-colors"
          aria-label="Toggle Sidebar"
        >
          <span className="material-symbols-outlined">menu</span>
        </button>
        <h2 className="text-xl font-black text-[#dee5ff] font-headline tracking-tight">
          {getTitle()}
        </h2>
      </div>

      <div className="flex items-center gap-4">
        <button 
          onClick={toggleRightPanel}
          className="p-2 text-on-surface hover:bg-surface-container/40 rounded-full transition-colors"
          aria-label="Toggle Utility Panel"
        >
          <span className="material-symbols-outlined">dock_to_right</span>
        </button>
      </div>
    </header>
  );
}
