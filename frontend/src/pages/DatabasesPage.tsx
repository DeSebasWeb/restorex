import { useState, useMemo } from 'react'
import { Search, Database, ArrowUpDown } from 'lucide-react'
import { StatusDot } from '../components/StatusDot'
import { fmtNum, fmtSize, formatTimestamp } from '../utils/format'
import type { DatabaseStatus } from '../types'

interface Props {
  databases: DatabaseStatus[]
}

type SortKey = 'name' | 'size' | 'tables' | 'rows' | 'changes'

export function DatabasesPage({ databases }: Props) {
  const [search, setSearch] = useState('')
  const [sortKey, setSortKey] = useState<SortKey>('name')
  const [sortAsc, setSortAsc] = useState(true)

  const handleSort = (key: SortKey) => {
    if (sortKey === key) {
      setSortAsc(!sortAsc)
    } else {
      setSortKey(key)
      setSortAsc(true)
    }
  }

  const filtered = useMemo(() => {
    let result = databases.filter(db =>
      db.name.toLowerCase().includes(search.toLowerCase())
    )
    result.sort((a, b) => {
      let cmp = 0
      switch (sortKey) {
        case 'name': cmp = a.name.localeCompare(b.name); break
        case 'size': cmp = a.size.localeCompare(b.size); break
        case 'tables': cmp = a.tables - b.tables; break
        case 'rows': cmp = a.live_rows - b.live_rows; break
        case 'changes': cmp = (a.inserts + a.updates + a.deletes) - (b.inserts + b.updates + b.deletes); break
        default: cmp = a.name.localeCompare(b.name)
      }
      return sortAsc ? cmp : -cmp
    })
    return result
  }, [databases, search, sortKey, sortAsc])

  const backedUp = databases.filter(d => d.last_backup).length
  const pending = databases.filter(d => !d.last_backup).length

  return (
    <div className="p-7 space-y-5">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold theme-text">All Databases</h2>
          <p className="text-xs theme-text-muted mt-0.5">
            {backedUp} protected &middot; {pending} pending &middot; {databases.length} total
          </p>
        </div>

        {/* Search */}
        <div className="relative">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 theme-text-faint" />
          <input
            type="text"
            placeholder="Search databases..."
            value={search}
            onChange={e => setSearch(e.target.value)}
            className="pl-9 pr-4 py-2 rounded-xl theme-bg-card border theme-border text-sm theme-text-secondary
                       placeholder:theme-text-faint focus:outline-none focus:border-blue-500/30 focus:ring-1 focus:ring-blue-500/20
                       transition-all w-64"
          />
        </div>
      </div>

      {/* Table */}
      <div className="theme-bg-card border theme-border rounded-2xl overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-[13px]">
            <thead>
              <tr className="text-left theme-bg-table-header">
                <th className="px-4 py-3 w-8">
                  <span className="text-[10px] uppercase tracking-wider font-semibold theme-text-muted">#</span>
                </th>
                {[
                  { key: 'name' as SortKey, label: 'Database' },
                  { key: 'size' as SortKey, label: 'Size' },
                  { key: 'tables' as SortKey, label: 'Tables' },
                  { key: 'rows' as SortKey, label: 'Live Rows' },
                  { key: 'changes' as SortKey, label: 'Inserts (sort by total)' },
                ].map(col => (
                  <th
                    key={col.key}
                    onClick={() => handleSort(col.key)}
                    className="px-4 py-3 text-[10px] uppercase tracking-wider font-semibold theme-text-muted cursor-pointer hover:theme-text-secondary transition-colors"
                  >
                    <span className="inline-flex items-center gap-1">
                      {col.label}
                      <ArrowUpDown size={10} className={sortKey === col.key ? 'text-blue-400' : 'opacity-30'} />
                    </span>
                  </th>
                ))}
                <th className="px-4 py-3 text-[10px] uppercase tracking-wider font-semibold theme-text-muted">Updates</th>
                <th className="px-4 py-3 text-[10px] uppercase tracking-wider font-semibold theme-text-muted">Deletes</th>
                <th className="px-4 py-3 text-[10px] uppercase tracking-wider font-semibold theme-text-muted">Last Checked</th>
                <th className="px-4 py-3 text-[10px] uppercase tracking-wider font-semibold theme-text-muted">Last Backup</th>
                <th className="px-4 py-3 text-[10px] uppercase tracking-wider font-semibold theme-text-muted">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[var(--border)]">
              {filtered.length === 0 ? (
                <tr>
                  <td colSpan={11} className="text-center py-12">
                    <div className="flex flex-col items-center theme-text-faint">
                      <Database size={36} className="mb-2 opacity-20" />
                      <p className="text-sm font-medium">
                        {databases.length === 0 ? 'No databases loaded' : 'No matches found'}
                      </p>
                      <p className="text-xs mt-1">
                        {databases.length === 0 ? 'Click "Scan DBs" to start' : 'Try a different search'}
                      </p>
                    </div>
                  </td>
                </tr>
              ) : (
                filtered.map((db, idx) => (
                  <tr key={db.name} className="theme-hover transition-colors">
                    <td className="px-4 py-3 theme-text-faint font-mono text-xs">{idx + 1}</td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-2">
                        <StatusDot status={db.last_backup ? 'green' : 'gray'} />
                        <span className="font-semibold theme-text-secondary">{db.name}</span>
                      </div>
                    </td>
                    <td className="px-4 py-3 theme-text-tertiary font-mono text-xs">{db.size}</td>
                    <td className="px-4 py-3 theme-text-tertiary">{db.tables}</td>
                    <td className="px-4 py-3 theme-text-tertiary font-mono text-xs">{fmtNum(db.live_rows)}</td>
                    <td className="px-4 py-3 text-emerald-400 font-mono text-xs">{fmtNum(db.inserts)}</td>
                    <td className="px-4 py-3 text-blue-400 font-mono text-xs">{fmtNum(db.updates)}</td>
                    <td className="px-4 py-3 text-red-400 font-mono text-xs">{fmtNum(db.deletes)}</td>
                    <td className="px-4 py-3 theme-text-muted text-xs">
                      {db.last_checked ? new Date(db.last_checked).toLocaleString('es-CO') : '--'}
                    </td>
                    <td className="px-4 py-3">
                      {db.last_backup ? (
                        <div className="flex flex-col">
                          <span className="text-xs theme-text-tertiary">{formatTimestamp(db.last_backup.timestamp)}</span>
                          <span className="text-[10px] theme-text-faint">
                            {fmtSize(db.last_backup.backup_size + db.last_backup.sql_size)}
                          </span>
                        </div>
                      ) : (
                        <span className="text-xs text-amber-500/80 font-medium">Never</span>
                      )}
                    </td>
                    <td className="px-4 py-3">
                      {db.last_backup ? (
                        <StatusDot status="green" label="OK" />
                      ) : (
                        <StatusDot status="yellow" label="Pending" />
                      )}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
