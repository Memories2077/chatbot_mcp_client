import { Client } from "@langchain/langgraph-sdk";
import { getLangGraphUrl } from "./config";

/**
 * Initialize LangGraph SDK Client
 */
export const createLangGraphClient = () => {
    return new Client({
        apiUrl: getLangGraphUrl(),
    });
};

/**
 * Assistant ID from langgraph.json
 */
export const ASSISTANT_ID = "agent";

/**
 * Interface for the message format expected by the Agent
 */
export interface LangGraphInput {
    messages: Array<{
        role: "user" | "assistant" | "system";
        content: string;
    }>;
}
