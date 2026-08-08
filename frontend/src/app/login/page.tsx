"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";

import { api, ApiError } from "@/lib/api";
import { useAuthStore } from "@/lib/auth-store";

export default function LoginPage() {
  const router = useRouter();
  const setTokens = useAuthStore((s) => s.setTokens);
  const setUser = useAuthStore((s) => s.setUser);

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const tokens = await api.login(email, password);
      setTokens(tokens.access_token, tokens.refresh_token);
      const user = await api.me();
      setUser(user);
      router.replace("/chat");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "No se pudo iniciar sesión");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex flex-1 items-center justify-center px-4">
      <form
        onSubmit={handleSubmit}
        className="w-full max-w-sm space-y-5 rounded-2xl border border-zinc-800 bg-zinc-900 p-8"
      >
        <div className="space-y-1 text-center">
          <h1 className="text-xl font-semibold text-zinc-50">Asistente Personal IA</h1>
          <p className="text-sm text-zinc-400">Iniciá sesión para continuar</p>
        </div>

        <div className="space-y-2">
          <label className="text-sm text-zinc-300" htmlFor="email">
            Email
          </label>
          <input
            id="email"
            type="email"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="w-full rounded-lg border border-zinc-700 bg-zinc-950 px-3 py-2 text-sm text-zinc-100 outline-none focus:border-indigo-500"
          />
        </div>

        <div className="space-y-2">
          <label className="text-sm text-zinc-300" htmlFor="password">
            Contraseña
          </label>
          <input
            id="password"
            type="password"
            required
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="w-full rounded-lg border border-zinc-700 bg-zinc-950 px-3 py-2 text-sm text-zinc-100 outline-none focus:border-indigo-500"
          />
        </div>

        {error && <p className="text-sm text-red-400">{error}</p>}

        <button
          type="submit"
          disabled={loading}
          className="w-full rounded-lg bg-indigo-600 py-2 text-sm font-medium text-white transition hover:bg-indigo-500 disabled:opacity-50"
        >
          {loading ? "Ingresando…" : "Ingresar"}
        </button>

        <p className="text-center text-sm text-zinc-400">
          ¿No tenés cuenta?{" "}
          <Link href="/register" className="text-indigo-400 hover:underline">
            Crear cuenta
          </Link>
        </p>
      </form>
    </div>
  );
}
