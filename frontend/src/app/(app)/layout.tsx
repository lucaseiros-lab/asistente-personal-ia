"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { Sidebar } from "@/components/Sidebar";
import { api } from "@/lib/api";
import { useAuthStore } from "@/lib/auth-store";

export default function AppLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const { accessToken, hydrated, hydrate, setUser, user } = useAuthStore();
  const [checking, setChecking] = useState(true);

  useEffect(() => {
    hydrate();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (!hydrated) return;
    if (!accessToken) {
      router.replace("/login");
      return;
    }
    if (user) {
      // eslint-disable-next-line react-hooks/set-state-in-effect
      setChecking(false);
      return;
    }
    api
      .me()
      .then((u) => {
        setUser(u);
        setChecking(false);
      })
      .catch(() => {
        router.replace("/login");
      });
  }, [hydrated, accessToken, user, router, setUser]);

  if (!hydrated || checking) {
    return (
      <div className="flex flex-1 items-center justify-center">
        <p className="text-sm text-zinc-500">Cargando…</p>
      </div>
    );
  }

  return (
    <div className="flex h-screen flex-1 overflow-hidden">
      <Sidebar />
      <main className="flex flex-1 flex-col overflow-hidden">{children}</main>
    </div>
  );
}
