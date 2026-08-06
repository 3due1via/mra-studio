import type { Environment, EnvironmentInput, MraObject, MraObjectInput, Project, ProjectInput } from "../types/projects";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...init?.headers },
  });
  if (!response.ok) {
    const detail = await response.json().catch(() => null);
    throw new Error(detail?.detail ?? `Errore API (${response.status})`);
  }
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

export const listProjects = () => request<Project[]>("/api/v1/projects");
export const createProject = (input: ProjectInput) => request<Project>("/api/v1/projects", { method: "POST", body: JSON.stringify(input) });
export const updateProject = (id: string, input: Partial<ProjectInput>) => request<Project>(`/api/v1/projects/${id}`, { method: "PUT", body: JSON.stringify(input) });
export const deleteProject = (id: string) => request<void>(`/api/v1/projects/${id}`, { method: "DELETE" });
export const listEnvironments = (projectId: string) => request<Environment[]>(`/api/v1/projects/${projectId}/environments`);
export const createEnvironment = (projectId: string, input: EnvironmentInput) => request<Environment>(`/api/v1/projects/${projectId}/environments`, { method: "POST", body: JSON.stringify(input) });
export const listObjects = (environmentId: string) => request<MraObject[]>(`/api/v1/projects/environments/${environmentId}/objects`);
export const createObject = (environmentId: string, input: MraObjectInput) => request<MraObject>(`/api/v1/projects/environments/${environmentId}/objects`, { method: "POST", body: JSON.stringify(input) });
