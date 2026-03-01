'use server';
/**
 * @fileOverview A LangChain flow for integrating dynamic MCP server tools with Gemini LLM.
 *
 * - mcpServerToolIntegration - A function that handles user queries by leveraging dynamically loaded tools from MCP servers.
 * - McpServerToolIntegrationInput - The input type for the mcpServerToolIntegration function.
 * - McpServerToolIntegrationOutput - The return type for the mcpServerToolIntegration function.
 */

import { ChatGoogleGenerativeAI } from "@langchain/google-genai";
import { HumanMessage, AIMessage, ToolMessage } from "@langchain/core/messages";
import { DynamicTool } from "langchain/tools";
import { z } from 'zod';

const McpServerToolIntegrationInputSchema = z.object({
  userMessage: z.string().describe('The user\'s message to the LLM.'),
  mcpServerUrls: z.array(z.string().url()).describe('An array of URLs for MCP servers to integrate as tools.'),
  modelName: z.string().optional().describe('Optional: The name of the Gemini model to use (e.g., "googleai/gemini-2.5-flash"). Defaults to configured model.'),
  temperature: z.number().min(0).max(1).default(0.7).optional().describe('Optional: Controls the randomness of the output. Lower values mean less random.'),
  maxOutputTokens: z.number().int().positive().optional().describe('Optional: The maximum number of tokens to generate in the response.'),
  history: z.array(z.object({
    role: z.enum(['user', 'model']),
    content: z.string(),
  })).optional().describe('Optional: Chat history to provide context to the LLM. Each entry is a simple text message.'),
});
export type McpServerToolIntegrationInput = z.infer<typeof McpServerToolIntegrationInputSchema>;

const McpServerToolIntegrationOutputSchema = z.object({
    response: z.string().describe('The LLM\'s response, incorporating tool outputs if any.'),
    toolCalls: z.array(z.object({
      name: z.string().describe('The name of the tool called.'),
      input: z.any().describe('The input parameters passed to the tool.'),
    })).optional().describe('Details of tools called by the LLM.'),
    toolOutputs: z.array(z.object({
      name: z.string(),
      input: z.any(),
      output: z.any(),
    })).optional().describe('Outputs from the tools called by the LLM.'),
});
export type McpServerToolIntegrationOutput = z.infer<typeof McpServerToolIntegrationOutputSchema>;


async function loadMcpToolsFromUrl(mcpUrl: string): Promise<DynamicTool[]> {
  console.log(`Simulating loading tools from MCP server: ${mcpUrl}`);
  // In a real implementation, you'd make an HTTP request to `mcpUrl`
  // to get tool definitions and create Langchain DynamicTool objects.

  if (mcpUrl.includes('weather-service')) {
    return [
      new DynamicTool({
        name: 'getCurrentWeather',
        description: 'Gets the current weather for a specified city.',
        func: async (input: { city: string }) => {
            const { city } = input;
            console.log(`Mock: Calling getCurrentWeather for ${city} via ${mcpUrl}`);
            if (city.toLowerCase() === 'london') {
                return 'It is sunny with a temperature of 20 degrees Celsius in London.';
            } else if (city.toLowerCase() === 'paris') {
                return 'It is cloudy with a temperature of 15 degrees Celsius in Paris.';
            } else if (city.toLowerCase() === 'new york') {
                return 'It is partly cloudy with a temperature of 25 degrees Celsius in New York.';
            }
            return `Could not find weather for ${city}.`;
        },
        schema: z.object({ city: z.string().describe('The name of the city.') }),
      }),
      new DynamicTool({
          name: 'getForecast',
          description: 'Gets the weather forecast for a specified city and number of days (1-7).',
          func: async(input: {city: string, days: number}) => {
              console.log(`Mock: Calling getForecast for ${input.city} for ${input.days} days via ${mcpUrl}`);
              if (input.city.toLowerCase() === 'london') {
                return `Forecast for London for ${input.days} days: Expect scattered showers and mild temperatures.`;
              } else if (input.city.toLowerCase() === 'paris') {
                return `Forecast for Paris for ${input.days} days: Expect cool, cloudy weather.`;
              } else if (input.city.toLowerCase() === 'new york') {
                return `Forecast for New York for ${input.days} days: Expect warm and clear skies.`;
              }
              return `Could not get forecast for ${input.city}.`;
          },
          schema: z.object({
            city: z.string().describe('The name of the city.'),
            days: z.number().int().min(1).max(7).describe('The number of days for the forecast.'),
          }),
      }),
    ];
  } else if (mcpUrl.includes('stock-service')) {
    return [
      new DynamicTool({
        name: 'getStockPrice',
        description: 'Retrieves the current stock price for a given ticker symbol.',
        func: async (input: { ticker: string }) => {
            const { ticker } = input;
            console.log(`Mock: Calling getStockPrice for ${ticker} via ${mcpUrl}`);
            switch (ticker.toUpperCase()) {
                case 'GOOGL': return 1700.50;
                case 'AAPL': return 180.25;
                case 'MSFT': return 450.10;
                default: return 0;
            }
        },
        schema: z.object({ ticker: z.string().describe('The stock ticker symbol (e.g., GOOGL, AAPL).') }),
      }),
    ];
  }
  return [];
}


