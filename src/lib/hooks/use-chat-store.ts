"use client";

import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';
import { v4 as uuidv4 } from 'uuid';
import type { ChatMessage, ChatSettings, ChatRole } from '@/lib/types';
import { geminiChatInteraction } from '@/ai/flows/gemini-chat-interaction';
import { mcpServerToolIntegration } from '@/ai/flows/mcp-server-tool-integration';

interface ChatState {
  messages: ChatMessage[];
  historyForLLM: { role: 'user' | 'model'; content: string }[];
  settings: ChatSettings;
  isLoading: boolean;
  sendMessage: (text: string) => void;
  setSettings: (settings: ChatSettings) => void;
  addMessage: (message: ChatMessage) => void;
  clearMessages: () => void;
}

const defaultSettings: ChatSettings = {
  model: 'googleai/gemini-2.5-flash',
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

      clearMessages: () => set({ messages: [], historyForLLM: [] }),

      sendMessage: async (text) => {
        const { settings, historyForLLM } = get();
        set({ isLoading: true });

        const userMessage: ChatMessage = {
          id: uuidv4(),
          role: 'user',
          content: text,
        };
        set((state) => ({ messages: [...state.messages, userMessage] }));

        try {
          if (settings.mcpServers.length > 0) {
            // Use tool integration flow
            const toolResponse = await mcpServerToolIntegration({
              userMessage: text,
              mcpServerUrls: settings.mcpServers.map(s => s.url),
              modelName: settings.model,
              temperature: settings.temperature,
              maxOutputTokens: settings.maxTokens,
              history: historyForLLM,
            });

            // Add tool call visualization if any
            if (toolResponse.toolCalls && toolResponse.toolCalls.length > 0) {
                const toolCallMessage: ChatMessage = {
                    id: uuidv4(),
                    role: 'tool-output',
                    content: toolResponse.response,
                    toolCalls: toolResponse.toolCalls.map(tc => ({ name: tc.name, args: tc.input })),
                };
                set((state) => ({ messages: [...state.messages, toolCallMessage] }));
            } else {
                // Regular model response without tool usage
                 const modelMessage: ChatMessage = {
                    id: uuidv4(),
                    role: 'model',
                    content: toolResponse.response,
                };
                set((state) => ({ messages: [...state.messages, modelMessage] }));
            }
             
            // Update history
            set({ historyForLLM: [
                ...historyForLLM,
                { role: 'user', content: text },
                { role: 'model', content: toolResponse.response }
            ]});

          } else {
            // Use simple chat flow
            const chatResponse = await geminiChatInteraction({
              message: text,
              history: historyForLLM,
              modelName: settings.model,
              temperature: settings.temperature,
            });

            const modelMessage: ChatMessage = {
              id: uuidv4(),
              role: 'model',
              content: chatResponse.response,
            };
            set((state) => ({ messages: [...state.messages, modelMessage] }));
            set({ historyForLLM: chatResponse.newHistory });
          }
        } catch (error: any) {
          console.error("Error calling AI flow:", error);
          const errorMessageText = error.message || "Sorry, I encountered an unknown error. Please try again.";
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
