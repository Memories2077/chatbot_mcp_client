"use client";

import { useState } from "react";
import { cn } from "@/lib/utils";
import { useChatStore } from "@/lib/hooks/use-chat-store";
import { MODEL_CONFIG, BACKEND_API } from "@/lib/config";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Slider } from "@/components/ui/slider";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { useToast } from "@/hooks/use-toast";

export function RightUtilityPanel() {
  const { isRightPanelOpen, toggleRightPanel, settings, setSettings } = useChatStore();
  const [mcpInput, setMcpInput] = useState("");
  const [isVerifyingMcp, setIsVerifyingMcp] = useState(false);
  const { toast } = useToast();

  const providers = Object.keys(MODEL_CONFIG);
  const currentModels = MODEL_CONFIG[settings.provider]?.models || [];

  const handleAddMcp = async () => {
    const trimmedUrl = mcpInput.trim();
    if (!trimmedUrl) return;
    
    setIsVerifyingMcp(true);
    
    try {
      const response = await fetch(BACKEND_API.mcpMetadata(), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url: trimmedUrl })
      });

      const data = await response.json();

      if (!response.ok || data.status === "error") {
        throw new Error(data.detail || "Connection refused by host or invalid MCP URL.");
      }
      
      const newMcp = { 
        name: data.name, 
        url: trimmedUrl 
      };

      if (settings.mcpServers.some(s => s.url === newMcp.url)) {
        toast({ 
          title: "Duplicate Server", 
          description: "This MCP server is already in your active list.",
          variant: "destructive" 
        });
      } else {
        setSettings({ mcpServers: [...settings.mcpServers, newMcp] });
        setMcpInput("");
        toast({ 
          title: "Neural Link Established", 
          description: `Successfully connected to ${data.name}.` 
        });
      }
    } catch (error: any) {
      console.error("MCP Verification Error:", error);
      toast({ 
        title: "Connection Failed", 
        description: "Ethereal could not reach the specified neural node.",
        variant: "destructive"
      });
    } finally {
      setIsVerifyingMcp(false);
    }
  };

  const handleRemoveMcp = (url: string) => {
    setSettings({ mcpServers: settings.mcpServers.filter(s => s.url !== url) });
  };

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
          <button 
            onClick={toggleRightPanel}
            className="p-1.5 rounded-full hover:bg-surface-container/40 text-primary transition-all duration-200"
          >
            <span className="material-symbols-outlined text-xl">close</span>
          </button>
        </div>
        
        <h3 className="font-headline font-bold text-lg text-primary mt-2 flex items-center gap-2">
          <span className="material-symbols-outlined">tune</span>
          Model Settings
        </h3>
      </div>
      
      <div className="flex-1 overflow-y-auto space-y-6 pr-2 no-scrollbar">
        {/* Provider Selection */}
        <div className="space-y-2">
          <label className="text-[10px] font-bold text-on-surface-variant uppercase tracking-widest ml-1">Provider</label>
          <Select 
            value={settings.provider} 
            onValueChange={(val: any) => setSettings({ provider: val })}
          >
            <SelectTrigger className="w-full bg-surface-container-lowest/50 border-outline-variant/10 rounded-xl h-12">
              <SelectValue placeholder="Select Provider" />
            </SelectTrigger>
            <SelectContent>
              {providers.map(p => (
                <SelectItem key={p} value={p} className="capitalize">{p}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        {/* Model Selection */}
        <div className="space-y-2">
          <label className="text-[10px] font-bold text-on-surface-variant uppercase tracking-widest ml-1">Model Name</label>
          <Select 
            value={settings.model} 
            onValueChange={(val) => setSettings({ model: val })}
          >
            <SelectTrigger className="w-full bg-surface-container-lowest/50 border-outline-variant/10 rounded-xl h-12">
              <SelectValue placeholder="Select Model" />
            </SelectTrigger>
            <SelectContent>
              {currentModels.map(m => (
                <SelectItem key={m} value={m}>{m}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        {/* Temperature Slider */}
        <div className="space-y-4 bg-surface-container/40 p-4 rounded-2xl border border-outline-variant/10">
          <div className="flex justify-between items-center">
            <label className="text-[10px] font-bold text-on-surface-variant uppercase tracking-widest">Temperature</label>
            <span className="text-xs font-mono text-primary bg-primary/10 px-2 py-0.5 rounded-md">{settings.temperature}</span>
          </div>
          <Slider
            value={[settings.temperature]}
            max={1}
            step={0.1}
            onValueChange={(val) => setSettings({ temperature: val[0] })}
            className="py-2"
          />
          <p className="text-[9px] text-on-surface-variant leading-tight opacity-60">
            Higher values make output more random, lower values more deterministic.
          </p>
        </div>

        {/* MCP Servers */}
        <div className="space-y-4">
          <h3 className="font-headline font-bold text-sm text-primary flex items-center gap-2">
            <span className="material-symbols-outlined text-lg">hub</span>
            MCP Tools
          </h3>
          
          <div className="flex gap-2">
            <Input 
              placeholder="Server URL..." 
              value={mcpInput}
              onChange={(e) => setMcpInput(e.target.value)}
              className="bg-surface-container-lowest/50 border-outline-variant/10 rounded-xl flex-1"
              disabled={isVerifyingMcp}
              onKeyDown={(e) => e.key === "Enter" && handleAddMcp()}
            />
            <Button 
              onClick={handleAddMcp}
              size="icon" 
              className="rounded-xl bg-primary text-on-primary shrink-0"
              disabled={isVerifyingMcp || !mcpInput.trim()}
            >
              {isVerifyingMcp ? (
                <span className="animate-spin material-symbols-outlined">sync</span>
              ) : (
                <span className="material-symbols-outlined">add</span>
              )}
            </Button>
          </div>

          <div className="space-y-2 max-h-48 overflow-y-auto pr-1 no-scrollbar">
            {settings.mcpServers.map((server) => (
              <div 
                key={server.url} 
                className="group flex items-center justify-between p-3 bg-surface-container-lowest/30 rounded-xl border border-outline-variant/5 hover:border-outline-variant/20 transition-all"
              >
                <div className="flex flex-col overflow-hidden mr-2">
                  <span className="text-xs font-bold text-on-surface truncate">{server.name}</span>
                  <span className="text-[9px] text-on-surface-variant truncate opacity-60">{server.url}</span>
                </div>
                <button 
                  onClick={() => handleRemoveMcp(server.url)}
                  className="opacity-0 group-hover:opacity-100 p-1 hover:text-error transition-all"
                >
                  <span className="material-symbols-outlined text-sm">delete</span>
                </button>
              </div>
            ))}
            {settings.mcpServers.length === 0 && (
              <div className="py-8 text-center border-2 border-dashed border-outline-variant/10 rounded-2xl">
                <span className="material-symbols-outlined text-on-surface-variant/20 text-3xl">dns</span>
                <p className="text-[10px] text-on-surface-variant/40 mt-1 uppercase font-bold tracking-tighter">No Servers Active</p>
              </div>
            )}
          </div>
        </div>
      </div>

      <div className="mt-auto pt-4 border-t border-outline-variant/10">
        <div className="bg-primary/5 p-4 rounded-2xl border border-primary/10">
          <div className="flex justify-between items-center mb-2">
            <p className="text-[10px] font-bold text-primary uppercase tracking-widest">Token Usage</p>
            <span className="text-[9px] font-mono text-primary/60">65%</span>
          </div>
          <div className="h-1.5 w-full bg-surface-container-lowest rounded-full overflow-hidden">
            <div className="h-full bg-primary w-[65%] rounded-full shadow-[0_0_10px_rgba(255,255,255,0.2)]"></div>
          </div>
        </div>
      </div>
    </aside>
  );
}