export async function mcpServerToolIntegration(input: McpServerToolIntegrationInput): Promise<McpServerToolIntegrationOutput> {
    const { userMessage, mcpServerUrls, modelName, temperature, maxOutputTokens, history } = input;
    
    try {
        let allTools: DynamicTool[] = [];
        for (const url of mcpServerUrls) {
            const tools = await loadMcpToolsFromUrl(url);
            allTools = allTools.concat(tools);
        }

        let lcModelName = 'gemini-1.5-flash-latest';
        if (modelName === 'googleai/gemini-2.5-pro') {
            lcModelName = 'gemini-1.5-pro-latest';
        }

        const model = new ChatGoogleGenerativeAI({
            modelName: lcModelName,
            temperature,
            maxOutputTokens,
            apiKey: process.env.GOOGLE_API_KEY,
        });

        const modelWithTools = model.bindTools(allTools);

        const chatHistory = (history || []).map(turn => {
            return turn.role === 'user' ? new HumanMessage(turn.content) : new AIMessage(turn.content);
        });

        const fullHistory = [...chatHistory, new HumanMessage(userMessage)];

        const result = await modelWithTools.invoke(fullHistory);

        const toolCallsForUI: { name: string; input: any; }[] = [];
        const toolOutputsForLLM: ToolMessage[] = [];
        const toolOutputsForUI: { name: string; input: any; output: any }[] = [];


        if (result.tool_calls) {
            for (const toolCall of result.tool_calls) {
                const tool = allTools.find(t => t.name === toolCall.name);
                if (tool) {
                    toolCallsForUI.push({ name: tool.name, input: toolCall.args });
                    const output = await tool.invoke(toolCall.args);
                    toolOutputsForUI.push({ name: tool.name, input: toolCall.args, output });
                    toolOutputsForLLM.push(new ToolMessage({ tool_call_id: toolCall.id!, content: JSON.stringify(output)}));
                }
            }
        }

        let finalResponse = result.content as string;
        if (toolOutputsForLLM.length > 0) {
            fullHistory.push(...toolOutputsForLLM);
            const finalResult = await modelWithTools.invoke(fullHistory);
            finalResponse = finalResult.content as string;
        }

        return {
            response: finalResponse,
            toolCalls: toolCallsForUI,
            toolOutputs: toolOutputsForUI,
        };
    } catch (e: any) {
        console.error("LangChain Error:", e);
        throw new Error(`AI model call failed: ${e.message}. This may be due to an invalid API key or network issues.`);
    }
}
