"use client";

import { useRouter } from "next/navigation";

import { api } from "@/lib/api";

export default function ChatEmptyPage() {
  const router = useRouter();

  async function handleStart() {
    const conversation = await api.createConversation();
    router.push(`/chat/${conversation.id}`);
  }

  return (
    <div className="flex flex-1 flex-col items-center justify-center gap-4 text-center px-4">
      <h1 className="text-2xl font-semibold text-zinc-100">Asistente Personal IA</h1>
      <p className="max-w-md text-sm text-zinc-400">
        Hablá o escribí como lo harías con tu secretario ejecutivo. Recuerda, organiza y prioriza
        por vos.
      </p>
      <button
        onClick={handleStart}
        className="rounded-lg bg-indigo-600 px-5 py-2.5 text-sm font-medium text-white transition hover:bg-indigo-500"
      >
        Iniciar conversación
      </button>
    </div>
  );
}
