import type { User, UserInput } from "../types/auth";
import { apiRequest } from "./apiClient";

export const login = (email: string, password: string) => apiRequest<{ user: User }>("/api/v1/auth/login", { method: "POST", body: JSON.stringify({ email, password }) });
export const currentUser = () => apiRequest<User>("/api/v1/auth/me");
export const logout = () => apiRequest<void>("/api/v1/auth/logout", { method: "POST" });
export const listUsers = () => apiRequest<User[]>("/api/v1/users");
export const createUser = (input: UserInput) => apiRequest<User>("/api/v1/users", { method: "POST", body: JSON.stringify(input) });
export const updateUser = (id: string, input: Partial<Omit<UserInput, "email"> & { is_active: boolean }>) => apiRequest<User>(`/api/v1/users/${id}`, { method: "PATCH", body: JSON.stringify(input) });
export const revokeSessions = (id: string) => apiRequest<void>(`/api/v1/users/${id}/revoke-sessions`, { method: "POST" });
