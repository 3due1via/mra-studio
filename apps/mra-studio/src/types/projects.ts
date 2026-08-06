export type ProjectStatus = "draft" | "active" | "paused" | "completed" | "archived";

export type Project = {
  id: string;
  name: string;
  project_type: string;
  customer: string;
  description: string;
  status: ProjectStatus;
  progress: number;
  created_at: string;
  updated_at: string;
};

export type ProjectInput = Omit<Project, "id" | "created_at" | "updated_at">;

export type Environment = {
  id: string;
  project_id: string;
  name: string;
  environment_type: string;
  area_m2: string;
  height_m: string;
  width_m: string;
  length_m: string;
  notes: string;
  created_at: string;
  updated_at: string;
};

export type EnvironmentInput = Omit<Environment, "id" | "project_id" | "created_at" | "updated_at">;

export type MraObject = {
  id: string;
  environment_id: string;
  category: string;
  name: string;
  brand: string;
  model: string;
  serial_number: string;
  description: string;
  status: string;
  metadata_json: Record<string, unknown>;
  created_at: string;
  updated_at: string;
};

export type MraObjectInput = Omit<MraObject, "id" | "environment_id" | "created_at" | "updated_at">;
