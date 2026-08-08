import { apiRequest } from "./apiClient";
import type { Intervention, InterventionAssignee, InterventionCreate, InterventionEvent, InterventionFilters, InterventionLink, InterventionPage, InterventionStatus, InterventionSummary, InterventionTransitionResult } from "../types/interventions";

const query = (values:Record<string,unknown>) => { const params = new URLSearchParams(); Object.entries(values).forEach(([key,value]) => { if (value !== undefined && value !== null && value !== "") params.set(key,String(value)); }); const encoded=params.toString(); return encoded?`?${encoded}`:""; };
export const listInterventions=(filters:InterventionFilters={},cursor?:string)=>apiRequest<InterventionPage>(`/api/v1/interventions${query({...filters,cursor})}`);
export const interventionSummary=()=>apiRequest<InterventionSummary>("/api/v1/interventions/summary");
export const interventionAssignees=()=>apiRequest<InterventionAssignee[]>("/api/v1/interventions/assignees");
export const createIntervention=(payload:InterventionCreate)=>apiRequest<Intervention>("/api/v1/interventions",{method:"POST",body:JSON.stringify(payload)});
export const getIntervention=(id:string)=>apiRequest<Intervention>(`/api/v1/interventions/${id}`);
export const patchIntervention=(id:string,payload:{expected_version:number;title?:string;description?:string;priority?:Intervention["priority"];assigned_user_id?:string|null;due_at?:string|null})=>apiRequest<Intervention>(`/api/v1/interventions/${id}`,{method:"PATCH",body:JSON.stringify(payload)});
export const transitionIntervention=(id:string,payload:{command_id:string;expected_version:number;to_status:InterventionStatus;note?:string;resolution_summary?:string})=>apiRequest<InterventionTransitionResult>(`/api/v1/interventions/${id}/transitions`,{method:"POST",body:JSON.stringify(payload)});
export const interventionTimeline=(id:string)=>apiRequest<InterventionEvent[]>(`/api/v1/interventions/${id}/timeline`);
export const interventionKnowledge=(id:string)=>apiRequest<InterventionLink[]>(`/api/v1/interventions/${id}/knowledge`);
export const linkInterventionKnowledge=(id:string,payload:{knowledge_card_id:string;usage_type:InterventionLink["usage_type"];note:string})=>apiRequest<InterventionLink>(`/api/v1/interventions/${id}/knowledge`,{method:"POST",body:JSON.stringify(payload)});
export const unlinkInterventionKnowledge=(id:string,linkId:string)=>apiRequest<void>(`/api/v1/interventions/${id}/knowledge/${linkId}`,{method:"DELETE"});
