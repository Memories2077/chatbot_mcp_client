import * as React from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { cn } from '@/lib/utils';
import type { ChatMessage as ChatMessageType } from '@/lib/types';
import { ChevronDown, Zap, Sparkles, Database, Server, Copy, CheckCircle2 } from 'lucide-react';

interface ChatMessageProps {
  message?: ChatMessageType;
  isLoading?: boolean;
}

// DelegateBox Component
const DelegateBox = ({ title, content, icon: Icon, color }: { title: string; content: string; icon: React.ReactNode; color: string }) => {
  const [isOpen, setIsOpen] = React.useState(false);
  
  return (
    <div className={cn(
      "my-3 rounded-2xl border transition-all duration-500 overflow-hidden",
      isOpen
        ? `border-${color}-500/30 bg-${color}-500/[0.03]`
        : `border-outline-variant/5 bg-surface-container-low/5 hover:bg-surface-container-low/10`
    )}>
      <button 
        onClick={() => setIsOpen(!isOpen)}
        className={cn(
          "w-full px-6 py-4 flex items-center justify-between hover:bg-white/5 transition-colors group/btn",
          color === 'amber' && "hover:bg-amber-500/5",
          color === 'blue' && "hover:bg-blue-500/5",
          color === 'purple' && "hover:bg-purple-500/5"
        )}
      >
        <div className="flex items-center gap-3">
          <div className={cn(
            "w-7 h-7 rounded-full flex items-center justify-center transition-all",
            color === 'amber' && "bg-amber-500/10 text-amber-400",
            color === 'blue' && "bg-blue-500/10 text-blue-400",
            color === 'purple' && "bg-purple-500/10 text-purple-400"
          )}>
            {Icon}
          </div>
          <span className={cn(
            "text-[11px] font-bold tracking-[0.25em] uppercase transition-colors font-headline",
            color === 'amber' && "text-amber-500",
            color === 'blue' && "text-blue-500",
            color === 'purple' && "text-purple-500"
          )}>
            {title}
          </span>
        </div>
        <ChevronDown className={cn("w-4 h-4 transition-transform duration-500", isOpen && "rotate-180", color === 'amber' && "text-amber-500/50", color === 'blue' && "text-blue-500/50", color === 'purple' && "text-purple-500/50")} />
      </button>
      
      <div className={cn(
        "transition-all duration-500 ease-in-out overflow-hidden",
        isOpen ? "max-h-[3000px] opacity-100" : "max-h-0 opacity-0"
      )}>
        <div className={cn(
          "px-8 pb-8 pt-2 border-t",
          color === 'amber' && "border-amber-500/10",
          color === 'blue' && "border-blue-500/10",
          color === 'purple' && "border-purple-500/10"
        )}>
          <div className="prose prose-sm md:prose-base dark:prose-invert max-w-none text-on-surface/85 leading-relaxed font-body">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>
              {content}
            </ReactMarkdown>
          </div>
        </div>
      </div>
    </div>
  );
};

