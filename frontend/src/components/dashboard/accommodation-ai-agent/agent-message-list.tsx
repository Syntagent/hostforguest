"use client";

import { cn } from "@/lib/utils";
import type { AccommodationAgentMessage } from "@/lib/api";

type AgentMessageListProps = {
  messages: AccommodationAgentMessage[];
};

export function AgentMessageList({ messages }: AgentMessageListProps) {
  return (
    <div className="max-h-[150px] space-y-2 overflow-y-auto sm:max-h-[280px]">
      {messages.map((message, index) => (
        <div
          key={`${message.role}-${index}`}
          className={cn(
            "max-w-[92%] rounded-2xl px-3 py-2 text-sm leading-6 sm:max-w-[88%]",
            message.role === "user"
              ? "ml-auto bg-blue-600 text-white shadow-sm"
              : "border border-blue-100 bg-white text-gray-800 shadow-sm",
          )}
        >
          {message.content}
        </div>
      ))}
    </div>
  );
}

