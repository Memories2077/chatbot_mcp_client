'use server';
/**
 * @fileOverview This file implements a LangChain flow for interactive chat with a Gemini LLM.
 *
 * - geminiChatInteraction - A function that handles a single turn of a chat conversation.
 * - ChatInteractionInput - The input type for the geminiChatInteraction function, including message, history, model, and temperature.
 * - ChatInteractionOutput - The return type for the geminiChatInteraction function, including the LLM's response and updated history.
 */

import { ChatGoogleGenerativeAI } from "@langchain/google-genai";
import { HumanMessage, AIMessage } from "@langchain/core/messages";
import { z } from 'zod';

const ChatInteractionInputSchema = z.object({
  message: z.string().describe('The current message from the user.'),
  history: z.array(
    z.object({ role: z.enum(['user', 'model']), content: z.string() })
  ).describe('The conversation history leading up to this turn.'),
  modelName: z.string().default('googleai/gemini-2.5-flash').describe('The name of the Gemini model to use.'),
  temperature: z.number().min(0).max(1).default(0.7).describe('The temperature for the LLM response generation.'),
});
export type ChatInteractionInput = z.infer<typeof ChatInteractionInputSchema>;

const ChatInteractionOutputSchema = z.object({
  response: z.string().describe('The LLM\'s response to the current message.'),
  newHistory: z.array(
    z.object({ role: z.enum(['user', 'model']), content: z.string() })
  ).describe('The updated conversation history including the new turn.'),
});
export type ChatInteractionOutput = z.infer<typeof ChatInteractionOutputSchema>;

export async function geminiChatInteraction(
  input: ChatInteractionInput
): Promise<ChatInteractionOutput> {
  const { message, history, modelName, temperature } = input;

  // Map the model name from settings to the name LangChain expects.
  let lcModelName = 'gemini-2.5-flash-latest';
  if (modelName === 'googleai/gemini-2.5-pro') {
    lcModelName = 'gemini-1.5-pro-latest';
  }

  try {
    const model = new ChatGoogleGenerativeAI({
      modelName: 'gemini-2.5-flash',
      temperature,
      apiKey: process.env.GEMINI_API_KEY,
    });

    const chatHistory = history.map(turn => {
      return turn.role === 'user' ? new HumanMessage(turn.content) : new AIMessage(turn.content);
    });

    const fullHistory = [...chatHistory, new HumanMessage(message)];

    const result = await model.invoke(fullHistory);

    const llmResponse = result.content as string;

    const newHistory: Array<{ role: 'user' | 'model', content: string }> = [
      ...history,
      { role: 'user', content: message },
      { role: 'model', content: llmResponse },
    ];

    return {
      response: llmResponse,
      newHistory: newHistory,
    };
  } catch (e: any) {
    console.error("LangChain Error:", e);
    // Re-throw a more user-friendly error.
    throw new Error(`AI model call failed: ${e.message}. This may be due to an invalid API key or network issues.`);
  }
}
