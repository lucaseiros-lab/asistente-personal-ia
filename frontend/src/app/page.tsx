"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

import { useAuthStore } from "@/lib/auth-store";

export default function Home() {
  const router = useRouter();
  const { accessToken, hydrated, hydrate } = useAuthStore();

  useEffect(() => {
    hydrate();
  }, [hydrate]);

  useEffect(() => {
    if (!hydrated) return;
    router.replace(accessToken ? "/chat" : "/login");
  }, [hydrated, accessToken, router]);

  return (
    <div className="flex flex-1 items-center justify-center">
      <p className="text-sm text-zinc-500">Cargando…</p>
    </div>
  );
}
