import { useEffect, useState } from 'react'
import type { ReactNode } from 'react'
import { Activity, AlertTriangle, CheckCircle2, RefreshCw, ShieldAlert } from 'lucide-react'
import { AgentRisk, AgentRun, analyzeRisks, DocumentItem, getAgentRuns } from '../services/api'

const errorMessage = (error:unknown) => error instanceof Error ? error.message : 'Something went wrong. Please try again.'

function Notice({kind='info',children}:{kind?:'info'|'error'|'success';children:ReactNode}){
 return <div className={`agent-notice ${kind}`}>{kind==='error'?<AlertTriangle/>:<CheckCircle2/>}<span>{children}</span></div>
}

function DocumentPicker({documents,selected,setSelected}:{documents:DocumentItem[];selected:string[];setSelected:(ids:string[])=>void}){
 const all=selected.length===0
 return <div className="agent-scope"><div><strong>Documents to analyze</strong><button type="button" onClick={()=>setSelected([])}>{all?'All selected':'Use all'}</button></div>{documents.map(doc=><label key={doc.id}><input type="checkbox" checked={all||selected.includes(doc.id)} onChange={()=>setSelected(all?documents.filter(item=>item.id!==doc.id).map(item=>item.id):selected.includes(doc.id)?selected.filter(id=>id!==doc.id):[...selected,doc.id])}/><span>{doc.name}</span><small>{doc.department}</small></label>)}</div>
}

function RiskList({risks,disclaimer}:{risks:AgentRisk[];disclaimer?:string}){
 return <article className="agent-card agent-output"><div className="output-head"><div><small>EVIDENCE-BASED FINDINGS</small><h2>Risk findings</h2></div><b>{risks.length} findings</b></div>{risks.map((risk,i)=><div className="risk-row" key={`${risk.document_id}-${i}`}><span className={`severity ${risk.severity.toLowerCase()}`}>{risk.severity}</span><div><strong>{risk.title}</strong><p>{risk.description}</p><blockquote>{risk.evidence}</blockquote><small>Recommended action: {risk.recommendation}</small></div></div>)}<p className="disclaimer">{disclaimer}</p></article>
}

export function RiskPage({documents}:{documents:DocumentItem[]}){
 const [selected,setSelected]=useState<string[]>([]),[focus,setFocus]=useState('obligations, penalties, deadlines, contradictions and compliance concerns'),[risks,setRisks]=useState<AgentRisk[]|null>(null),[busy,setBusy]=useState(false),[error,setError]=useState('')
 const run=async()=>{setBusy(true);setError('');setRisks(null);try{setRisks((await analyzeRisks(focus,selected)).risks)}catch(error){setError(errorMessage(error))}finally{setBusy(false)}}
 return <section className="agent-workspace"><div className="agent-two-column"><article className="agent-card agent-prompt"><ShieldAlert/><h2>Risk & Compliance Analysis</h2><p>Review obligations and potentially high-impact clauses using traceable document evidence.</p><label className="agent-label">Analysis focus</label><textarea value={focus} onChange={event=>setFocus(event.target.value)}/><button className="primary action-button" onClick={run} disabled={busy||!documents.length||!focus.trim()}>{busy?<><RefreshCw className="spin"/>Analyzing evidence…</>:<><ShieldAlert/>Run risk analysis</>}</button>{!documents.length&&<Notice kind="error">Upload documents to enable risk analysis.</Notice>}{error&&<Notice kind="error">{error}</Notice>}</article><DocumentPicker documents={documents} selected={selected} setSelected={setSelected}/></div>{risks?.length?<RiskList risks={risks} disclaimer="AI risk analysis supports human review and is not legal or compliance advice."/>:risks&&<article className="agent-card"><Notice kind="success">No risk indicators matched this analysis focus. Try a broader focus if needed.</Notice></article>}</section>
}

export function RunsPage(){
 const [runs,setRuns]=useState<AgentRun[]>([]),[loading,setLoading]=useState(true),[error,setError]=useState('')
 const load=()=>{setLoading(true);setError('');getAgentRuns().then(setRuns).catch(error=>setError(errorMessage(error))).finally(()=>setLoading(false))};useEffect(load,[])
 return <section className="agent-card"><div className="output-head"><div><small>SAFE METADATA ONLY</small><h2>Agent Execution History</h2></div><button className="secondary-button" onClick={load}><RefreshCw className={loading?'spin':''}/> Refresh</button></div><p>Monitor risk-analysis latency and evidence use. Private model reasoning is never displayed.</p>{error&&<Notice kind="error">{error}</Notice>}{loading?<div className="page-loading">Loading runs…</div>:runs.length?<div className="run-table"><div className="run-head"><b>Agent</b><b>Status</b><b>Steps</b><b>Retrievals</b><b>Documents</b><b>Evidence</b><b>Quality</b><b>Latency</b></div>{runs.map(run=><div key={run.id}><span><Activity/> {run.agent_type}</span><span className="run-status">{run.status}</span><span>{run.steps}</span><span>{run.retrieval_attempts}</span><span>{run.documents_examined}</span><span>{run.evidence_count}</span><span>{Math.round(run.critic_score*100)}%</span><span>{run.latency_ms} ms</span></div>)}</div>:<Notice>Run a Risk Analysis to create the first execution record.</Notice>}</section>
}
