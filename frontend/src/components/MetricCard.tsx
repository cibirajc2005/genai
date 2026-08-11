import type { LucideIcon } from 'lucide-react'

interface Props { icon: LucideIcon; label: string; value: string; note: string; tone: string }

export function MetricCard({ icon: Icon, label, value, note, tone }: Props) {
  return <article className="metric-card"><div className={`metric-icon ${tone}`}><Icon size={20}/></div><div className="metric-copy"><span>{label}</span><strong>{value}</strong><small>{note}</small></div></article>
}

