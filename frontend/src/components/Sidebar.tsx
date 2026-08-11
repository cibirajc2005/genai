import { Activity, BookOpen, Bot, FileStack, Gauge, Library, Lightbulb, Network, SearchCheck, ShieldAlert } from 'lucide-react'

const navigation = [
  [Gauge, 'Dashboard', true], [Bot, 'AI Assistant', false], [FileStack, 'Documents', false],
  [BookOpen, 'Compare Documents', false],
  [SearchCheck, 'AI Research', false], [Lightbulb, 'AI Insights', false],
  [ShieldAlert, 'Risk Analysis', false], [Network, 'Knowledge Map', false], [Activity, 'Agent Runs', false],
] as const

export type PageName = 'Dashboard'|'AI Assistant'|'Documents'|'Compare Documents'|'AI Research'|'AI Insights'|'Risk Analysis'|'Knowledge Map'|'Agent Runs'
export function Sidebar({page,onChange}:{page:PageName;onChange:(page:PageName)=>void}) {
  return <aside className="sidebar">
    <div className="brand"><span className="brand-mark"><Library size={20}/></span><div><strong>Knowledge Hub</strong><small>Document Assistant</small></div></div>
    <nav aria-label="Primary navigation">
      <p className="nav-label">Workspace</p>
      {navigation.map(([Icon, label]) => <button onClick={()=>onChange(label as PageName)} className={`nav-item ${page===label ? 'active' : ''}`} key={label}><Icon size={18}/><span>{label}</span>{label === 'AI Assistant' && <em>AI</em>}</button>)}
    </nav>
  </aside>
}
