import type { HealthResponse } from '../types/health'

const API_BASE = (import.meta.env.VITE_API_URL ?? '').replace(/\/$/, '')
const apiUrl = (path:string) => `${API_BASE}${path}`

export async function getHealth(signal?: AbortSignal): Promise<HealthResponse> {
  const response = await fetch(apiUrl('/api/health'), { signal })
  if (!response.ok) throw new Error(`Health check failed (${response.status})`)
  return response.json() as Promise<HealthResponse>
}

export interface DocumentItem { id:string; name:string; file_type:string; size:number; status:string; department:string; created_at:string; chunk_count:number; vector_model:string|null }
export interface DocumentDetail extends DocumentItem { preview:string; chunks:{id:string;chunk_index:number;content:string;vector_model:string}[] }
export interface Citation { document_id:string; document_name:string; excerpt:string; score:number }
export interface ChatResult { answer:string; conversation_id:string; citations:Citation[]; confidence:string; configured:boolean }
export interface Analytics { total_documents:number; indexed_documents:number; total_queries:number; successful_answers:number; average_response_time_ms:number }
export interface AgentEvidence {document_id:string;document_name:string;chunk_id:string;excerpt:string;score:number;verified:boolean}
export interface AgentRisk {title:string;severity:string;description:string;evidence:string;document_id:string;recommendation:string}
export interface ResearchResult {run_id:string;conversation_id:string;status:string;plan:{order:number;name:string;status:string}[];answer:string;evidence:AgentEvidence[];risks:AgentRisk[];critic:{passed:boolean;score:number;recommendation:string};disclaimer?:string}
export interface AgentRun {id:string;agent_type:string;status:string;steps:number;tool_calls:number;retrieval_attempts:number;documents_examined:number;evidence_count:number;critic_score:number;latency_ms:number;created_at:string}
export interface Insight {category:string;title:string;description:string;severity:string;evidence:string;document_id:string;document_name:string}
export interface KnowledgeMap {nodes:{id:string;label:string;type:string}[];links:{source:string;target:string}[]}

async function json<T>(url:string, options?:RequestInit):Promise<T>{
  const response=await fetch(apiUrl(url),options)
  if(!response.ok){ const body=await response.json().catch(()=>({detail:'Request failed'})); throw new Error(body.detail ?? `Request failed (${response.status})`) }
  return response.status===204 ? (undefined as T) : response.json() as Promise<T>
}
export const listDocuments=()=>json<DocumentItem[]>('/api/documents')
export const uploadDocument=(file:File,department:string)=>{const form=new FormData();form.append('file',file);form.append('department',department);return json<DocumentItem>('/api/documents/upload',{method:'POST',body:form})}
export const deleteDocument=(id:string)=>json<void>(`/api/documents/${id}`,{method:'DELETE'})
export const getDocument=(id:string)=>json<DocumentDetail>(`/api/documents/${id}`)
export const askQuestion=(question:string,documentIds:string[]=[])=>json<ChatResult>('/api/chat',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({question,document_ids:documentIds})})
export const getAnalytics=()=>json<Analytics>('/api/analytics')
export const compareDocuments=(document_a_id:string,document_b_id:string)=>json<{comparison:string;document_a:string;document_b:string;configured:boolean}>('/api/documents/compare',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({document_a_id,document_b_id})})
export const research=(question:string,document_ids:string[]=[])=>json<ResearchResult>('/api/agents/research',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({question,document_ids})})
export const getInsights=()=>json<Insight[]>('/api/insights')
export const getAgentRuns=()=>json<AgentRun[]>('/api/agents/runs')
export const analyzeRisks=(question:string,document_ids:string[]=[])=>json<{risks:AgentRisk[];disclaimer:string}>('/api/agents/risk-analysis',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({question,document_ids})})
export const getKnowledgeMap=()=>json<KnowledgeMap>('/api/knowledge-map')
export const askAnalytics=(question:string)=>json<{answer:string;data:{label:string;value:number}[];visualization:string}>('/api/agents/analytics',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({question})})
export const submitReview=(analysis_id:string,action:'approve'|'reject'|'request_reanalysis',comment='')=>json('/api/ai-reviews',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({analysis_id,action,comment})})
