"use client";

import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';
import { v4 as uuidv4 } from 'uuid';
import type { ChatMessage, ChatSettings } from '@/lib/types';
import { BACKEND_API, MODEL_CONFIG } from '@/lib/config';

interface ChatState {
  messages: ChatMessage[];
  settings: ChatSettings;
  isLoading: boolean;
  isRightPanelOpen: boolean;
  toggleRightPanel: () => void;
  sendMessage: (text: string, settings?: ChatSettings) => void;
  setSettings: (settings: Partial<ChatSettings>) => void;
  addMessage: (message: ChatMessage) => void;
  clearMessages: () => void;
}

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
      settings: defaultSettings,
      isLoading: false,
      isRightPanelOpen: true,

      toggleRightPanel: () => set((state) => ({ isRightPanelOpen: !state.isRightPanelOpen })),

      setSettings: (newSettings) => {
        const currentSettings = get().settings;
        const updatedSettings = { ...currentSettings, ...newSettings };

        // If provider changed, update model to the default for that provider
        if (newSettings.provider && newSettings.provider !== currentSettings.provider) {
          updatedSettings.model = MODEL_CONFIG[newSettings.provider].defaultModel;
        }
        
        set({ settings: updatedSettings });
      },
      
      addMessage: (message) => set((state) => ({ messages: [...state.messages, message] })),

      clearMessages: () => {
        console.log("Clearing all messages.");
        set({ messages: [] });
      },

      sendMessage: async (text, overrideSettings) => {
        const { messages, settings: currentSettings } = get();
        const settings = overrideSettings || currentSettings;
        set({ isLoading: true });

        const now = new Date().toISOString();
        const userMessage: ChatMessage = {
          id: uuidv4(),
          role: 'user',
          content: text,
          timestamp: now,
        };

        const updatedMessages = [...messages, userMessage];
        set({ messages: updatedMessages });

        // Transform messages for LLM with Index and Timestamp
        const historyForBackend = updatedMessages.map((msg, index) => ({
          role: msg.role === 'model' ? 'model' : 'user',
          content: `[Turn ${index}][${msg.timestamp}] ${msg.content}`
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
            messages: [...state.messages, modelMessage]
          }));
          
        } catch (error: any) {
          console.error("Error calling AI flow:", error);
          const backendUrl = BACKEND_API.chat();
          const errorMessageText = error.message || `Sorry, I encountered an unknown error connecting to the backend at ${backendUrl}. Make sure it's running.`;
          const errorMessage: ChatMessage = {
            id: uuidv4(),
            role: 'system',
            content: errorMessageText,
            timestamp: new Date().toISOString(),
          };
          set((state) => ({ messages: [...state.messages, errorMessage] }));
        } finally {
          set({ isLoading: false });
        }
      },
    }),
    {
      name: 'gemini-insight-link-storage',
      storage: createJSONStorage(() => localStorage),
      onRehydrateStorage: () => (state) => {
        if (state) {
          // On hydration, ensure the settings are valid, otherwise reset.
          const provider = state.settings.provider;
          if (!provider || !MODEL_CONFIG[provider]) {
            state.settings = defaultSettings;
            return;
          }
          const model = state.settings.model;
          if (!MODEL_CONFIG[provider].models.includes(model)) {
            state.settings.model = MODEL_CONFIG[provider].defaultModel;
          }
        }
      }
    }
  )
);
