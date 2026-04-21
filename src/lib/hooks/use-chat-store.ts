"use client";

import { create } from "zustand";
import { persist, createJSONStorage } from "zustand/middleware";
import { v4 as uuidv4 } from "uuid";
import type { ChatMessage, ChatSettings, ChatHistoryItem } from "@/lib/types";
import { BACKEND_API, MODEL_CONFIG } from "@/lib/config";

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
          const historyForBackend = updatedMessages.map((msg) => ({
            role: msg.role === "model" ? "model" : "user",
            content: msg.content,
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
          let fullContent = "";
          let hasAddedAiMessage = false;

          while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            const chunk = decoder.decode(value, { stream: true });
            const lines = chunk.split("\n\n");

            for (const line of lines) {
              if (line.startsWith("data: ")) {
                const dataStr = line.replace("data: ", "").trim();
                
                if (dataStr === "[DONE]") {
                  break;
                }

                try {
                  const data = JSON.parse(dataStr);
                  if (data.content) {
                    fullContent += data.content;
                    
                    if (!hasAddedAiMessage) {
                      set((state) => ({
                        messages: [...state.messages, {
                          id: aiMessageId,
                          role: "model",
                          content: fullContent,
                          timestamp: new Date().toISOString(),
                        }],
                      }));
                      hasAddedAiMessage = true;
                    } else {
                      set((state) => ({
                        messages: state.messages.map((m) =>
                          m.id === aiMessageId ? { ...m, content: fullContent } : m
                        ),
                      }));
                    }
                  } else if (data.error) {
                    throw new Error(data.error);
                  }
                } catch (e) {
                  // Ignore partial parsing errors if the line is incomplete
                }
              }
            }
          }

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
            messages: [...state.messages.filter(m => m.id !== aiMessageId), errorMessage],
            lastActive: Date.now(),
          }));
        } finally {
          set({ isLoading: false });
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
        lastActive: state.lastActive,
      }),
      onRehydrateStorage: () => (state) => {
        if (state) {
          // Migration: if provider is metaclaw, reset to gemini
          // Use type casting since 'metaclaw' is no longer in the type definition
          if ((state.settings?.provider as string) === "metaclaw") {
            state.settings.provider = "gemini";
            state.settings.model = MODEL_CONFIG.gemini.defaultModel;
          }

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
