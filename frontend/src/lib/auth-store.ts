"use client";

import { create } from "zustand";

import type { User } from "./types";

const ACCESS_TOKEN_KEY = "asistente_access_token";
const REFRESH_TOKEN_KEY = "asistente_refresh_token";

interface AuthState {
  user: User | null;
  accessToken: string | null;
  refreshToken: string | null;
  hydrated: boolean;
  setTokens: (accessToken: string, refreshToken: string) => void;
  setUser: (user: User | null) => void;
  hydrate: () => void;
  logout: () => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  accessToken: null,
  refreshToken: null,
  hydrated: false,
  setTokens: (accessToken, refreshToken) => {
    if (typeof window !== "undefined") {
      window.localStorage.setItem(ACCESS_TOKEN_KEY, accessToken);
      window.localStorage.setItem(REFRESH_TOKEN_KEY, refreshToken);
    }
    set({ accessToken, refreshToken });
  },
  setUser: (user) => set({ user }),
  hydrate: () => {
    if (typeof window === "undefined") return;
    const accessToken = window.localStorage.getItem(ACCESS_TOKEN_KEY);
    const refreshToken = window.localStorage.getItem(REFRESH_TOKEN_KEY);
    set({ accessToken, refreshToken, hydrated: true });
  },
  logout: () => {
    if (typeof window !== "undefined") {
      window.localStorage.removeItem(ACCESS_TOKEN_KEY);
      window.localStorage.removeItem(REFRESH_TOKEN_KEY);
    }
    set({ user: null, accessToken: null, refreshToken: null });
  },
}));
