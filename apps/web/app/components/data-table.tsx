"use client";

import React, { useState } from "react";
import {
  useReactTable,
  getCoreRowModel,
  getSortedRowModel,
  getFilteredRowModel,
  getPaginationRowModel,
  flexRender,
  ColumnDef,
  SortingState,
  ColumnFiltersState,
} from "@tanstack/react-table";
import { Search, ArrowUpDown, ArrowUp, ArrowDown, ChevronLeft, ChevronRight, ChevronsLeft, ChevronsRight } from "lucide-react";

export interface DataTableProps<TData, TValue> {
  columns: ColumnDef<TData, TValue>[];
  data: TData[];
  searchPlaceholder?: string;
  globalFilterColumn?: string; // Column ID to apply global search against
}

export function DataTable<TData, TValue>({
  columns,
  data,
  searchPlaceholder = "Search...",
  globalFilterColumn,
}: DataTableProps<TData, TValue>) {
  const [sorting, setSorting] = useState<SortingState>([]);
  const [columnFilters, setColumnFilters] = useState<ColumnFiltersState>([]);
  const [globalFilter, setGlobalFilter] = useState("");

  const table = useReactTable({
    data,
    columns,
    state: {
      sorting,
      columnFilters,
      globalFilter,
    },
    onSortingChange: setSorting,
    onColumnFiltersChange: setColumnFilters,
    onGlobalFilterChange: setGlobalFilter,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
    getPaginationRowModel: getPaginationRowModel(),
    globalFilterFn: "includesString",
  });

  return (
    <div className="flex flex-col h-full bg-[var(--color-surface)] border border-[var(--color-border)] rounded-xl overflow-hidden">
      {/* Toolbar */}
      <div className="flex items-center gap-3 px-4 py-3 border-b border-[var(--color-border)]">
        <div className="relative flex-1 max-w-xs">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[var(--color-text-dim)]" />
          <input
            type="text"
            value={(globalFilter ?? "") as string}
            onChange={(e) => setGlobalFilter(e.target.value)}
            placeholder={searchPlaceholder}
            className="w-full bg-[var(--color-bg)] border border-[var(--color-border)] rounded-lg pl-9 pr-3 py-2 text-sm text-[var(--color-text)] placeholder:text-[var(--color-text-dim)] focus:outline-none focus:border-[var(--color-accent)]/50 transition-colors"
          />
        </div>
      </div>

      {/* Table */}
      <div className="overflow-x-auto min-h-[300px]">
        <table className="w-full text-sm">
          <thead>
            {table.getHeaderGroups().map((headerGroup) => (
              <tr key={headerGroup.id} className="border-b border-[var(--color-border)] text-left">
                {headerGroup.headers.map((header) => {
                  const canSort = header.column.getCanSort();
                  return (
                    <th
                      key={header.id}
                      className="px-4 py-3 text-[10px] uppercase tracking-wider text-[var(--color-text-dim)] font-medium select-none"
                      style={{ width: header.column.columnDef.size !== 150 ? header.column.columnDef.size : "auto" }}
                    >
                      {header.isPlaceholder ? null : (
                        <div
                          className={`flex items-center gap-1 ${canSort ? "cursor-pointer hover:text-[var(--color-text)] transition-colors" : ""}`}
                          onClick={canSort ? header.column.getToggleSortingHandler() : undefined}
                        >
                          {flexRender(header.column.columnDef.header, header.getContext())}
                          {canSort && (
                            <span className="w-4 h-4 inline-flex items-center justify-center">
                              {{
                                asc: <ArrowUp className="w-3 h-3" />,
                                desc: <ArrowDown className="w-3 h-3" />,
                              }[header.column.getIsSorted() as string] ?? (
                                <ArrowUpDown className="w-3 h-3 opacity-20" />
                              )}
                            </span>
                          )}
                        </div>
                      )}
                    </th>
                  );
                })}
              </tr>
            ))}
          </thead>
          <tbody>
            {table.getRowModel().rows?.length ? (
              table.getRowModel().rows.map((row) => (
                <tr
                  key={row.id}
                  className="border-b border-[var(--color-border-subtle)] hover:bg-[var(--color-surface-hover)] transition-colors last:border-0"
                >
                  {row.getVisibleCells().map((cell) => (
                    <td key={cell.id} className="px-4 py-3 text-[var(--color-text)] text-sm whitespace-nowrap">
                      {flexRender(cell.column.columnDef.cell, cell.getContext())}
                    </td>
                  ))}
                </tr>
              ))
            ) : (
              <tr>
                <td colSpan={columns.length} className="h-24 text-center text-sm text-[var(--color-text-dim)]">
                  No matching results found.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {/* Pagination Footer */}
      {table.getPageCount() > 1 && (
        <div className="flex items-center justify-between px-4 py-3 border-t border-[var(--color-border)] text-xs text-[var(--color-text-muted)]">
          <div>
            Showing {table.getState().pagination.pageIndex * table.getState().pagination.pageSize + 1} to{" "}
            {Math.min(
              (table.getState().pagination.pageIndex + 1) * table.getState().pagination.pageSize,
              table.getFilteredRowModel().rows.length
            )}{" "}
            of {table.getFilteredRowModel().rows.length} rows
          </div>
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-1">
              <span>Rows per page</span>
              <select
                value={table.getState().pagination.pageSize}
                onChange={(e) => table.setPageSize(Number(e.target.value))}
                className="bg-[var(--color-bg)] border border-[var(--color-border)] rounded px-2 py-1 outline-none focus:border-[var(--color-accent)]"
              >
                {[10, 20, 50].map((pageSize) => (
                  <option key={pageSize} value={pageSize}>
                    {pageSize}
                  </option>
                ))}
              </select>
            </div>
            <div className="flex items-center gap-1">
              <button
                onClick={() => table.setPageIndex(0)}
                disabled={!table.getCanPreviousPage()}
                className="p-1 rounded border border-[var(--color-border)] disabled:opacity-50 hover:bg-[var(--color-surface-hover)]"
              >
                <ChevronsLeft className="w-3 h-3" />
              </button>
              <button
                onClick={() => table.previousPage()}
                disabled={!table.getCanPreviousPage()}
                className="p-1 rounded border border-[var(--color-border)] disabled:opacity-50 hover:bg-[var(--color-surface-hover)]"
              >
                <ChevronLeft className="w-3 h-3" />
              </button>
              <div className="px-2 font-medium">
                Page {table.getState().pagination.pageIndex + 1} of {table.getPageCount()}
              </div>
              <button
                onClick={() => table.nextPage()}
                disabled={!table.getCanNextPage()}
                className="p-1 rounded border border-[var(--color-border)] disabled:opacity-50 hover:bg-[var(--color-surface-hover)]"
              >
                <ChevronRight className="w-3 h-3" />
              </button>
              <button
                onClick={() => table.setPageIndex(table.getPageCount() - 1)}
                disabled={!table.getCanNextPage()}
                className="p-1 rounded border border-[var(--color-border)] disabled:opacity-50 hover:bg-[var(--color-surface-hover)]"
              >
                <ChevronsRight className="w-3 h-3" />
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
