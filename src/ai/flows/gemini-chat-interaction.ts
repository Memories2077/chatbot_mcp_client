'use server';
/**
 * @fileOverview This file implements a Genkit flow for interactive chat with a Gemini LLM.
 *
 * - geminiChatInteraction - A function that handles a single turn of a chat conversation.
 * - ChatInteractionInput - The input type for the geminiChatInteraction function, including message, history, model, and temperature.
 * - ChatInteractionOutput - The return type for the geminiChatInteraction function, including the LLM's response and updated history.
 */

import { ai } from '@/ai/genkit';
import { z } from 'genkit';

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

const geminiChatInteractionFlow = ai.defineFlow(
  {
    name: 'geminiChatInteractionFlow',
    inputSchema: ChatInteractionInputSchema,
    outputSchema: ChatInteractionOutputSchema,
  },
  async (input) => {
    const { message, history, modelName, temperature } = input;

    // Convert history to the format expected by Genkit's `history` option
    const llmHistory = history.map(turn => ({
      role: turn.role as 'user' | 'model',
      content: [{ text: turn.content }]
    }));

    // Ensure the model name has the 'googleai/' prefix to avoid errors with old stored settings.
    const fullModelName = modelName.startsWith('googleai/') ? modelName : `googleai/${modelName}`;

    const chat = ai.model(fullModelName).startChat({
      history: llmHistory,
      config: {
        temperature: temperature,
        safetySettings: [
            {
                category: 'HARM_CATEGORY_HATE_SPEECH',
                threshold: 'BLOCK_NONE',
            },
            {
                category: 'HARM_CATEGORY_DANGEROUS_CONTENT',
                threshold: 'BLOCK_NONE',
            },
            {
                category: 'HARM_CATEGORY_HARASSMENT',
                threshold: 'BLOCK_NONE',
            },
            {
                category: 'HARM_CATEGORY_SEXUALLY_EXPLICIT',
                threshold: 'BLOCK_NONE',
            },
        ]
      },
    });

    const response = await chat.sendMessage(message);

    if (!response.output) {
      // This error is thrown if the LLM response is blocked or empty.
      // This could be due to safety settings, or an issue with the API key.
      throw new Error('LLM did not return a response. This may be due to safety settings or an invalid API key.');
    }

    const llmResponse = response.text;

    // Update history with the user's message and the LLM's response
    const newHistory: Array<{ role: 'user' | 'model', content: string }> = [
      ...history,
      { role: 'user', content: message },
      { role: 'model', content: llmResponse },
    ];

    return {
      response: llmResponse,
      newHistory: newHistory,
    };
  }
);

export async function geminiChatInteraction(
  input: ChatInteractionInput
): Promise<ChatInteractionOutput> {
  return geminiChatInteractionFlow(input);
}
