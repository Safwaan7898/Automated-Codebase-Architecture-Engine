import React, { useState, useMemo } from 'react';
import { ChevronDown, ChevronUp, ChevronsUpDown, ChevronLeft, ChevronRight, Search } from 'lucide-react';

export interface Column<T> {
  key: keyof T | string;
  header: string;
  sortable?: boolean;
  render?: (item: T, index: number) => React.ReactNode;
  width?: string;
}

export interface DataTableProps<T> {
  data: T[];
  columns: Column<T>[];
  searchPlaceholder?: string;
  searchableKey?: keyof T;
  pageSize?: number;
  emptyMessage?: string;
  className?: string;
}

export function DataTable<T extends Record<string, any>>({
  data,
  columns,
  searchPlaceholder = 'Filter records...',
  searchableKey,
  pageSize = 10,
  emptyMessage = 'No matching records found.',
  className = ''
}: DataTableProps<T>) {
  const [searchTerm, setSearchTerm] = useState('');
  const [sortKey, setSortKey] = useState<string | null>(null);
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('asc');
  const [currentPage, setCurrentPage] = useState(1);
  const [rowsPerPage, setRowsPerPage] = useState(pageSize);

  // Filter
  const filteredData = useMemo(() => {
    if (!searchTerm.trim()) return data;
    const lower = searchTerm.toLowerCase();
    return data.filter((item) => {
      if (searchableKey) {
        return String(item[searchableKey] ?? '').toLowerCase().includes(lower);
      }
      return Object.values(item).some((val) =>
        String(val ?? '').toLowerCase().includes(lower)
      );
    });
  }, [data, searchTerm, searchableKey]);

  // Sort
  const sortedData = useMemo(() => {
    if (!sortKey) return filteredData;
    return [...filteredData].sort((a, b) => {
      const aVal = a[sortKey];
      const bVal = b[sortKey];
      if (aVal === bVal) return 0;
      if (aVal === null || aVal === undefined) return 1;
      if (bVal === null || bVal === undefined) return -1;
      if (typeof aVal === 'number' && typeof bVal === 'number') {
        return sortOrder === 'asc' ? aVal - bVal : bVal - aVal;
      }
      const strA = String(aVal).toLowerCase();
      const strB = String(bVal).toLowerCase();
      return sortOrder === 'asc' ? strA.localeCompare(strB) : strB.localeCompare(strA);
    });
  }, [filteredData, sortKey, sortOrder]);

  // Pagination
  const totalPages = Math.max(1, Math.ceil(sortedData.length / rowsPerPage));
  const paginatedData = useMemo(() => {
    const start = (currentPage - 1) * rowsPerPage;
    return sortedData.slice(start, start + rowsPerPage);
  }, [sortedData, currentPage, rowsPerPage]);

  const handleSort = (key: string) => {
    if (sortKey === key) {
      if (sortOrder === 'asc') setSortOrder('desc');
      else {
        setSortKey(null);
        setSortOrder('asc');
      }
    } else {
      setSortKey(key);
      setSortOrder('asc');
    }
  };

  return (
    <div className={`space-y-4 ${className}`}>
      {/* Search Bar */}
      <div className="flex flex-col sm:flex-row items-center justify-between gap-4">
        <div className="relative w-full sm:w-72">
          <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-[var(--agencia-text-muted)]" />
          <input
            type="text"
            value={searchTerm}
            onChange={(e) => {
              setSearchTerm(e.target.value);
              setCurrentPage(1);
            }}
            placeholder={searchPlaceholder}
            className="w-full pl-9 pr-3 py-2 text-xs rounded-xl bg-[var(--agencia-surface)] border border-[var(--agencia-border)] text-[var(--agencia-text)] placeholder-[var(--placeholder)] focus:outline-none focus:border-[var(--agencia-lime)] transition-colors"
          />
        </div>
        <div className="text-xs text-[var(--agencia-text-muted)] font-mono self-end sm:self-center">
          Showing <span className="text-[var(--agencia-text)] font-semibold">{sortedData.length}</span> results
        </div>
      </div>

      {/* Table Surface */}
      <div className="overflow-x-auto rounded-xl border border-[var(--agencia-border)] bg-[var(--agencia-surface)]/60 backdrop-blur-md">
        <table className="w-full text-left text-xs border-collapse">
          <thead>
            <tr className="border-b border-[var(--agencia-border)] bg-[var(--agencia-surface)]/80 text-[var(--agencia-text-muted)] font-mono uppercase tracking-wider text-[11px]">
              {columns.map((col, idx) => {
                const isSorted = sortKey === String(col.key);
                return (
                  <th
                    key={idx}
                    style={{ width: col.width }}
                    onClick={() => col.sortable && handleSort(String(col.key))}
                    className={`py-3 px-4 select-none ${col.sortable ? 'cursor-pointer hover:text-[var(--agencia-text)]' : ''}`}
                  >
                    <div className="flex items-center gap-1.5">
                      <span>{col.header}</span>
                      {col.sortable && (
                        <span className="text-[var(--agencia-text-muted)]">
                          {isSorted ? (
                            sortOrder === 'asc' ? (
                              <ChevronUp className="w-3.5 h-3.5 text-[var(--accent-text)]" />
                            ) : (
                              <ChevronDown className="w-3.5 h-3.5 text-[var(--accent-text)]" />
                            )
                          ) : (
                            <ChevronsUpDown className="w-3.5 h-3.5 opacity-40" />
                          )}
                        </span>
                      )}
                    </div>
                  </th>
                );
              })}
            </tr>
          </thead>
          <tbody className="divide-y divide-[var(--agencia-border)]">
            {paginatedData.length === 0 ? (
              <tr>
                <td colSpan={columns.length} className="py-8 text-center text-[var(--agencia-text-muted)]">
                  {emptyMessage}
                </td>
              </tr>
            ) : (
              paginatedData.map((row, rIdx) => (
                <tr
                  key={rIdx}
                  className="hover:bg-[var(--agencia-glass-border)] transition-colors text-[var(--agencia-text)]"
                >
                  {columns.map((col, cIdx) => (
                    <td key={cIdx} className="py-3 px-4 font-sans align-middle">
                      {col.render
                        ? col.render(row, rIdx)
                        : String(row[col.key as keyof T] ?? '')}
                    </td>
                  ))}
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination Controls */}
      <div className="flex flex-col sm:flex-row items-center justify-between gap-4 text-xs font-mono text-[var(--agencia-text-muted)] pt-2">
        <div className="flex items-center gap-2">
          <span>Rows per page:</span>
          <select
            value={rowsPerPage}
            onChange={(e) => {
              setRowsPerPage(Number(e.target.value));
              setCurrentPage(1);
            }}
            className="bg-[var(--agencia-surface)] border border-[var(--agencia-border)] rounded-lg px-2 py-1 text-[var(--agencia-text)] focus:outline-none focus:border-[var(--agencia-lime)]"
          >
            <option value={5}>5</option>
            <option value={10}>10</option>
            <option value={20}>20</option>
            <option value={50}>50</option>
          </select>
        </div>

        <div className="flex items-center gap-3">
          <span>
            Page <span className="text-[var(--agencia-text)] font-semibold">{currentPage}</span> of{' '}
            <span className="text-[var(--agencia-text)] font-semibold">{totalPages}</span>
          </span>
          <div className="flex items-center gap-1">
            <button
              onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
              disabled={currentPage === 1}
              className="p-1.5 rounded-lg border border-[var(--agencia-border)] bg-[var(--agencia-surface)] hover:bg-[var(--agencia-glass-border)] disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
            >
              <ChevronLeft className="w-4 h-4" />
            </button>
            <button
              onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
              disabled={currentPage === totalPages}
              className="p-1.5 rounded-lg border border-[var(--agencia-border)] bg-[var(--agencia-surface)] hover:bg-[var(--agencia-glass-border)] disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
            >
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
