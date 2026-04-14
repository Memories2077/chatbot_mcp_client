"use client";

import { create } from "zustand";
import { persist, createJSONStorage } from "zustand/middleware";
import { v4 as uuidv4 } from "uuid";
import type { ChatMessage, ChatSettings, ChatHistoryItem } from "@/lib/types";
import { BACKEND_API, MODEL_CONFIG } from "@/lib/config";
import { createLangGraphClient, ASSISTANT_ID } from "@/lib/langgraph";

interface ChatState {
  messages: ChatMessage[];
  history: ChatHistoryItem[];
  currentChatId: string | null;
  settings: ChatSettings;
  isLoading: boolean;
  isRightPanelOpen: boolean;
  isMcpMode: boolean;
  lastActive: number;
  toggleRightPanel: () => void;
  setRightPanelOpen: (open: boolean) => void;
  toggleMcpMode: () => void;
  sendMessage: (text: string, settings?: ChatSettings) => void;
  setSettings: (settings: Partial<ChatSettings>) => void;
  addMessage: (message: ChatMessage) => void;
  clearMessages: () => void;
  loadHistory: (id: string) => void;
  deleteHistory: (id: string) => void;
  persistCurrentChat: () => void;
}

const SESSION_TIMEOUT = 1000 * 60 * 60; // 1 hour

const defaultSettings: ChatSettings = {
  provider: "gemini",
  model: "gemini-2.5-flash",
  temperature: 0.7,
  maxTokens: 2048,
  mcpServers: [],
};