// EnrichedContextBox Component
const EnrichedContextBox = ({ content }: { content: string }) => {
  const [isOpen, setIsOpen] = React.useState(false);
  
  return (
    <div className={cn(
      "my-3 rounded-2xl border transition-all duration-500 overflow-hidden",
      isOpen
        ? "border-purple-500/30 bg-purple-500/[0.03]"
        : "border-outline-variant/5 bg-surface-container-low/5 hover:bg-surface-container-low/10"
    )}>
      <button 
        onClick={() => setIsOpen(!isOpen)}
        className="w-full px-6 py-4 flex items-center justify-between hover:bg-purple-500/5 transition-colors group/btn"
      >
        <div className="flex items-center gap-3">
          <div className="w-7 h-7 rounded-full bg-purple-500/10 text-purple-400 flex items-center justify-center">
            <Database className="w-4 h-4" />
          </div>
          <span className="text-[11px] font-bold tracking-[0.25em] uppercase text-purple-500 font-headline">
            Enriched Context (RAG)
          </span>
        </div>
        <ChevronDown className={cn("w-4 h-4 text-purple-500/50 transition-transform duration-500", isOpen && "rotate-180")} />
      </button>
      
      <div className={cn(
        "transition-all duration-500 ease-in-out overflow-hidden",
        isOpen ? "max-h-[1000px] opacity-100" : "max-h-0 opacity-0"
      )}>
        <div className="px-8 pb-8 pt-2 border-t border-purple-500/10">
          <div className="text-sm text-on-surface/70">
            {content === '[]' ? (
              <p className="italic text-on-surface-variant/60">No enriched context available</p>
            ) : (
              <ReactMarkdown remarkPlugins={[remarkGfm]}>
                {content}
              </ReactMarkdown>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

// MCP Success Card Component
const McpSuccessCard = ({ content }: { content: string }) => {
  const [isOpen, setIsOpen] = React.useState(true);
  const [copied, setCopied] = React.useState(false);
  
  const handleCopy = (text: string) => {
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };
  
  const serverIdMatch = content.match(/Server ID:\s*([\w-]+)/i);
  const statusMatch = content.match(/Status:\s*(\w+)/i);
  const jsonMatch = content.match(/```json\n([\s\S]*?)\n```/) || content.match(/\{[\s\S]*"mcpServers"[\s\S]*\}/);
  
  let jsonStr = "";
  if (jsonMatch) {
    jsonStr = typeof jsonMatch[1] === 'string' ? jsonMatch[1] : jsonMatch[0];
  }
  
  return (
    <div className="my-3 rounded-2xl border border-emerald-500/20 bg-emerald-500/[0.03] overflow-hidden transition-all duration-500">
      <button 
        onClick={() => setIsOpen(!isOpen)}
        className="w-full px-6 py-4 flex items-center justify-between hover:bg-emerald-500/5 transition-colors group/btn"
      >
        <div className="flex items-center gap-3">
          <div className="w-7 h-7 rounded-full bg-emerald-500/10 flex items-center justify-center">
            <CheckCircle2 className="w-4 h-4 text-emerald-400" />
          </div>
          <span className="text-[11px] font-bold tracking-[0.25em] uppercase text-emerald-500">MCP Server Created Successfully</span>
        </div>
        <ChevronDown className={cn("w-4 h-4 text-emerald-500/50 transition-transform duration-500", isOpen && "rotate-180")} />
      </button>
      
      <div className={cn(
        "transition-all duration-500 ease-in-out overflow-hidden",
        isOpen ? "max-h-[2000px] opacity-100" : "max-h-0 opacity-0"
      )}>
        <div className="px-6 pb-6 pt-2 border-t border-emerald-500/10 space-y-6">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {serverIdMatch && (
              <div className="bg-white/5 p-4 rounded-xl border border-emerald-500/10 group/card">
                <span className="text-[9px] font-bold uppercase text-emerald-500/60 block mb-3">Server ID</span>
                <div className="flex items-start justify-between gap-3">
                  <span className="text-xs font-mono text-emerald-400 break-all">{serverIdMatch[1]}</span>
                  <button 
                    onClick={() => handleCopy(serverIdMatch[1])}
                    className="opacity-0 group-hover/card:opacity-100 transition-opacity p-1 hover:bg-emerald-500/20 rounded flex-shrink-0"
                  >
                    <Copy className="w-3 h-3 text-emerald-400" />
                  </button>
                </div>
              </div>
            )}
            {statusMatch && (
              <div className="bg-white/5 p-4 rounded-xl border border-emerald-500/10">
                <span className="text-[9px] font-bold uppercase text-emerald-500/60 block mb-3">Status</span>
                <div className="flex items-center gap-2">
                  <span className="relative flex h-2 w-2 flex-shrink-0">
                    <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-500 opacity-75"></span>
                    <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
                  </span>
                  <span className="text-xs font-bold text-emerald-400 uppercase">{statusMatch[1]}</span>
                </div>
              </div>
            )}
          </div>
          
          {jsonStr && (
            <div>
              <span className="text-[9px] font-bold uppercase text-emerald-500/60 block mb-3">Configuration</span>
              <div className="relative group/code">
                <button 
                  onClick={() => handleCopy(jsonStr)}
                  className="absolute top-3 right-3 p-2 bg-emerald-500/10 hover:bg-emerald-500/20 text-emerald-400 rounded-lg border border-emerald-500/20 transition-all opacity-0 group-hover/code:opacity-100 z-10"
                >
                  <Copy className="w-4 h-4" />
                </button>
                <div className="bg-black/60 rounded-xl border border-emerald-500/10 overflow-hidden">
                  <pre className="p-4 text-[11px] font-mono leading-relaxed text-emerald-300/70 overflow-x-auto no-scrollbar max-h-[300px] whitespace-pre-wrap break-words">
                    {jsonStr}
                  </pre>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

// Parse content into sections
const parseContent = (text: string) => {
  const sections: {
    type: 'examiner' | 'generator' | 'context' | 'success' | 'text';
    title?: string;
    content: string;
    serverId?: string;
  }[] = [];
  
  // Extract sections using regex
  const examinerMatch = text.match(/DELEGATE_TO_EXAMINER:([\s\S]*?)(?=DELEGATE_TO_GENERATOR:|ENRICHED_CONTEXT|✅|$)/i);
  const generatorMatch = text.match(/DELEGATE_TO_GENERATOR:([\s\S]*?)(?=ENRICHED_CONTEXT|✅|$)/i);
  const contextMatch = text.match(/ENRICHED_CONTEXT\s*\(RAG\):\s*([\s\S]*?)(?=✅|USER_ID|$)/i);
  const successMatches = text.matchAll(/✅\s*MCP Server created successfully!([\s\S]*?)(?=✅|$)/gi);
  
  if (examinerMatch) {
    sections.push({
      type: 'examiner',
      title: 'Delegate to Examiner',
      content: examinerMatch[1].trim(),
    });
  }
  
  if (generatorMatch) {
    sections.push({
      type: 'generator',
      title: 'Delegate to Generator',
      content: generatorMatch[1].trim(),
    });
  }
  
  if (contextMatch) {
    sections.push({
      type: 'context',
      content: contextMatch[1].trim(),
    });
  }
  
  const successIds = new Set<string>();
  for (const match of successMatches) {
    const serverIdMatch = match[1].match(/Server ID:\s*([\w-]+)/i);
    const serverId = serverIdMatch?.[1] || 'unknown';
    
    if (!successIds.has(serverId)) {
      sections.push({
        type: 'success',
        serverId,
        content: match[0],
      });
      successIds.add(serverId);
    }
  }
  
  return sections.length > 0 ? sections : [{ type: 'text' as const, content: text }];
};

const ChatMessage = React.memo(({ message, isLoading }: ChatMessageProps) => {
  const role = isLoading ? 'model' : message!.role;
  const content = isLoading ? '' : message!.content;
  const isUser = role === 'user';

  if (isUser) {
    return (
      <div className="flex justify-end w-full mb-8 animate-in fade-in slide-in-from-right-4 duration-300">
        <div className="flex flex-col items-end max-w-[80%] md:max-w-[70%]">
          <div className="flex items-center gap-2 mb-2 px-1">
            <span className="text-[10px] font-bold uppercase tracking-[0.2em] text-secondary opacity-70 font-label">Explorer</span>
            <div className="w-6 h-6 rounded-full bg-secondary/10 flex items-center justify-center border border-secondary/20">
              <span className="material-symbols-outlined text-[14px] text-secondary">person</span>
            </div>
          </div>
          <div className="bg-surface-container-highest/40 backdrop-blur-md text-on-surface px-5 py-3 rounded-2xl rounded-tr-none border border-outline-variant/10 shadow-sm break-words w-full">
            <p className="text-sm leading-relaxed whitespace-pre-wrap">{content}</p>
          </div>
          {message?.timestamp && (
            <span className="mt-1 px-1 text-[9px] opacity-30 font-medium">
              {new Date(message.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
            </span>
          )}
        </div>
      </div>
    );
  }

  const sections = parseContent(content);
  const hasMcpSections = sections.some(s => ['examiner', 'generator', 'context', 'success'].includes(s.type));

  return (
    <div className="w-full mb-12 animate-in fade-in slide-in-from-bottom-4 duration-500">
      <div className="flex items-center gap-3 mb-5 opacity-80">
        <div className="w-8 h-8 rounded-lg bg-primary/10 text-primary flex items-center justify-center border border-primary/20 shadow-[0_0_15px_rgba(250,249,253,0.1)]">
          <span className="material-symbols-outlined text-[18px]">auto_awesome</span>
        </div>
        <div className="flex flex-col">
          <span className="text-[10px] font-bold uppercase tracking-[0.3em] text-primary font-headline">Ethereal Intelligence</span>
          <span className="text-[8px] uppercase tracking-widest text-on-surface-variant opacity-50">Neural Processing Unit</span>
        </div>
      </div>
      
      <div className="w-full bg-surface-container-low/20 rounded-[2rem] p-6 md:p-10 border border-outline-variant/5 shadow-2xl backdrop-blur-sm relative overflow-hidden group">
        <div className="absolute top-0 left-0 w-full h-[1px] bg-gradient-to-r from-transparent via-primary/30 to-transparent"></div>
        
        {isLoading ? (
          <div className="flex items-center gap-5 py-6">
            <div className="flex gap-2">
              <span className="w-2.5 h-2.5 bg-primary rounded-full animate-bounce [animation-delay:-0.3s] shadow-[0_0_10px_rgba(250,249,253,0.5)]"></span>
              <span className="w-2.5 h-2.5 bg-primary rounded-full animate-bounce [animation-delay:-0.15s] shadow-[0_0_10px_rgba(250,249,253,0.5)]"></span>
              <span className="w-2.5 h-2.5 bg-primary rounded-full animate-bounce shadow-[0_0_10px_rgba(250,249,253,0.5)]"></span>
            </div>
            <span className="text-sm font-medium text-on-surface-variant animate-pulse tracking-tight italic font-body">Synthesizing response from neural data...</span>
          </div>
        ) : hasMcpSections ? (
          <div className="flex flex-col">
            {sections.map((section, idx) => {
              let delayMs = 0;
              if (section.type === 'examiner') delayMs = 0;
              else if (section.type === 'generator') delayMs = 700;
              else if (section.type === 'context') delayMs = 1400;
              
              const animationStyle = delayMs > 0 ? { animationDelay: `${delayMs}ms` } : undefined;
              
              if (section.type === 'examiner') {
                return (
                  <div key={idx} className="animate-in fade-in slide-in-from-bottom-4 duration-300" style={animationStyle}>
                    <DelegateBox
                      title="Delegate to Examiner"
                      content={section.content}
                      icon={<Zap className="w-4 h-4" />}
                      color="amber"
                    />
                  </div>
                );
              }
              if (section.type === 'generator') {
                return (
                  <div key={idx} className="animate-in fade-in slide-in-from-bottom-4 duration-300" style={animationStyle}>
                    <DelegateBox
                      title="Delegate to Generator"
                      content={section.content}
                      icon={<Sparkles className="w-4 h-4" />}
                      color="blue"
                    />
                  </div>
                );
              }
              if (section.type === 'context') {
                return (
                  <div key={idx} className="animate-in fade-in slide-in-from-bottom-4 duration-300" style={animationStyle}>
                    <EnrichedContextBox content={section.content} />
                  </div>
                );
              }
              if (section.type === 'success') {
                return <McpSuccessCard key={idx} content={section.content} />;
              }
              return null;
            })}
          </div>
        ) : (
          <div className="prose prose-sm md:prose-base dark:prose-invert max-w-none break-words overflow-x-hidden">
            <ReactMarkdown
              remarkPlugins={[remarkGfm]}
              components={{
                pre({node, ...props}) {
                  return (
                    <div className="relative my-8 group/code">
                      <div className="absolute -top-3 right-4 px-3 py-1 bg-surface-container-highest text-[9px] font-bold font-mono rounded-full border border-outline-variant/20 opacity-0 group-hover/code:opacity-100 transition-all duration-300 transform translate-y-1 group-hover/code:translate-y-0 z-10 text-primary">
                        SOURCE_CODE
                      </div>
                      <pre {...props} className="bg-black/60 p-6 rounded-2xl border border-outline-variant/10 overflow-x-auto no-scrollbar font-mono text-xs md:text-sm leading-relaxed shadow-inner" />
                    </div>
                  );
                },
                code(props: any) {
                  const { inline, className, children } = props;
                  return inline ? (
                    <code className="bg-primary/10 text-primary px-1.5 py-0.5 rounded-md font-mono text-[0.85em] border border-primary/5">
                      {children}
                    </code>
                  ) : (
                    <code className={cn(className, "block")}>
                      {children}
                    </code>
                  );
                },
                p: ({children}) => <p className="mb-6 last:mb-0 leading-relaxed text-on-surface/90 font-body">{children}</p>,
                li: ({children}) => <li className="mb-2 text-on-surface/80">{children}</li>,
                h1: ({children}) => <h1 className="text-2xl font-bold mb-6 text-primary border-b border-outline-variant/10 pb-2">{children}</h1>,
                h2: ({children}) => <h2 className="text-xl font-bold mb-4 text-primary/90">{children}</h2>,
              }}
            >
              {content}
            </ReactMarkdown>
          </div>
        )}

        {!isLoading && message?.timestamp && (
          <div className="mt-10 pt-5 border-t border-outline-variant/5 flex justify-between items-center opacity-20 group-hover:opacity-40 transition-opacity duration-500">
            <div className="flex items-center gap-2">
              <span className="w-1 h-1 rounded-full bg-primary"></span>
              <span className="text-[9px] font-bold tracking-[0.2em] uppercase">Verified Output</span>
            </div>
            <span className="text-[9px] font-mono tracking-tighter">
              {new Date(message.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' })}
            </span>
          </div>
        )}
      </div>
    </div>
  );
});

ChatMessage.displayName = 'ChatMessage';

export { ChatMessage };

