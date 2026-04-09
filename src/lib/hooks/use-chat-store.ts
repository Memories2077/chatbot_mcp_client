"use client";

import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';
import { v4 as uuidv4 } from 'uuid';
import type { ChatMessage, ChatSettings, ChatHistoryItem } from '@/lib/types';
import { BACKEND_API, MODEL_CONFIG } from '@/lib/config';

interface ChatState {
  messages: ChatMessage[];
  history: ChatHistoryItem[];
  settings: ChatSettings;
  isLoading: boolean;
  isRightPanelOpen: boolean;
  lastActive: number;
  toggleRightPanel: () => void;
  sendMessage: (text: string, settings?: ChatSettings) => void;
  setSettings: (settings: Partial<ChatSettings>) => void;
  addMessage: (message: ChatMessage) => void;
  clearMessages: () => void;
  loadHistory: (id: string) => void;
  deleteHistory: (id: string) => void;
}

const SESSION_TIMEOUT = 1000 * 60 * 60; // 1 hour

const defaultSettings: ChatSettings = {
  provider: 'gemini',
  model: 'gemini-2.5-flash',
  temperature: 0.7,
  maxTokens: 2048,
  mcpServers: [],
};

export const useChatStore = create<ChatState>()(
  persist(
    (set, get) => ({
      messages: [],
      history: [],
      settings: defaultSettings,
      isLoading: false,
      isRightPanelOpen: true,
      lastActive: Date.now(),

      toggleRightPanel: () => set((state) => ({ isRightPanelOpen: !state.isRightPanelOpen })),

      setSettings: (newSettings) => {
        const currentSettings = get().settings;
        const updatedSettings = { ...currentSettings, ...newSettings };
        if (newSettings.provider && newSettings.provider !== currentSettings.provider) {
          updatedSettings.model = MODEL_CONFIG[newSettings.provider].defaultModel;
        }
        set({ settings: updatedSettings, lastActive: Date.now() });
      },

      addMessage: (message) => set((state) => ({ 
        messages: [...state.messages, message],
        lastActive: Date.now()
      })),

      clearMessages: () => {
        const { messages, history } = get();
        if (messages.length > 0) {
          // Create a title from the first message
          const firstMsg = messages.find(m => m.role === 'user')?.content || "Untitled Chat";
          const title = firstMsg.length > 30 ? firstMsg.substring(0, 30) + "..." : firstMsg;
          
          const newItem: ChatHistoryItem = {
            id: uuidv4(),
            title,
            messages: [...messages],
            timestamp: new Date().toISOString()
          };
          set({ history: [newItem, ...history], messages: [], lastActive: Date.now() });
        } else {
          set({ messages: [], lastActive: Date.now() });
        }
      },

      loadHistory: (id: string) => {
        const { history } = get();
        const item = history.find(h => h.id === id);
        if (item) {
          set({ messages: [...item.messages], lastActive: Date.now() });
        }
      },

      deleteHistory: (id: string) => {
        set((state) => ({
          history: state.history.filter(h => h.id !== id)
        }));
      },

      sendMessage: async (text, overrideSettings) => {
        const { messages, settings: currentSettings } = get();
        const settings = overrideSettings || currentSettings;
        set({ isLoading: true, lastActive: Date.now() });

        const now = new Date().toISOString();
        const userMessage: ChatMessage = {
          id: uuidv4(),
          role: 'user',
          content: text,
          timestamp: now,
        };

        const updatedMessages = [...messages, userMessage];
        set({ messages: updatedMessages });

        const historyForBackend = updatedMessages.map((msg) => ({
          role: msg.role === 'model' ? 'model' : 'user',
          content: msg.content
        }));

        try {
          const response = await fetch(BACKEND_API.chat(), {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              messages: historyForBackend,
              provider: settings?.provider,
              model: settings?.model,
              temperature: settings?.temperature,
              mcpServers: settings?.mcpServers?.map(s => s.url) || []
            })
          });

          if (!response.ok) {
            throw new Error(`Backend error: ${response.statusText}`);
          }

          const data = await response.json();

          const modelMessage: ChatMessage = {
            id: uuidv4(),
            role: 'model',
            content: data.response,
            timestamp: new Date().toISOString(),
          };
          set((state) => ({ 
            messages: [...state.messages, modelMessage],
            lastActive: Date.now()
          }));
          
        } catch (error: any) {
          console.error("Error calling AI flow:", error);
          const errorMessage: ChatMessage = {
            id: uuidv4(),
            role: 'system',
            content: error.message || "Failed to connect to backend.",
            timestamp: new Date().toISOString(),
          };
          set((state) => ({ messages: [...state.messages, errorMessage], lastActive: Date.now() }));
        } finally {
          set({ isLoading: false });
        }
      },
    }),
    {
      name: 'gemini-insight-link-storage',
      storage: createJSONStorage(() => localStorage),
      partialize: (state) => ({ 
        history: state.history,
        settings: state.settings,
        isRightPanelOpen: state.isRightPanelOpen,
        lastActive: state.lastActive
      }),
      onRehydrateStorage: () => (state) => {
        if (state) {
          const now = Date.now();
          if (state.messages && state.messages.length > 0 && (now - state.lastActive > SESSION_TIMEOUT)) {
            // Auto-archive old session before clearing
            const firstMsg = state.messages.find(m => m.role === 'user')?.content || "Auto-archived Chat";
            const title = firstMsg.length > 30 ? firstMsg.substring(0, 30) + "..." : firstMsg;
            const newItem: ChatHistoryItem = {
              id: uuidv4(),
              title: `(Archived) ${title}`,
              messages: [...state.messages],
              timestamp: new Date().toISOString()
            };
            state.history = [newItem, ...state.history];
            state.messages = [];
            state.lastActive = now;
          }
        }
      }
    }
  )
);
