import type { Environment, EnvironmentInput, EnvironmentUpdate, MraObject, MraObjectInput, MraObjectUpdate, Project, ProjectInput, ProjectUpdate } from "../types/projects";
import { apiRequest as request } from "./apiClient";

export const listProjects = () => request<Project[]>("/api/v1/projects");
export const getProject = (id: string) => request<Project>(`/api/v1/projects/${id}`);
export const createProject = (input: ProjectInput) => request<Project>("/api/v1/projects", { method: "POST", body: JSON.stringify(input) });
export const updateProject = (id: string, input: ProjectUpdate) => request<Project>(`/api/v1/projects/${id}`, { method: "PUT", body: JSON.stringify(input) });
export const deleteProject = (id: string) => request<void>(`/api/v1/projects/${id}`, { method: "DELETE" });
export const listEnvironments = (projectId: string) => request<Environment[]>(`/api/v1/projects/${projectId}/environments`);
export const createEnvironment = (projectId: string, input: EnvironmentInput) => request<Environment>(`/api/v1/projects/${projectId}/environments`, { method: "POST", body: JSON.stringify(input) });
export const getEnvironment = (id: string) => request<Environment>(`/api/v1/environments/${id}`);
export const updateEnvironment = (id: string, input: EnvironmentUpdate) => request<Environment>(`/api/v1/environments/${id}`, { method: "PUT", body: JSON.stringify(input) });
export const deleteEnvironment = (id: string) => request<void>(`/api/v1/environments/${id}`, { method: "DELETE" });
export const listObjects = (environmentId: string) => request<MraObject[]>(`/api/v1/environments/${environmentId}/objects`);
export const createObject = (environmentId: string, input: MraObjectInput) => request<MraObject>(`/api/v1/environments/${environmentId}/objects`, { method: "POST", body: JSON.stringify(input) });
export const getObject = (id: string) => request<MraObject>(`/api/v1/objects/${id}`);
export const updateObject = (id: string, input: MraObjectUpdate) => request<MraObject>(`/api/v1/objects/${id}`, { method: "PUT", body: JSON.stringify(input) });
export const deleteObject = (id: string) => request<void>(`/api/v1/objects/${id}`, { method: "DELETE" });
