import React from 'react'

interface PaginationProps {
  currentPage: number
  totalPages: number
  onPageChange: (page: number) => void
}

export default function Pagination({ currentPage, totalPages, onPageChange }: PaginationProps) {
  const pages = []
  const startPage = Math.max(1, currentPage - 2)
  const endPage = Math.min(totalPages, currentPage + 2)

  if (startPage > 1) {
    pages.push(1)
    if (startPage > 2) pages.push('...')
  }

  for (let i = startPage; i <= endPage; i++) {
    pages.push(i)
  }

  if (endPage < totalPages) {
    if (endPage < totalPages - 1) pages.push('...')
    pages.push(totalPages)
  }

  return (
    <div className="flex justify-center items-center gap-2">
      {/* 上一页 */}
      <button
        onClick={() => onPageChange(currentPage - 1)}
        disabled={currentPage === 1}
        className="px-3 py-2 rounded-md text-sm font-medium text-gray-700 bg-white border border-gray-300 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
      >
        上一页
      </button>

      {/* 页码 */}
      {pages.map((page, index) => (
        <React.Fragment key={index}>
          {page === '...' ? (
            <span className="px-2 py-2 text-gray-500">...</span>
          ) : (
            <button
              onClick={() => onPageChange(page as number)}
              className={`px-3 py-2 rounded-md text-sm font-medium ${
                page === currentPage
                  ? 'bg-primary text-white'
                  : 'text-gray-700 bg-white border border-gray-300 hover:bg-gray-50'
              }`}
            >
              {page}
            </button>
          )}
        </React.Fragment>
      ))}

      {/* 下一页 */}
      <button
        onClick={() => onPageChange(currentPage + 1)}
        disabled={currentPage === totalPages}
        className="px-3 py-2 rounded-md text-sm font-medium text-gray-700 bg-white border border-gray-300 hover:bg-gray-50 disabled:opacity-50 disabled:cursor-not-allowed"
      >
        下一页
      </button>
    </div>
  )
}
