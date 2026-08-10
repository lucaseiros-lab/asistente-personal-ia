"use client";

import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { api } from "@/lib/api";
import { useAuthStore } from "@/lib/auth-store";
import type { Conversation } from "@/lib/types";

export function Sidebar() {
  const router = useRouter();
  const params = useParams<{ conversationId?: string }>();
  const logout = useAuthStore((s) => s.logout);
  const user = useAuthStore((s) => s.user);

  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [loading, setLoading] = useState(true);

  async function loadConversations() {
    try {
      const data = await api.listConversations();
      setConversations(data);
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void loadConversations();
    // se recarga la lista cada vez que cambia la conversación activa
     
  }, [params?.conversationId]);

  async function handleNewConversation() {
    const conversation = await api.createConversation();
    setConversations((prev) => [conversation, ...prev]);
    router.push(`/chat/${conversation.id}`);
  }

  async function handleLogout() {
    await api.logout();
    logout();
    router.replace("/login");
  }

  return (
    <aside className="flex h-full w-72 flex-col border-r border-zinc-800 bg-zinc-950">
      <div className="p-3">
        <button
          onClick={handleNewConversation}
          className="flex w-full items-center justify-center gap-2 rounded-lg border border-zinc-700 px-3 py-2 text-sm text-zinc-200 transition hover:bg-zinc-800"
        >
          + Nueva conversación
        </button>
      </div>

      <nav className="flex-1 overflow-y-auto px-2">
        {loading && <p className="px-2 py-2 text-xs text-zinc-500">Cargando…</p>}
        {!loading && conversations.length === 0 && (
          <p className="px-2 py-2 text-xs text-zinc-500">Todavía no hay conversaciones.</p>
        )}
        <ul className="space-y-1">
          {conversations.map((conversation) => (
            <li key={conversation.id}>
              <Link
                href={`/chat/${conversation.id}`}
                className={`block truncate rounded-lg px-3 py-2 text-sm transition hover:bg-zinc-800 ${
                  params?.conversationId === conversation.id
                    ? "bg-zinc-800 text-zinc-50"
                    : "text-zinc-300"
                }`}
              >
                {conversation.title}
              </Link>
            </li>
          ))}
        </ul>
      </nav>

      <div className="border-t border-zinc-800 p-2">
        <Link
          href="/dashboard"
          className="block rounded-lg px-3 py-2 text-sm text-zinc-300 transition hover:bg-zinc-800"
        >
          📊 Dashboard
        </Link>
        <div className="flex items-center justify-between px-3 py-2">
          <span className="truncate text-xs text-zinc-500">{user?.email}</span>
          <button onClick={handleLogout} className="text-xs text-zinc-500 hover:text-zinc-200">
            Salir
          </button>
        </div>
      </div>
    </aside>
  );
}
