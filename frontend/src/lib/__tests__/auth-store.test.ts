import { beforeEach, describe, expect, it } from "vitest";

import { useAuthStore } from "../auth-store";

describe("useAuthStore", () => {
  beforeEach(() => {
    window.localStorage.clear();
    useAuthStore.setState({ user: null, accessToken: null, refreshToken: null, hydrated: false });
  });

  it("persists tokens to localStorage and to the store", () => {
    useAuthStore.getState().setTokens("access-123", "refresh-456");

    expect(useAuthStore.getState().accessToken).toBe("access-123");
    expect(useAuthStore.getState().refreshToken).toBe("refresh-456");
    expect(window.localStorage.getItem("asistente_access_token")).toBe("access-123");
    expect(window.localStorage.getItem("asistente_refresh_token")).toBe("refresh-456");
  });

  it("hydrates state from localStorage", () => {
    window.localStorage.setItem("asistente_access_token", "stored-access");
    window.localStorage.setItem("asistente_refresh_token", "stored-refresh");

    useAuthStore.getState().hydrate();

    expect(useAuthStore.getState().accessToken).toBe("stored-access");
    expect(useAuthStore.getState().refreshToken).toBe("stored-refresh");
    expect(useAuthStore.getState().hydrated).toBe(true);
  });

  it("clears everything on logout", () => {
    useAuthStore.getState().setTokens("access-123", "refresh-456");
    useAuthStore.getState().setUser({ id: "1", email: "a@a.com", full_name: "A", is_active: true });

    useAuthStore.getState().logout();

    expect(useAuthStore.getState().user).toBeNull();
    expect(useAuthStore.getState().accessToken).toBeNull();
    expect(window.localStorage.getItem("asistente_access_token")).toBeNull();
  });
});
