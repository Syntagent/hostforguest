"use client";

import { cn } from "@/lib/utils";
import type { AccommodationAgentMessage } from "@/lib/api";

type AgentMessageListProps = {
  messages: AccommodationAgentMessage[];
};

export function AgentMessageList({ messages }: AgentMessageListProps) {
  return (
    <div className="max-h-[360px] space-y-3 overflow-y-auto rounded-2xl border border-border bg-gray-50 p-3">
      {messages.map((message, index) => (
        <div
          key={`${message.role}-${index}`}
          className={cn(
            "rounded-2xl px-3 py-2 text-sm leading-6 shadow-sm",
            message.role === "user"
              ? "ml-8 bg-blue-600 text-white"
              : "mr-8 border border-border bg-white text-gray-800",
          )}
        >
          {message.content}
        </div>
      ))}
    </div>
  );
}

