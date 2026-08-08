"use client";

import { useEffect, useRef, useState } from "react";
import { useParams } from "next/navigation";

import { MessageBubble } from "@/components/MessageBubble";
import { MessageInput } from "@/components/MessageInput";
import { PriorityBadge } from "@/components/PriorityBadge";
import { api, ApiError } from "@/lib/api";
import type { ExecutedAction, Message, PriorityLevel } from "@/lib/types";

export default function ChatConversationPage() {
  const params = useParams<{ conversationId: string }>();
  const conversationId = params.conversationId;

  const [messages, setMessages] = useState<Message[]>([]);
  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [lastActions, setLastActions] = useState<ExecutedAction[]>([]);
  const [lastPriority, setLastPriority] = useState<PriorityLevel | null>(null);
  const bottomRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    let cancelled = false;
    // Reinicio intencional de estado de carga al cambiar de conversación.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    setLoading(true);
     
    setError(null);
    api
      .listMessages(conversationId)
      .then((data) => {
        if (!cancelled) setMessages(data);
      })
      .catch(() => {
        if (!cancelled) setError("No se pudo cargar la conversación");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [conversationId]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  async function handleSend(content: string, inputType: "texto" | "audio") {
    setSending(true);
    setError(null);
    try {
      const response = await api.sendMessage(conversationId, content, inputType);
      setMessages((prev) => [...prev, response.user_message, response.assistant_message]);
      setLastActions(response.executed_actions);
      setLastPriority(response.priority);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo enviar el mensaje");
      throw err;
    } finally {
      setSending(false);
    }
  }

  return (
    <div className="flex flex-1 flex-col overflow-hidden">
      <div className="flex-1 overflow-y-auto px-4 py-6">
        {loading && <p className="text-center text-sm text-zinc-500">Cargando conversación…</p>}
        {!loading && messages.length === 0 && (
          <p className="text-center text-sm text-zinc-500">
            Escribí o hablá para empezar. El asistente va a recordar, priorizar y actuar por vos.
          </p>
        )}
        <div className="mx-auto flex max-w-3xl flex-col gap-3">
          {messages.map((message) => (
            <MessageBubble key={message.id} message={message} />
          ))}
        </div>

        {lastActions.length > 0 && (
          <div className="mx-auto mt-4 max-w-3xl space-y-1 rounded-xl border border-zinc-800 bg-zinc-900 p-3 text-xs text-zinc-400">
            <p className="flex items-center gap-1 font-medium text-zinc-300">
              {lastPriority && <PriorityBadge priority={lastPriority} />}
              Acciones realizadas
            </p>
            <ul className="list-inside list-disc">
              {lastActions.map((action, index) => (
                <li key={index}>
                  {action.entity_type}: {action.title}
                </li>
              ))}
            </ul>
          </div>
        )}

        {error && <p className="mx-auto mt-4 max-w-3xl text-sm text-red-400">{error}</p>}
        <div ref={bottomRef} />
      </div>

      <MessageInput onSend={handleSend} disabled={sending} />
    </div>
  );
}
