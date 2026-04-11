import * as React from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { cn } from '@/lib/utils';
import type { ChatMessage as ChatMessageType } from '@/lib/types';

interface ChatMessageProps {
  message?: ChatMessageType;
  isLoading?: boolean;
}

const ChatMessage = React.memo(({ message, isLoading }: ChatMessageProps) => {
  const role = isLoading ? 'model' : message!.role;
  const content = isLoading ? '...' : message!.content;
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

  // AI Response Style: Professional Document/Textbox Look
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
        {/* Decorative Top Line */}
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
                code({node, inline, className, children, ...props}) {
                  return inline ? (
                    <code className="bg-primary/10 text-primary px-1.5 py-0.5 rounded-md font-mono text-[0.85em] border border-primary/5" {...props}>
                      {children}
                    </code>
                  ) : (
                    <code className={cn(className, "block")} {...props}>
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
