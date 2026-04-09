"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { cn } from "@/lib/utils";
import { useSidebar } from "@/components/ui/sidebar";
import { useChatStore } from "@/lib/hooks/use-chat-store";

const navItems = [
  { label: "Search", href: "#", icon: "search" },
  { label: "Chat History", href: "/history", icon: "history" },
  { label: "Projects", href: "#", icon: "folder_open" },
];

export function Sidebar() {
  const pathname = usePathname();
  const router = useRouter();
  const { open, isMobile, toggleSidebar, setOpen } = useSidebar();
  const { clearMessages, history, loadHistory } = useChatStore();

  if (isMobile) return null;

  const handleNewChat = () => {
    clearMessages();
    setOpen(false); // Auto close sidebar
    router.push("/chat");
  };

  const handleLoadChat = (id: string) => {
    loadHistory(id);
    setOpen(false); // Auto close sidebar
    router.push("/chat");
  };

  const handleNavLinkClick = () => {
    setOpen(false); // Auto close sidebar on nav
  };

  return (
    <aside
      className={cn(
        "hidden md:flex flex-col h-full p-6 bg-surface-container-low/60 backdrop-blur-[32px] rounded-r-[3rem] shadow-[0_0_50px_rgba(0,0,0,0.3)] z-50 transition-all duration-500 ease-in-out overflow-hidden absolute left-0 top-0",
        open ? "w-80 opacity-100 translate-x-0" : "w-0 p-0 opacity-0 -translate-x-full"
      )}
    >
      <div className="mb-10 flex items-center justify-between px-2 w-full">
        <Link href="/" className="flex items-center gap-3" onClick={handleNavLinkClick}>
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-primary to-primary-container flex items-center justify-center text-on-primary">
            <span className="material-symbols-outlined">auto_awesome</span>
          </div>
          <div className="flex flex-col">
            <span className="text-2xl font-bold text-white font-headline">
              Memories
            </span>
          </div>
        </Link>
        <button 
          onClick={toggleSidebar}
          className="p-2 hover:bg-surface-container/40 rounded-full text-on-surface-variant transition-colors"
        >
          <span className="material-symbols-outlined">close</span>
        </button>
      </div>

      <button 
        onClick={handleNewChat}
        className="mb-8 w-full bg-primary text-on-primary font-bold py-4 px-6 rounded-full flex items-center justify-center gap-2 hover:scale-95 active:scale-90 transition-all duration-300 shadow-lg shadow-primary/20"
      >
        <span className="material-symbols-outlined">add_circle</span>
        New Chat
      </button>

      <nav className="space-y-2 mb-8">
        {navItems.map((item) => {
          const isActive = pathname === item.href;
          return (
            <Link
              key={item.label}
              href={item.href}
              onClick={handleNavLinkClick}
              className={cn(
                "flex items-center gap-4 p-4 rounded-2xl transition-all duration-300 font-headline tracking-tight",
                isActive
                  ? "bg-surface-container text-primary font-bold"
                  : "text-on-surface-variant hover:bg-surface-container/40"
              )}
            >
              <span className="material-symbols-outlined">{item.icon}</span>
              <span>{item.label}</span>
            </Link>
          );
        })}
      </nav>

      {/* Recent History Section */}
      <div className="flex-1 overflow-y-auto no-scrollbar space-y-4">
        <h3 className="px-4 text-[10px] font-bold uppercase tracking-[0.2em] text-on-surface-variant opacity-50">Recent Conversations</h3>
        <div className="space-y-1">
          {history.slice(0, 5).map((chat) => (
            <button
              key={chat.id}
              onClick={() => handleLoadChat(chat.id)}
              className="w-full flex flex-col gap-1 p-4 rounded-2xl text-left hover:bg-surface-container/40 transition-all group"
            >
              <span className="text-xs font-bold text-on-surface truncate group-hover:text-primary transition-colors">{chat.title}</span>
              <span className="text-[10px] text-on-surface-variant opacity-50">
                {new Date(chat.timestamp).toLocaleDateString()}
              </span>
            </button>
          ))}
          {history.length === 0 && (
            <p className="px-4 py-8 text-[10px] text-center text-on-surface-variant opacity-30 italic">No recent chats</p>
          )}
        </div>
      </div>

      <div className="mt-auto pt-6 border-t border-outline-variant/10">
        <div className="flex items-center gap-3 p-2 hover:bg-surface-container/40 rounded-xl transition-colors cursor-pointer">
          <img
            alt="Profile"
            className="w-10 h-10 rounded-full border-2 border-primary/20 object-cover"
            src="https://lh3.googleusercontent.com/aida-public/AB6AXuD_KVwTptp5FKeoBaD47uLZEfKUByKbFnfLtqYjjcC65rlxUTYrBCm-kPs3spVjM2RVbWlPzP-AiYTJ4dA-BDWMjjcHuyy3no4CWu-NXGNJ55XqrEHX73MvL_meckHanvxGC1DVDWMkPPmXkqHjaN81R7wTzirlcxl8_lNj9DZhXJm-DKPWy8gXEwbgjzWHrfgq0R5nEdRVfecMIf-BfPe3pvc4AIfZs3gaYsTpHqitoEwShFwl32OXR9XQDW_0WnZvGufg4A0bwvor"
          />
          <div className="flex flex-col">
            <span className="text-sm font-bold text-on-surface">Alex Rivera</span>
            <span className="text-xs text-on-surface-variant font-label">Pro Member</span>
          </div>
          <span className="ml-auto material-symbols-outlined text-on-surface-variant">
            more_vert
          </span>
        </div>
      </div>
    </aside>
  );
}
