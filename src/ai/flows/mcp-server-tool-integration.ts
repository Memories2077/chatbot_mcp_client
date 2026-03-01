'use server';
/**
 * @fileOverview A Genkit flow for integrating dynamic MCP server tools with Gemini LLM.
 *
 * - mcpServerToolIntegration - A function that handles user queries by leveraging dynamically loaded tools from MCP servers.
 * - McpServerToolIntegrationInput - The input type for the mcpServerToolIntegration function.
 * - McpServerToolIntegrationOutput - The return type for the mcpServerToolIntegration function.
 */

import { ai } from '@/ai/genkit';
import { z } from 'genkit';
import { Tool } from 'genkit';

/**
 * Input schema for the MCP Server Tool Integration flow.
 * It includes the user's message, a list of MCP server URLs, and optional model configuration.
 */
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

/**
 * Output schema for the MCP Server Tool Integration flow.
 * It includes the LLM's response and details about any tool calls and their outputs.
 */
const McpServerToolIntegrationOutputSchema = z.object({
  response: z.string().describe('The LLM\'s response, incorporating tool outputs if any.'),
  toolCalls: z.array(z.object({
    name: z.string().describe('The name of the tool called.'),
    input: z.any().describe('The input parameters passed to the tool.'),
  })).optional().describe('Details of tools called by the LLM.'),
  toolOutputs: z.array(z.object({
    toolCall: z.object({
      name: z.string().describe('The name of the tool that was called.'),
      input: z.any().describe('The input parameters passed to the tool.'),
    }),
    output: z.any().describe('The output returned by the tool.'),
  })).optional().describe('Outputs from the tools called by the LLM.'),
});
export type McpServerToolIntegrationOutput = z.infer<typeof McpServerToolIntegrationOutputSchema>;

/**
 * Simulates loading tools from an MCP server URL.
 * In a real application, this would involve connecting to the MCP server
 * to discover its available tools, their schemas, and their execution endpoints.
 * For this example, it returns mock Genkit Tool definitions.
 * @param mcpUrl The URL of the MCP server.
 * @returns A promise that resolves to an array of Genkit Tool objects.
 */
async function loadMcpToolsFromUrl(mcpUrl: string): Promise<Tool<any, any, any>[]> {
  console.log(`Simulating loading tools from MCP server: ${mcpUrl}`);
  // In a real implementation, you'd make an HTTP request to `mcpUrl`
  // to get tool definitions (name, description, input schema) and
  // then create a Genkit Tool object. The tool's execute function
  // would then make a call back to the MCP server to perform the action.

  // For demonstration, let's return some mock tools based on the URL content.
  if (mcpUrl.includes('weather-service')) {
    return [
      ai.defineTool(
        {
          name: 'getCurrentWeather',
          description: 'Gets the current weather for a specified city.',
          inputSchema: z.object({
            city: z.string().describe('The name of the city.'),
          }),
          outputSchema: z.string(), // Simplified output for mock
        },
        async (input) => {
          console.log(`Mock: Calling getCurrentWeather for ${input.city} via ${mcpUrl}`);
          // Simulate API call to MCP server for weather
          if (input.city.toLowerCase() === 'london') {
            return 'It is sunny with a temperature of 20 degrees Celsius in London.';
          } else if (input.city.toLowerCase() === 'paris') {
            return 'It is cloudy with a temperature of 15 degrees Celsius in Paris.';
          } else if (input.city.toLowerCase() === 'new york') {
            return 'It is partly cloudy with a temperature of 25 degrees Celsius in New York.';
          }
          return `Could not find weather for ${input.city}.`;
        }
      ),
      ai.defineTool(
        {
          name: 'getForecast',
          description: 'Gets the weather forecast for a specified city and number of days (1-7).',
          inputSchema: z.object({
            city: z.string().describe('The name of the city.'),
            days: z.number().int().min(1).max(7).describe('The number of days for the forecast.'),
          }),
          outputSchema: z.string(),
        },
        async (input) => {
          console.log(`Mock: Calling getForecast for ${input.city} for ${input.days} days via ${mcpUrl}`);
          // Simulate API call to MCP server for forecast
          if (input.city.toLowerCase() === 'london') {
            return `Forecast for London for ${input.days} days: Expect scattered showers and mild temperatures.`;
          } else if (input.city.toLowerCase() === 'paris') {
            return `Forecast for Paris for ${input.days} days: Expect cool, cloudy weather.`;
          } else if (input.city.toLowerCase() === 'new york') {
            return `Forecast for New York for ${input.days} days: Expect warm and clear skies.`;
          }
          return `Could not get forecast for ${input.city}.`;
        }
      ),
    ];
  } else if (mcpUrl.includes('stock-service')) {
    return [
      ai.defineTool(
        {
          name: 'getStockPrice',
          description: 'Retrieves the current stock price for a given ticker symbol.',
          inputSchema: z.object({
            ticker: z.string().describe('The stock ticker symbol (e.g., GOOGL, AAPL).'),
          }),
          outputSchema: z.number(),
        },
        async (input) => {
          console.log(`Mock: Calling getStockPrice for ${input.ticker} via ${mcpUrl}`);
          // Simulate API call to MCP server for stock price
          switch (input.ticker.toUpperCase()) {
            case 'GOOGL':
              return 1700.50;
            case 'AAPL':
              return 180.25;
            case 'MSFT':
              return 450.10;
            default:
              return 0; // Not found
          }
        }
      ),
    ];
  }
  return []; // No tools for unknown MCP URL
}

