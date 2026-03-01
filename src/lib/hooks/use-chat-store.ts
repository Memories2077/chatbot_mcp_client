"use client";

import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';
import { v4 as uuidv4 } from 'uuid';
import type { ChatMessage, ChatSettings } from '@/lib/types';

interface ChatState {
  messages: ChatMessage[];
  historyForLLM: { role: 'user' | 'model'; content: string }[];
  settings: ChatSettings;
  isLoading: boolean;
  sendMessage: (text: string, settings?: ChatSettings) => void;
  setSettings: (settings: ChatSettings) => void;
  addMessage: (message: ChatMessage) => void;
  clearMessages: () => void;
}

const defaultSettings: ChatSettings = {
  model: 'gemini-2.0-flash',
  temperature: 0.7,
  maxTokens: 2048,
  mcpServers: [],
};

export const useChatStore = create<ChatState>()(
  persist(
    (set, get) => ({
      messages: [],
      historyForLLM: [],
      settings: defaultSettings,
      isLoading: false,

      setSettings: (settings) => set({ settings }),
      
      addMessage: (message) => set((state) => ({ messages: [...state.messages, message] })),

      clearMessages: () => {
        console.log("Clearing all messages and LLM history.");
        set({ messages: [], historyForLLM: [] });
      },

      sendMessage: async (text, settings) => {
        const { historyForLLM } = get();
        set({ isLoading: true });

        const userMessage: ChatMessage = {
          id: uuidv4(),
          role: 'user',
          content: text,
        };
        set((state) => ({ messages: [...state.messages, userMessage] }));

        const newHistory = [...historyForLLM, { role: 'user' as const, content: text }];

        try {
          const response = await fetch('http://100.78.98.117:8000/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
              messages: newHistory,
              model: settings?.model,
              temperature: settings?.temperature,
              mcpServers: settings?.mcpServers.map(s => s.url)
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
          };
          set((state) => ({ 
            messages: [...state.messages, modelMessage],
            historyForLLM: [...newHistory, { role: 'model' as const, content: data.response }]
          }));
          
        } catch (error: any) {
          console.error("Error calling AI flow:", error);
          const errorMessageText = error.message || "Sorry, I encountered an unknown error connecting to the Python backend. Make sure it's running on http://100.78.98.117:8000.";
          const errorMessage: ChatMessage = {
            id: uuidv4(),
            role: 'system',
            content: errorMessageText,
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
    }
  )
);