export const useChatStore = create<ChatState>()(
  persist(
    (set, get) => ({
      messages: [],
      history: [],
      currentChatId: null,
      settings: defaultSettings,
      isLoading: false,
      isRightPanelOpen: false, // Default to closed for better UX
      isMcpMode: false,
      lastActive: Date.now(),

      toggleRightPanel: () =>
        set((state) => ({ isRightPanelOpen: !state.isRightPanelOpen })),
      setRightPanelOpen: (open: boolean) => set({ isRightPanelOpen: open }),
      
      toggleMcpMode: () => set((state) => ({ isMcpMode: !state.isMcpMode })),

      setSettings: (newSettings) => {
        const currentSettings = get().settings;
        const updatedSettings = { ...currentSettings, ...newSettings };
        if (
          newSettings.provider &&
          newSettings.provider !== currentSettings.provider
        ) {
          updatedSettings.model =
            MODEL_CONFIG[newSettings.provider as keyof typeof MODEL_CONFIG]?.defaultModel || updatedSettings.model;
        }
        set({ settings: updatedSettings, lastActive: Date.now() });
      },

      addMessage: (message) =>
        set((state) => ({
          messages: [...state.messages, message],
          lastActive: Date.now(),
        })),

      persistCurrentChat: () => {
        const { messages, history, currentChatId } = get();
        if (messages.length === 0) return;

        let updatedHistory = [...history];
        const firstMsg =
          messages.find((m) => m.role === "user")?.content || "Untitled Chat";
        const title =
          firstMsg.length > 30 ? firstMsg.substring(0, 30) + "..." : firstMsg;

        if (currentChatId) {
          const index = updatedHistory.findIndex((h) => h.id === currentChatId);
          if (index !== -1) {
            updatedHistory[index] = {
              ...updatedHistory[index],
              messages: [...messages],
              timestamp: new Date().toISOString(),
            };
            const item = updatedHistory.splice(index, 1)[0];
            updatedHistory.unshift(item);
          } else {
            const newId = uuidv4();
            const newItem: ChatHistoryItem = {
              id: newId,
              title,
              messages: [...messages],
              timestamp: new Date().toISOString(),
            };
            updatedHistory = [newItem, ...updatedHistory];
            set({ currentChatId: newId });
          }
        } else {
          const newId = uuidv4();
          const newItem: ChatHistoryItem = {
            id: newId,
            title,
            messages: [...messages],
            timestamp: new Date().toISOString(),
          };
          updatedHistory = [newItem, ...updatedHistory];
          set({ currentChatId: newId });
        }
        set({ history: updatedHistory });
      },

      clearMessages: () => {
        const { persistCurrentChat } = get();
        persistCurrentChat();
        // Auto-close right panel when clearing/starting new chat
        set({
          messages: [],
          currentChatId: null,
          isRightPanelOpen: false,
          lastActive: Date.now(),
        });
      },

      loadHistory: (id: string) => {
        const { history } = get();
        const item = history.find((h) => h.id === id);
        if (item) {
          // Auto-close right panel when loading a historical chat to focus on content
          set({
            messages: [...item.messages],
            currentChatId: id,
            isRightPanelOpen: false,
            lastActive: Date.now(),
          });
        }
      },

      deleteHistory: (id: string) => {
        set((state) => ({
          history: state.history.filter((h) => h.id !== id),
          currentChatId:
            state.currentChatId === id ? null : state.currentChatId,
        }));
      },

      sendMessage: async (text, overrideSettings) => {
        const {
          messages,
          settings: currentSettings,
          currentChatId,
          isMcpMode,
          persistCurrentChat,
        } = get();
        
        const settings = overrideSettings || currentSettings;

        const formatBotResponse = (content: string) => {
          if (!content) return content;
          const trimmed = content.trim();
          if (trimmed.startsWith('{') && trimmed.includes('"mcpServers"')) {
            if (!trimmed.includes('```')) {
              return "```json\n" + trimmed + "\n```";
            }
          }
          return content;
        };

        
        // Ensure we have a local chat ID
        let chatId = currentChatId;
        if (!chatId) {
          chatId = uuidv4();
          set({ currentChatId: chatId });
        }

        set({ isLoading: true, lastActive: Date.now() });

        const now = new Date().toISOString();
        const userMessage: ChatMessage = {
          id: uuidv4(),
          role: "user",
          content: text,
          timestamp: now,
        };

        const updatedMessages = [...messages, userMessage];
        set({ messages: updatedMessages });

        // --- BRANCH 1: Create MCP Server (LangGraph Streaming) ---
        if (isMcpMode) {
          try {
            const client = createLangGraphClient();
            // Reusing Thread ID if possible
            let lgThreadId: string | undefined = undefined;
            try {
              const existingThreads = await client.threads.search({
                metadata: { localChatId: chatId },
                limit: 1,
              });
              lgThreadId = existingThreads?.[0]?.thread_id;
            } catch {}

            if (!lgThreadId) {
              const newThread = await client.threads.create({
                metadata: { localChatId: chatId },
              });
              lgThreadId = newThread.thread_id;
            }

            const aiMessageId = uuidv4();
            set((state) => ({
              messages: [...state.messages, {
                id: aiMessageId,
                role: "model",
                content: "",
                timestamp: new Date().toISOString(),
              }],
            }));

            let fullContent = "";
            let lastLength = 0;
            let lastMsgId = '';
            const streamedIds = new Set<string>();

            const stream = client.runs.stream(
              lgThreadId,
              ASSISTANT_ID,
              {
                input: { messages: [{ role: "user", content: text }] }, // chỉ prompt hiện tại
                streamMode: "messages",
                config: { configurable: { model_name: settings.model } }
              }
            );

            for await (const chunk of stream) {
              if (chunk.event === "error") {
                console.error("LangGraph error:", chunk.data);
              }

              else if (chunk.event === "messages/partial" && Array.isArray(chunk.data)) {
                const msgChunk = chunk.data[0];
                if (typeof msgChunk.content === 'string' && msgChunk.content.length > 0) {
                  if (msgChunk.id !== lastMsgId) {
                    lastLength = 0;
                    lastMsgId = msgChunk.id;
                  }
                  streamedIds.add(msgChunk.id);
                  const newPart = msgChunk.content.substring(lastLength);
                  lastLength = msgChunk.content.length;

                  if (newPart) {
                    fullContent += newPart;
                    set((state) => ({
                      messages: state.messages.map((m) =>
                        m.id === aiMessageId ? { ...m, content: fullContent } : m
                      ),
                    }));
                  }
                }
              }

              else if (chunk.event === "messages/complete" && Array.isArray(chunk.data)) {
                const msgChunk = chunk.data[0];
                if (typeof msgChunk.content === 'string' && !streamedIds.has(msgChunk.id)) {
                  fullContent += (fullContent ? '\n' : '') + msgChunk.content;
                  set((state) => ({
                    messages: state.messages.map((m) =>
                      m.id === aiMessageId ? { ...m, content: fullContent } : m
                    ),
                  }));
                }
                lastLength = 0;
                lastMsgId = '';
              }
            }

            persistCurrentChat();
          } catch (error: any) {
            console.error("Error calling LangGraph:", error);
            set((state) => ({
              messages: [...state.messages, {
                id: uuidv4(),
                role: "system",
                content: error.message || "Failed to connect to Agent service.",
                timestamp: new Date().toISOString(),
              }],
              lastActive: Date.now(),
            }));
          } finally {
            set({ isLoading: false });
          }
        }
        // --- BRANCH 2: Casual Talk (Legacy FastAPI /chat) ---
        else {
          const historyForBackend = updatedMessages.map((msg) => ({
            role: msg.role === "model" ? "model" : "user",
            content: msg.content,
          }));

          try {
            const response = await fetch(BACKEND_API.chat(), {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({
                messages: historyForBackend,
                provider: settings?.provider,
                model: settings?.model,
                temperature: settings?.temperature,
                mcpServers: settings?.mcpServers?.map((s) => s.url) || [],
              }),
            });

            if (!response.ok) {
              throw new Error(`Backend error: ${response.statusText}`);
            }

            const data = await response.json();

            const modelMessage: ChatMessage = {
              id: uuidv4(),
              role: "model",
              content: formatBotResponse(data.response),
              timestamp: new Date().toISOString(),
            };

            set((state) => ({
              messages: [...state.messages, modelMessage],
              lastActive: Date.now(),
            }));

            persistCurrentChat();
          } catch (error: any) {
            console.error("Error calling AI flow:", error);
            const errorMessage: ChatMessage = {
              id: uuidv4(),
              role: "system",
              content: error.message || "Failed to connect to backend.",
              timestamp: new Date().toISOString(),
            };
            set((state) => ({
              messages: [...state.messages, errorMessage],
              lastActive: Date.now(),
            }));
          } finally {
            set({ isLoading: false });
          }
        }
      },
    }),
    {
      name: "gemini-insight-link-storage",
      storage: createJSONStorage(() => localStorage),
      partialize: (state) => ({
        history: state.history,
        currentChatId: state.currentChatId,
        settings: state.settings,
        isMcpMode: state.isMcpMode,
        lastActive: state.lastActive,
      }),
      onRehydrateStorage: () => (state) => {
        if (state) {
          const now = Date.now();
          if (
            state.messages &&
            state.messages.length > 0 &&
            now - state.lastActive > SESSION_TIMEOUT
          ) {
            const firstMsg =
              state.messages.find((m) => m.role === "user")?.content ||
              "Auto-archived Chat";
            const title =
              firstMsg.length > 30
                ? firstMsg.substring(0, 30) + "..."
                : firstMsg;
            const newItem: ChatHistoryItem = {
              id: uuidv4(),
              title: `(Archived) ${title}`,
              messages: [...state.messages],
              timestamp: new Date().toISOString(),
            };
            state.history = [newItem, ...state.history];
            state.messages = [];
            state.currentChatId = null;
            state.isRightPanelOpen = false;
            state.lastActive = now;
          }
        }
      },
    },
  ),
);