/**
 * Defines a Genkit flow that integrates dynamically loaded tools from MCP servers.
 * It allows the LLM to use these tools to answer user queries that require external data or actions.
 */
const mcpServerToolIntegrationFlow = ai.defineFlow(
  {
    name: 'mcpServerToolIntegrationFlow',
    inputSchema: McpServerToolIntegrationInputSchema,
    outputSchema: McpServerToolIntegrationOutputSchema,
  },
  async (input) => {
    // Dynamically load tools from provided MCP server URLs
    let allTools: Tool<any, any, any>[] = [];
    for (const url of input.mcpServerUrls) {
      const tools = await loadMcpToolsFromUrl(url);
      allTools = allTools.concat(tools);
    }

    // Prepare history for the LLM
    const llmHistory = input.history?.map(entry => ({
      role: entry.role as 'user' | 'model',
      content: [{ text: entry.content }]
    })) || [];


    // Use the base model configured in src/ai/genkit.ts, or the one specified by the user
    const model = ai.model(input.modelName || 'googleai/gemini-2.5-flash');

    // Generate a response using the LLM, providing it with the dynamically loaded tools.
    const result = await ai.generate({
      model: model,
      prompt: input.userMessage,
      history: llmHistory,
      tools: allTools,
      config: {
        temperature: input.temperature,
        maxOutputTokens: input.maxOutputTokens,
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

    // Extract the textual response from the LLM.
    const responseContent = result.text;

    // Extract details about any tool calls made by the LLM for UI display.
    const toolCalls = result.toolCalls?.map(tc => ({
      name: tc.tool.name,
      input: tc.input,
    })) || [];

    // Extract details about the outputs of any tool calls for UI display.
    const toolOutputs = result.toolOutputs?.map(to => ({
      toolCall: {
        name: to.toolCall.tool.name,
        input: to.toolCall.input,
      },
      output: to.output,
    })) || [];

    return {
      response: responseContent,
      toolCalls,
      toolOutputs,
    };
  }
);

/**
 * Wrapper function to execute the MCP Server Tool Integration Genkit flow.
 * This function can be called directly from Next.js React code.
 * @param input The input for the flow, including user message, MCP server URLs, and optional model config.
 * @returns A promise that resolves to the LLM's response and tool interaction details.
 */
export async function mcpServerToolIntegration(input: McpServerToolIntegrationInput): Promise<McpServerToolIntegrationOutput> {
  return mcpServerToolIntegrationFlow(input);
}
