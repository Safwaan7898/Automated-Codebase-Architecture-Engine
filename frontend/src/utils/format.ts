/**
 * Helper to format byte counts into human-readable file sizes.
 * 1024-based, 1 decimal place, units B/KB/MB/GB/TB.
 * Example: 102760448 -> "98.0 MB"
 */
export function formatFileSize(bytes: number): string {
  if (bytes === null || bytes === undefined || isNaN(bytes) || bytes < 0) {
    return '0.0 B'
  }
  const units = ['B', 'KB', 'MB', 'GB', 'TB']
  let unitIndex = 0
  let size = bytes
  while (size >= 1024 && unitIndex < units.length - 1) {
    size /= 1024
    unitIndex++
  }
  return `${size.toFixed(1)} ${units[unitIndex]}`
}
