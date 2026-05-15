"use client";

import { create } from "zustand";
import { persist, createJSONStorage } from "zustand/middleware";
import { v4 as uuidv4 } from "uuid";
import type { ChatMessage, ChatSettings, ChatHistoryItem } from "@/lib/types";
import { BACKEND_API, MODEL_CONFIG } from "@/lib/config";

// Simple error logger - can be replaced with a proper logging service
const logError = (...args: any[]) => {
  if (process.env.NODE_ENV !== "production") {
    console.error(...args);
  }
  // In production, integrate with your monitoring service (e.g., Sentry)
};

interface ChatState {
  messages: ChatMessage[];
  history: ChatHistoryItem[];
  currentChatId: string | null;
  settings: ChatSettings;
  isLoading: boolean;
  isRightPanelOpen: boolean;
  lastActive: number;
  toggleRightPanel: () => void;
  setRightPanelOpen: (open: boolean) => void;
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

const MCP_BUILD_TRANSCRIPT_PATTERNS = [
  /DELEGATE_TO_EXAMINER:/i,
  /DELEGATE_TO_GENERATOR:/i,
  /ENRICHED_CONTEXT\s*\(RAG\):/i,
  /MCP Server (?:built|created) successfully/i,
];

const toBackendMessageContent = (message: ChatMessage): string => {
  if (message.role !== "model") {
    return message.content;
  }

  if (MCP_BUILD_TRANSCRIPT_PATTERNS.some((pattern) => pattern.test(message.content))) {
    return "An MCP server build was completed successfully in the previous assistant turn. The detailed build transcript is UI-only and should not be repeated.";
  }

  return message.content;
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
      lastActive: Date.now(),

      toggleRightPanel: () =>
        set((state) => ({ isRightPanelOpen: !state.isRightPanelOpen })),
      setRightPanelOpen: (open: boolean) => set({ isRightPanelOpen: open }),

      setSettings: (newSettings) => {
        const currentSettings = get().settings;
        const updatedSettings = { ...currentSettings, ...newSettings };
        if (
          newSettings.provider &&
          newSettings.provider !== currentSettings.provider
        ) {
          updatedSettings.model =
            MODEL_CONFIG[newSettings.provider as keyof typeof MODEL_CONFIG]
              ?.defaultModel || updatedSettings.model;
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
          currentChatId: state.currentChatId === id ? null : state.currentChatId,
          messages: state.currentChatId === id ? [] : state.messages,
        }));
      },

      sendMessage: async (text, overrideSettings) => {
        const {
          messages,
          settings: currentSettings,
          currentChatId,
          persistCurrentChat,
        } = get();

        const settings = overrideSettings || currentSettings;

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

        const aiMessageId = uuidv4();

        try {
          const historyForBackend = updatedMessages
            .filter((msg) => msg.role === "user" || msg.role === "model")
            .map((msg) => ({
              role: msg.role === "model" ? "model" : "user",
              content: toBackendMessageContent(msg),
            }));

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

          if (!response.body) {
            throw new Error("No response body");
          }

          const reader = response.body.getReader();
          const decoder = new TextDecoder();
          const bufferRef = { current: "" }; // Mutable buffer for incomplete SSE frames
          let fullContent = "";
          let hasAddedAiMessage = false;
          let streamComplete = false;

          const upsertAiMessage = (content: string) => {
            if (!hasAddedAiMessage) {
              set((state) => ({
                messages: [
                  ...state.messages,
                  {
                    id: aiMessageId,
                    role: "model",
                    content,
                    timestamp: new Date().toISOString(),
                  },
                ],
              }));
              hasAddedAiMessage = true;
            } else {
              set((state) => ({
                messages: state.messages.map((m) =>
                  m.id === aiMessageId ? { ...m, content } : m,
                ),
              }));
            }
          };

          const handleSsePayload = (dataStr: string) => {
            if (dataStr === "[DONE]") {
              streamComplete = true;
              return;
            }

            const data = JSON.parse(dataStr);
            const eventType = data.type as string | undefined;

            if (eventType === "done") {
              streamComplete = true;
              return;
            }

            if (eventType === "error" || data.error) {
              throw new Error(data.error || "Backend stream error");
            }

            if (eventType === "mcp_build_complete") {
              fullContent += "\n\n✅ MCP Server built successfully!\n\n";
              upsertAiMessage(fullContent);
              return;
            }

            const content =
              eventType === "status" ? data.message : data.content;

            if (typeof content === "string" && content.length > 0) {
              fullContent += content;
              upsertAiMessage(fullContent);
            }
          };

          while (true) {
            const { done, value } = await reader.read();

            // Decode chunk and append to buffer
            const chunk = decoder.decode(value, { stream: true });
            bufferRef.current += chunk;

            // Split by double newline (SSE delimiter)
            const lines = bufferRef.current.split("\n\n");
            // Keep the last incomplete line in the buffer
            bufferRef.current = lines.pop() || "";

            for (const line of lines) {
              const dataLines = line
                .split("\n")
                .filter((entry) => entry.startsWith("data:"))
                .map((entry) => entry.replace(/^data:\s?/, ""));

              for (const dataStr of dataLines) {
                handleSsePayload(dataStr.trim());
                if (streamComplete) break;
              }

              if (streamComplete) break;
            }

            if (done || streamComplete) break;
          }

          // Flush any remaining data in buffer after stream ends
          if (bufferRef.current && bufferRef.current.startsWith("data:")) {
            const dataLines = bufferRef.current
              .split("\n")
              .filter((entry) => entry.startsWith("data:"))
              .map((entry) => entry.replace(/^data:\s?/, ""));

            for (const dataStr of dataLines) {
              handleSsePayload(dataStr.trim());
              if (streamComplete) break;
            }
          }
        } catch (error: unknown) {
          logError("Error calling AI flow:", error);
          const errorMessage: ChatMessage = {
            id: uuidv4(),
            role: "system",
            content:
              error instanceof Error
                ? error.message
                : "Failed to connect to backend.",
            timestamp: new Date().toISOString(),
          };
          set((state) => ({
            messages: [
              ...state.messages.filter((m) => m.id !== aiMessageId),
              errorMessage,
            ],
            lastActive: Date.now(),
          }));
        } finally {
          persistCurrentChat();
          set({ isLoading: false });
        }
      },
    }),
    {
      name: "gemini-insight-link-storage",
      storage: createJSONStorage(() => localStorage),
      partialize: (state) => ({
        messages: state.messages,
        history: state.history,
        currentChatId: state.currentChatId,
        settings: state.settings,
        lastActive: state.lastActive,
      }),
      onRehydrateStorage: () => (state) => {
        if (state) {
          // Migration: ensure provider is valid
          const validProviders = ["gemini", "groq"];
          const provider = state.settings?.provider;
          if (!provider || !validProviders.includes(provider)) {
            state.settings.provider = "gemini";
            state.settings.model = MODEL_CONFIG.gemini.defaultModel;
          }

          const now = Date.now();
          if (
            state.currentChatId &&
            (!state.messages || state.messages.length === 0)
          ) {
            state.currentChatId = null;
          }

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
            const archivedItem: ChatHistoryItem = {
              id: uuidv4(),
              title: `(Archived) ${title}`,
              messages: [...state.messages],
              timestamp: new Date().toISOString(),
            };

            if (state.currentChatId) {
              const existingIndex = state.history.findIndex(
                (item) => item.id === state.currentChatId,
              );
              if (existingIndex !== -1) {
                archivedItem.id = state.currentChatId;
                state.history.splice(existingIndex, 1);
              }
            }

            state.history = [archivedItem, ...state.history];
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
