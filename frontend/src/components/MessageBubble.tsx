import type { Message } from "@/lib/types";

export function MessageBubble({ message }: { message: Message }) {
  const isUser = message.role === "user";

  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
      <div
        className={`max-w-2xl whitespace-pre-wrap rounded-2xl px-4 py-2.5 text-sm leading-relaxed ${
          isUser ? "bg-indigo-600 text-white" : "bg-zinc-800 text-zinc-100"
        }`}
      >
        {message.input_type === "audio" && (
          <span className="mr-1 text-xs opacity-70">🎙️</span>
        )}
        {message.content}
      </div>
    </div>
  );
}
