import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import JSZip from 'jszip'
import {
  FolderGit2,
  FolderOpen,
  FileArchive,
  Code2,
  ArrowRight,
  Terminal,
  AlertCircle,
  Loader2,
  Activity,
  Zap,
  Globe,
  XCircle,
} from 'lucide-react'
import { api } from '../api/client'
import { useAnalysisContext } from '../contexts/AnalysisContext'
import { formatFileSize } from '../utils/format'

type IngestTab = 'git' | 'local' | 'archive' | 'folder' | 'snippet'

const IGNORED_DIR_NAMES = new Set([
  'node_modules',
  '.git',
  '.svn',
  '.hg',
  '__pycache__',
  '.pytest_cache',
  '.ruff_cache',
  '.mypy_cache',
  '.tox',
  'venv',
  '.venv',
  'env',
  '.env',
  '.virtualenv',
  '.idea',
  '.vscode',
  'build',
  'dist',
  'out',
  'target',
  'bin',
  'obj',
  '.output',
  '.coverage',
  'htmlcov',
])

const IGNORED_FILE_EXTENSIONS = new Set([
  '.pyc',
  '.pyo',
  '.pyd',
  '.class',
  '.o',
  '.so',
  '.dll',
  '.dylib',
  '.exe',
])

const IGNORED_FILE_NAMES = new Set([
  '.ds_store',
  'thumbs.db',
  'desktop.ini',
])

function isIgnoredFile(relPath: string): boolean {
  const normalized = relPath.replace(/\\/g, '/')
  const segments = normalized.split('/')
  for (let i = 0; i < segments.length - 1; i++) {
    if (IGNORED_DIR_NAMES.has(segments[i].toLowerCase())) {
      return true
    }
  }
  const filename = segments[segments.length - 1].toLowerCase()
  if (IGNORED_FILE_NAMES.has(filename)) return true
  for (const ext of IGNORED_FILE_EXTENSIONS) {
    if (filename.endsWith(ext)) return true
  }
  return false
}

// Recursively traverse dropped Directory Entries
async function readEntriesFromDataTransfer(items: DataTransferItemList): Promise<File[]> {
  const files: File[] = []

  async function traverseEntry(entry: any, currentPath: string): Promise<void> {
    if (entry.isFile) {
      return new Promise<void>((resolve, reject) => {
        entry.file((file: File) => {
          const pathWithFolder = currentPath ? `${currentPath}/${file.name}` : file.name
          Object.defineProperty(file, 'webkitRelativePath', {
            value: pathWithFolder,
            writable: true,
          })
          files.push(file)
          resolve()
        }, reject)
      })
    } else if (entry.isDirectory) {
      const dirReader = entry.createReader()
      const readBatch = (): Promise<any[]> =>
        new Promise((resolve, reject) => {
          dirReader.readEntries(resolve, reject)
        })

      let entries: any[] = []
      let batch: any[]
      do {
        batch = await readBatch()
        entries = entries.concat(batch)
      } while (batch.length > 0)

      for (const child of entries) {
        await traverseEntry(child, currentPath ? `${currentPath}/${entry.name}` : entry.name)
      }
    }
  }

  for (let i = 0; i < items.length; i++) {
    const item = items[i]
    const entry = item.webkitGetAsEntry ? item.webkitGetAsEntry() : null
    if (entry) {
      await traverseEntry(entry, '')
    } else {
      const file = item.getAsFile?.()
      if (file) files.push(file)
    }
  }
  return files
}

export function IngestionPage() {
  const navigate = useNavigate()
  const { analyzeLiveCodebase, pollIngestJob, loadSample } = useAnalysisContext()

  const [activeTab, setActiveTab] = useState<IngestTab>('git')
  const [gitUrl, setGitUrl] = useState('')
  const [gitBranch, setGitBranch] = useState('main')
  const [gitToken, setGitToken] = useState('')
  const [localPath, setLocalPath] = useState('')
  const [language, setLanguage] = useState<'python' | 'java' | 'auto'>('auto')
  const [includeTests, setIncludeTests] = useState(false)
  // AI toggle — OFF by default; user must explicitly consent
  const [aiEnabled, setAiEnabled] = useState(false)
  const [scanDetails, setScanDetails] = useState<{
    nodeCount?: number
    edgeCount?: number
    filesExcluded?: number
    cycles?: number
  } | null>(null)
  const [snippetCode, setSnippetCode] = useState(
    `import sqlite3

class UserService:
    def __init__(self, db_path: str):
        self.conn = sqlite3.connect(db_path)

    def find_user(self, username: str):
        cursor = self.conn.cursor()
        query = f"SELECT * FROM users WHERE username = '{username}'"
        return cursor.execute(query).fetchall()
`
  )

  const [archiveFile, setArchiveFile] = useState<File | null>(null)
  const [archiveError, setArchiveError] = useState<string | null>(null)
  const [isDragOver, setIsDragOver] = useState(false)

  // Folder tab states
  const [folderFiles, setFolderFiles] = useState<File[]>([])
  const [inScopeFolderFiles, setInScopeFolderFiles] = useState<File[]>([])
  const [folderStats, setFolderStats] = useState<{
    folderName: string
    fileCount: number
    ignoredCount: number
    totalSize: number
  } | null>(null)
  const [folderError, setFolderError] = useState<string | null>(null)
  const [isFolderDragOver, setIsFolderDragOver] = useState(false)
  const folderInputRef = useRef<HTMLInputElement | null>(null)

  const [hasStartedRun, setHasStartedRun] = useState(false)
  const [loading, setLoading] = useState(false)
  const [progress, setProgress] = useState(0)
  const [uploadProgress, setUploadProgress] = useState(0)
  const [isUploading, setIsUploading] = useState(false)
  const [pipelineStage, setPipelineStage] = useState<'idle' | 'uploading' | 'extracting' | 'parsing' | 'analysing' | 'done'>('idle')
  const [statusLog, setStatusLog] = useState<string[]>([])
  const [error, setError] = useState<string | null>(null)
  const [maxUploadSizeMb, setMaxUploadSizeMb] = useState(100)
  const [allowLocalIngestion, setAllowLocalIngestion] = useState(false)
  const [allowedExtensions, setAllowedExtensions] = useState<string[]>([
    '.zip',
    '.tar.gz',
    '.tgz',
    '.tar',
  ])

  const abortControllerRef = useRef<AbortController | null>(null)

  useEffect(() => {
    api
      .getIngestConfig()
      .then((cfg) => {
        if (cfg.max_upload_size_mb) setMaxUploadSizeMb(cfg.max_upload_size_mb)
        if (cfg.allowed_extensions?.length) setAllowedExtensions(cfg.allowed_extensions)
        setAllowLocalIngestion(Boolean(cfg.allow_local_ingestion))
      })
      .catch(() => {})
  }, [])

  const addLog = (msg: string) => {
    setStatusLog((prev) => [...prev, `[${new Date().toLocaleTimeString()}] ${msg}`])
  }

  const validateArchive = (file: File): { valid: boolean; error?: string } => {
    const lowerName = file.name.toLowerCase()
    const validExts = allowedExtensions
    const hasValidExt = validExts.some((ext) => lowerName.endsWith(ext))
    if (!hasValidExt) {
      return { valid: false, error: 'Only .zip, .tar.gz, .tgz or .tar archives are supported' }
    }
    const maxSizeBytes = maxUploadSizeMb * 1024 * 1024
    if (file.size > maxSizeBytes) {
      const sizeMb = (file.size / (1024 * 1024)).toFixed(1)
      return { valid: false, error: `Archive is ${sizeMb} MB; the limit is ${maxUploadSizeMb} MB.` }
    }
    return { valid: true }
  }

  const handleArchiveFileSelect = (file: File) => {
    const val = validateArchive(file)
    if (!val.valid) {
      setArchiveError(val.error || 'Invalid file format')
      setArchiveFile(null)
      setError(val.error || 'Invalid file format')
    } else {
      setArchiveError(null)
      setError(null)
      setArchiveFile(file)
    }
  }

  const handleFolderFiles = (files: File[]) => {
    if (!files || files.length === 0) {
      setFolderFiles([])
      setInScopeFolderFiles([])
      setFolderStats(null)
      setFolderError(null)
      return
    }

    // Derive folder name from webkitRelativePath of first file if available
    let folderName = 'project'
    for (const f of files) {
      const rel = f.webkitRelativePath || ''
      if (rel) {
        const parts = rel.replace(/\\/g, '/').split('/')
        if (parts.length > 1 && parts[0]) {
          folderName = parts[0]
          break
        }
      }
    }

    const inScope: File[] = []
    let ignoredCount = 0
    let totalSizeBytes = 0

    for (const f of files) {
      const rel = f.webkitRelativePath || f.name
      if (isIgnoredFile(rel)) {
        ignoredCount++
      } else {
        inScope.push(f)
        totalSizeBytes += f.size
      }
    }

    const maxSizeBytes = maxUploadSizeMb * 1024 * 1024

    let err: string | null = null
    if (files.length > 50000) {
      err = `Folder contains ${files.length.toLocaleString()} files, exceeding the limit of 50,000 files.`
    } else if (totalSizeBytes > maxSizeBytes) {
      err = `Folder size (${formatFileSize(totalSizeBytes)}) exceeds configured upload limit of ${maxUploadSizeMb} MB.`
    } else if (inScope.length === 0) {
      err = `Selected folder has 0 in-scope files (${ignoredCount} ignored).`
    }

    setFolderFiles(files)
    setInScopeFolderFiles(inScope)
    setFolderStats({
      folderName,
      fileCount: inScope.length,
      ignoredCount,
      totalSize: totalSizeBytes,
    })
    setFolderError(err)
    if (err) {
      setError(err)
    } else {
      setError(null)
    }
  }

  const handleClearFolder = () => {
    setFolderFiles([])
    setInScopeFolderFiles([])
    setFolderStats(null)
    setFolderError(null)
    if (folderInputRef.current) {
      folderInputRef.current.value = ''
    }
  }

  const handleTabChange = (tab: IngestTab) => {
    if (loading && abortControllerRef.current) {
      abortControllerRef.current.abort()
      abortControllerRef.current = null
    }
    setActiveTab(tab)
    setHasStartedRun(false)
    setPipelineStage('idle')
    setProgress(0)
    setUploadProgress(0)
    setStatusLog([])
    setScanDetails(null)
    setError(null)
    setLoading(false)
    setIsUploading(false)
  }

  const handleCancel = () => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort()
      addLog('Ingestion cancelled by user.')
      setError('Ingestion cancelled by user.')
      setLoading(false)
      setIsUploading(false)
      setProgress(0)
      setPipelineStage('idle')
      setHasStartedRun(false)
      abortControllerRef.current = null
    }
  }

  // Detect whether an input is a remote Git URL
  const isGitUrl = (str: string) => {
    const s = str.trim().toLowerCase()
    return (
      s.startsWith('http://') ||
      s.startsWith('https://') ||
      s.startsWith('git@') ||
      s.includes('github.com/') ||
      s.includes('gitlab.com/') ||
      s.endsWith('.git')
    )
  }

  const handleStartIngest = async () => {
    setHasStartedRun(true)
    setLoading(true)
    setError(null)
    setProgress(5)
    setUploadProgress(0)
    setIsUploading(false)
    setPipelineStage('idle')
    setStatusLog([`Initializing real-time ingestion pipeline...`])

    const controller = new AbortController()
    abortControllerRef.current = controller

    try {
      let finalAnalysisId: string | null = null

      const targetInput = activeTab === 'local' ? localPath.trim() : gitUrl.trim()
      const isRemoteGit = isGitUrl(targetInput)

      if (isRemoteGit || activeTab === 'git') {
        const repoUrl = isRemoteGit ? targetInput : gitUrl.trim()
        if (!repoUrl) throw new Error('Please enter a Git repository URL (e.g. https://github.com/owner/repo).')
        addLog(`Target identified as remote Git repository: "${repoUrl}"...`)
        setPipelineStage('extracting')
        setProgress(20)
        addLog(`Connecting to real backend AST analyzer for shallow clone...`)

        setPipelineStage('parsing')
        setProgress(50)
        const realData = await analyzeLiveCodebase(repoUrl, language, includeTests)
        setPipelineStage('analysing')
        setProgress(85)
        addLog(
          `AST parsing complete! Successfully mapped ${realData.node_count} components and ${realData.edge_count} dependency edges.`
        )
        if (realData.files_excluded !== undefined) {
          addLog(`Scope filter applied: ${realData.files_excluded} files excluded (tests/fixtures).`)
        }
        setScanDetails({
          nodeCount: realData.node_count,
          edgeCount: realData.edge_count,
          filesExcluded: realData.files_excluded,
          cycles: realData.cycles?.length || 0,
        })
        addLog(`Discovered ${realData.smells?.length ?? 0} architectural smells and computed cyclomatic topology.`)
        finalAnalysisId = realData.repo_id ? String(realData.repo_id) : null
        setPipelineStage('done')
        setProgress(100)
      } else if (activeTab === 'local') {
        if (!localPath.trim()) throw new Error('Please enter a local filesystem directory path.')
        addLog(`Scanning local filesystem workspace at: "${localPath}"...`)
        setPipelineStage('extracting')
        setProgress(25)
        setPipelineStage('parsing')
        setProgress(50)
        addLog(`Parsing source files into Abstract Syntax Trees...`)
        const realData = await analyzeLiveCodebase(localPath, language, includeTests)
        setPipelineStage('analysing')
        setProgress(85)
        addLog(`Identified ${realData.node_count} components and ${realData.edge_count} dependency edges.`)
        if (realData.files_excluded !== undefined) {
          addLog(`Scope filter applied: ${realData.files_excluded} files excluded (tests/fixtures).`)
        }
        setScanDetails({
          nodeCount: realData.node_count,
          edgeCount: realData.edge_count,
          filesExcluded: realData.files_excluded,
          cycles: realData.cycles?.length || 0,
        })
        addLog(`Calculated cyclomatic complexity and detected ${realData.smells?.length ?? 0} architectural smells.`)
        finalAnalysisId = realData.repo_id ? String(realData.repo_id) : null
        setPipelineStage('done')
        setProgress(100)
      } else if (activeTab === 'archive') {
        if (!archiveFile) {
          const msg = archiveError || 'Please select an archive file (.zip, .tar.gz, .tgz, .tar) first.'
          throw new Error(msg)
        }

        const val = validateArchive(archiveFile)
        if (!val.valid) {
          throw new Error(val.error)
        }

        setIsUploading(true)
        setPipelineStage('uploading')
        addLog(`Uploading archive package: ${archiveFile.name} (${formatFileSize(archiveFile.size)})...`)

        const res = await api.uploadArchive(
          archiveFile,
          (pct) => {
            setUploadProgress(pct)
            setProgress(Math.round(5 + pct * 0.35))
          },
          controller.signal,
          includeTests
        )

        setIsUploading(false)
        setPipelineStage('extracting')
        setProgress(45)
        addLog(`Archive accepted [Job: ${res.job_id}]. Extracting safely...`)

        const jobResult = await pollIngestJob(res.job_id, (msg, pct) => {
          addLog(msg)
          if (pct >= 90) setPipelineStage('analysing')
          else if (pct >= 50) setPipelineStage('parsing')
          else if (pct >= 30) setPipelineStage('extracting')
          setProgress(pct)
        })

        if (jobResult?.files_excluded !== undefined) {
          addLog(`Scope filter applied: ${jobResult.files_excluded} files excluded (tests/fixtures).`)
        }
        setScanDetails({
          nodeCount: jobResult?.node_count,
          edgeCount: jobResult?.edge_count,
          filesExcluded: jobResult?.files_excluded,
          cycles: jobResult?.cycles?.length || 0,
        })

        finalAnalysisId = res.job_id || (jobResult?.repo_id ? String(jobResult.repo_id) : null)
        setPipelineStage('done')
        setProgress(100)
      } else if (activeTab === 'folder') {
        if (!folderFiles.length || !inScopeFolderFiles.length) {
          throw new Error('Please select a project folder with source files.')
        }
        if (folderError) {
          throw new Error(folderError)
        }
        setIsUploading(true)
        setPipelineStage('uploading')
        addLog(
          `Packaging ${inScopeFolderFiles.length} files from "${folderStats?.folderName || 'folder'}" into ZIP client-side...`
        )

        const zip = new JSZip()
        for (const f of inScopeFolderFiles) {
          const relPath = f.webkitRelativePath || f.name
          zip.file(relPath, f)
        }

        addLog('Compressing folder package...')
        const zipBlob = await zip.generateAsync(
          { type: 'blob', compression: 'DEFLATE', compressionOptions: { level: 6 } },
          (meta) => {
            setUploadProgress(Math.round(meta.percent * 0.4))
          }
        )

        const zipFile = new File([zipBlob], `${folderStats?.folderName || 'project'}.zip`, {
          type: 'application/zip',
        })

        addLog(
          `Archive ready: ${zipFile.name} (${formatFileSize(zipFile.size)}). Uploading through standard archive pipeline...`
        )

        const res = await api.uploadArchive(
          zipFile,
          (pct) => {
            setUploadProgress(Math.round(40 + pct * 0.6))
            setProgress(Math.round(5 + pct * 0.35))
          },
          controller.signal,
          includeTests
        )

        setIsUploading(false)
        setPipelineStage('extracting')
        setProgress(45)
        addLog(`Folder archive accepted [Job: ${res.job_id}]. Extracting safely...`)

        const jobResult = await pollIngestJob(res.job_id, (msg, pct) => {
          addLog(msg)
          if (pct >= 90) setPipelineStage('analysing')
          else if (pct >= 50) setPipelineStage('parsing')
          else if (pct >= 30) setPipelineStage('extracting')
          setProgress(pct)
        })

        if (jobResult?.files_excluded !== undefined) {
          addLog(`Scope filter applied: ${jobResult.files_excluded} files excluded (tests/fixtures).`)
        }
        setScanDetails({
          nodeCount: jobResult?.node_count,
          edgeCount: jobResult?.edge_count,
          filesExcluded: jobResult?.files_excluded,
          cycles: jobResult?.cycles?.length || 0,
        })

        finalAnalysisId = res.job_id || (jobResult?.repo_id ? String(jobResult.repo_id) : null)
        setPipelineStage('done')
        setProgress(100)
      } else if (activeTab === 'snippet') {
        if (!snippetCode.trim()) throw new Error('Please enter code in the snippet editor.')
        addLog(`Transmitting ${language} code snippet to AST parser...`)
        setPipelineStage('parsing')
        setProgress(30)
        const res = await api.startIngestion(
          {
            source_type: 'snippet',
            code: snippetCode,
            language: language === 'auto' ? 'python' : language,
            include_tests: includeTests,
          },
          controller.signal
        )
        addLog(`Snippet parsed [Job: ${res.job_id}]. Generating AST node topology...`)
        const jobResult = await pollIngestJob(res.job_id, (msg, pct) => {
          addLog(msg)
          if (pct >= 90) setPipelineStage('analysing')
          else if (pct >= 50) setPipelineStage('parsing')
          setProgress(pct)
        })
        if (jobResult?.files_excluded !== undefined) {
          addLog(`Scope filter applied: ${jobResult.files_excluded} files excluded.`)
        }
        setScanDetails({
          nodeCount: jobResult?.node_count,
          edgeCount: jobResult?.edge_count,
          filesExcluded: jobResult?.files_excluded,
          cycles: jobResult?.cycles?.length || 0,
        })
        finalAnalysisId = res.job_id || (jobResult?.repo_id ? String(jobResult.repo_id) : null)
        setPipelineStage('done')
        setProgress(100)
      }

      addLog('Real-time analysis succeeded! Redirecting to Interactive Risk & Topology Dashboard...')
      setTimeout(() => {
        if (finalAnalysisId) {
          navigate(`/dashboard?analysis=${encodeURIComponent(finalAnalysisId)}`)
        } else {
          navigate('/dashboard')
        }
      }, 700)
    } catch (err: any) {
      let msg = 'Ingestion failed. Please check parameters.'
      if (err?.name === 'CanceledError' || err?.code === 'ERR_CANCELED' || err?.name === 'AbortError') {
        msg = 'Upload cancelled by user.'
      } else if (err?.response?.data?.detail) {
        msg = typeof err.response.data.detail === 'string' ? err.response.data.detail : JSON.stringify(err.response.data.detail)
      } else if (err?.message) {
        msg = err.message
      }
      setError(msg)
      addLog(`ERROR: ${msg}`)
      setProgress(0)
      setPipelineStage('idle')
    } finally {
      setLoading(false)
      setIsUploading(false)
      abortControllerRef.current = null
    }
  }

  const getTabValidation = (): { isValid: boolean; hint?: string } => {
    if (activeTab === 'git') {
      if (!gitUrl.trim()) return { isValid: false, hint: 'Enter a Git repository URL (e.g. https://github.com/owner/repo)' }
      return { isValid: true }
    }
    if (activeTab === 'local') {
      if (!allowLocalIngestion) return { isValid: false, hint: 'Local filesystem ingestion is disabled by policy' }
      if (!localPath.trim()) return { isValid: false, hint: 'Enter a local filesystem directory path' }
      return { isValid: true }
    }
    if (activeTab === 'archive') {
      if (archiveError) return { isValid: false, hint: archiveError }
      if (!archiveFile) return { isValid: false, hint: 'Select or drop an archive file (.zip, .tar.gz)' }
      return { isValid: true }
    }
    if (activeTab === 'folder') {
      if (folderError) return { isValid: false, hint: folderError }
      if (!folderFiles.length || !inScopeFolderFiles.length) return { isValid: false, hint: 'Select or drop a project folder' }
      return { isValid: true }
    }
    if (activeTab === 'snippet') {
      if (!snippetCode.trim()) return { isValid: false, hint: 'Enter or paste code in the snippet editor' }
      return { isValid: true }
    }
    return { isValid: false }
  }

  const { isValid: isInputValid, hint: validationHint } = getTabValidation()
  const isRunDisabled = loading || !isInputValid

  return (
    <div className="space-y-6 max-w-6xl mx-auto px-4 py-6 font-sans">
      {/* ── Header ──────────────────────────────────────────────────────── */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-[var(--border)] dark:border-white/10 pb-6">
        <div>
          <div className="flex items-center gap-2">
            <span className="badge-acid text-[10px] uppercase tracking-widest inline-flex items-center gap-1">
              <Zap size={10} /> LIVE AST INGESTION
            </span>
          </div>
          <h1 className="acid-title text-3xl sm:text-4xl md:text-5xl tracking-[-0.04em] text-[var(--text)] dark:text-white mt-1">
            CODEBASE PIPELINE
          </h1>
          <p className="text-xs sm:text-sm text-[var(--text-muted)] dark:text-white/60 mt-1 max-w-2xl font-mono">
            Directly parse GitHub repos, local workspaces, ZIP archives, or code snippets to construct real-time dependency architectures.
          </p>
        </div>

        {/* Quick status pill */}
        <div className="flex items-center gap-2 bg-[var(--surface-2)]/60 dark:bg-black/60 border border-[var(--border)] dark:border-white/15 px-4 py-2 rounded-full font-mono text-xs text-[var(--text-secondary)] dark:text-white/80">
          <span className="w-2 h-2 rounded-full bg-[#CCFF00] shadow-[0_0_6px_#CCFF00]" />
          <span>REAL-TIME AST ENGINE ACTIVE</span>
        </div>
      </div>

      {/* ── Main Ingestion Card (Liquid Chrome) ─────────────────────────── */}
      <div className="liquid-card p-6 sm:p-8 relative shadow-2xl">
        {/* Source Type Selector Tabs */}
        <div className="grid grid-cols-2 sm:grid-cols-5 gap-2 mb-8 p-1.5 bg-[var(--surface-2)] dark:bg-[#050505] border border-[var(--border)] dark:border-white/10 rounded-2xl">
          {[
            { id: 'git', label: 'GITHUB / GIT', icon: <Globe size={14} /> },
            {
              id: 'local',
              label: 'LOCAL PATH',
              icon: <FolderOpen size={14} />,
              disabled: !allowLocalIngestion,
              disabledNote: 'Disabled by administrator',
              tooltip: 'Local filesystem ingestion is disabled by administrator policy.',
            },
            { id: 'archive', label: 'ZIP ARCHIVE', icon: <FileArchive size={14} /> },
            { id: 'folder', label: 'FOLDER DROP', icon: <FolderGit2 size={14} /> },
            { id: 'snippet', label: 'SNIPPET', icon: <Code2 size={14} /> },
          ].map((tab) => {
            const isDisabled = tab.disabled
            return (
              <button
                key={tab.id}
                data-testid={`tab-${tab.id}`}
                disabled={isDisabled}
                title={isDisabled ? tab.tooltip : undefined}
                onClick={() => {
                  if (isDisabled) return
                  handleTabChange(tab.id as IngestTab)
                }}
                className={`flex flex-col sm:flex-row items-center justify-center gap-1.5 py-2.5 px-3 rounded-xl text-xs font-mono tracking-wider transition-colors duration-150 ${
                  isDisabled
                    ? 'opacity-40 cursor-not-allowed bg-zinc-900/30 text-zinc-500 border border-zinc-800'
                    : activeTab === tab.id
                    ? 'bg-gradient-to-r from-white via-zinc-200 to-white text-black font-extrabold shadow-[0_0_15px_rgba(204,255,0,0.5)] border border-[#CCFF00]'
                    : 'text-[var(--text-muted)] hover:text-[var(--text)] hover:bg-[var(--surface)] dark:text-white/60 dark:hover:text-white dark:hover:bg-white/5'
                }`}
              >
                <div className="flex items-center gap-1.5">
                  {tab.icon}
                  <span>{tab.label}</span>
                </div>
                {isDisabled && (
                  <span className="text-[8px] px-1.5 py-0.5 rounded bg-amber-950/40 text-amber-400 border border-amber-500/30 font-mono tracking-tight" title={tab.tooltip}>
                    Disabled
                  </span>
                )}
              </button>
            )
          })}
        </div>

        {/* Input Parameters by Tab */}
        <div className="space-y-6">
          {/* TAB 1: GIT */}
          {activeTab === 'git' && (
            <div className="space-y-4">
              <div>
                <label className="block text-[11px] font-mono tracking-wider text-[var(--text-secondary)] dark:text-white/70 mb-1.5 uppercase">
                  Git Repository URL (Public or Private)
                </label>
                <div className="relative">
                  <input
                    type="text"
                    value={gitUrl}
                    onChange={(e) => setGitUrl(e.target.value)}
                    placeholder="https://github.com/username/repository"
                    className="w-full bg-[var(--surface)] dark:bg-black/80 border border-[var(--border)] dark:border-white/20 focus:border-[#CCFF00] rounded-xl px-4 py-3 text-xs text-[var(--text)] placeholder-[var(--placeholder)] dark:text-white outline-none font-mono"
                  />
                  <span className="absolute right-3 top-3 text-[10px] font-mono text-[var(--accent-text)] dark:text-[#CCFF00]">
                    SHALLOW CLONE --DEPTH 1
                  </span>
                </div>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="block text-[11px] font-mono tracking-wider text-[var(--text-secondary)] dark:text-white/70 mb-1.5 uppercase">
                    Branch / Tag (Optional)
                  </label>
                  <input
                    type="text"
                    value={gitBranch}
                    onChange={(e) => setGitBranch(e.target.value)}
                    placeholder="main or master"
                    className="w-full bg-[var(--surface)] dark:bg-black/80 border border-[var(--border)] dark:border-white/20 focus:border-[#CCFF00] rounded-xl px-4 py-2.5 text-xs text-[var(--text)] placeholder-[var(--placeholder)] dark:text-white outline-none font-mono"
                  />
                </div>
                <div>
                  <label className="block text-[11px] font-mono tracking-wider text-[var(--text-secondary)] dark:text-white/70 mb-1.5 uppercase">
                    Personal Access Token (For Private Repos)
                  </label>
                  <input
                    type="password"
                    value={gitToken}
                    onChange={(e) => setGitToken(e.target.value)}
                    placeholder="ghp_••••••••••••••••"
                    className="w-full bg-[var(--surface)] dark:bg-black/80 border border-[var(--border)] dark:border-white/20 focus:border-[#CCFF00] rounded-xl px-4 py-2.5 text-xs text-[var(--text)] placeholder-[var(--placeholder)] dark:text-white outline-none font-mono"
                  />
                </div>
              </div>
            </div>
          )}

          {/* TAB 2: LOCAL PATH */}
          {activeTab === 'local' && (
            <div className="space-y-4">
              {!allowLocalIngestion ? (
                <div data-testid="local-path-disabled-note" className="p-4 rounded-xl bg-amber-500/10 border border-amber-500/30 text-amber-300 font-mono text-xs flex items-center gap-3">
                  <AlertCircle size={18} className="flex-shrink-0 text-amber-400" />
                  <div>
                    <strong className="block text-amber-400 font-bold mb-0.5">Disabled by administrator</strong>
                    <span className="text-white/80">Local filesystem path ingestion is disabled by administrator security policy. Please ingest via GitHub repository URL, ZIP archive, or Snippet instead.</span>
                  </div>
                </div>
              ) : (
                <div>
                  <label className="block text-[11px] font-mono tracking-wider text-[var(--text-secondary)] dark:text-white/70 mb-1.5 uppercase">
                    Server Directory Path
                  </label>
                  <input
                    type="text"
                    value={localPath}
                    onChange={(e) => setLocalPath(e.target.value)}
                    placeholder="e.g. samples/python-flask"
                    className="w-full bg-[var(--surface)] dark:bg-black/80 border border-[var(--border)] dark:border-white/20 focus:border-[#CCFF00] rounded-xl px-4 py-3 text-xs text-[var(--text)] placeholder-[var(--placeholder)] dark:text-white outline-none font-mono"
                  />
                </div>
              )}
            </div>
          )}

          {/* TAB 3: ARCHIVE */}
          {activeTab === 'archive' && (
            <div className="space-y-4">
              <div
                onDragOver={(e) => {
                  e.preventDefault()
                  setIsDragOver(true)
                }}
                onDragLeave={(e) => {
                  e.preventDefault()
                  setIsDragOver(false)
                }}
                onDrop={(e) => {
                  e.preventDefault()
                  setIsDragOver(false)
                  if (e.dataTransfer.files?.[0]) handleArchiveFileSelect(e.dataTransfer.files[0])
                }}
                className={`border-2 border-dashed rounded-2xl p-8 text-center transition-colors ${
                  isDragOver
                    ? 'border-[#CCFF00] bg-[#CCFF00]/10'
                    : archiveError
                    ? 'border-red-500/60 bg-red-950/20'
                    : 'border-[var(--border)] dark:border-white/20 hover:border-[#CCFF00] bg-[var(--surface-2)]/40 dark:bg-black/40'
                }`}
              >
                <FileArchive size={36} className={`mx-auto mb-3 ${archiveError ? 'text-red-400' : 'text-[var(--accent-text)] dark:text-[#CCFF00]'}`} />
                <label className="cursor-pointer block">
                  <span className="chrome-btn px-4 py-2 text-xs font-bold inline-block mb-2">
                    SELECT .ZIP OR .TAR.GZ FILE
                  </span>
                  <input
                    type="file"
                    data-testid="archive-file-input"
                    accept=".zip,.tar.gz,.tgz,.tar"
                    className="hidden"
                    onChange={(e) => {
                      if (e.target.files?.[0]) handleArchiveFileSelect(e.target.files[0])
                    }}
                  />
                </label>
                <p className="text-xs font-mono text-[var(--text-muted)] dark:text-white/60 mt-1">
                  {archiveFile ? (
                    <span className="text-[var(--accent-text)] dark:text-[#CCFF00] font-bold" data-testid="selected-file-info">
                      Selected: {archiveFile.name} ({formatFileSize(archiveFile.size)})
                    </span>
                  ) : (
                    <span>Drag and drop archive here or click above. Limit: <strong data-testid="configured-upload-limit" className="text-[var(--text)] dark:text-white">{maxUploadSizeMb} MB</strong> (.zip, .tar.gz, .tgz, .tar)</span>
                  )}
                </p>
                <div data-testid="configured-upload-limit-badge" className="mt-2 inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-[var(--surface-2)] dark:bg-white/5 border border-[var(--border)] dark:border-white/10 text-[11px] font-mono text-zinc-700 dark:text-zinc-200">
                  <span>Configured upload limit:</span>
                  <span className="font-bold text-[var(--accent-text)] dark:text-[#CCFF00]">{maxUploadSizeMb} MB</span>
                  <span className="text-[10px] text-zinc-600 dark:text-zinc-300 font-mono">(ARCHLENS_MAX_UPLOAD_SIZE_MB)</span>
                </div>
                {archiveError && (
                  <div data-testid="archive-inline-error" className="text-red-400 font-bold text-xs mt-2 flex items-center justify-center gap-1.5 font-mono">
                    <AlertCircle size={14} className="shrink-0" />
                    <span>{archiveError}</span>
                  </div>
                )}
              </div>
            </div>
          )}

          {/* TAB 4: FOLDER */}
          {activeTab === 'folder' && (
            <div className="space-y-4">
              <div
                onDragOver={(e) => {
                  e.preventDefault()
                  setIsFolderDragOver(true)
                }}
                onDragLeave={() => setIsFolderDragOver(false)}
                onDrop={async (e) => {
                  e.preventDefault()
                  setIsFolderDragOver(false)
                  if (e.dataTransfer.items && e.dataTransfer.items.length > 0) {
                    try {
                      const extractedFiles = await readEntriesFromDataTransfer(e.dataTransfer.items)
                      if (extractedFiles.length > 0) {
                        handleFolderFiles(extractedFiles)
                        return
                      }
                    } catch {
                      // fallback
                    }
                  }
                  if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
                    handleFolderFiles(Array.from(e.dataTransfer.files))
                  }
                }}
                className={`border-2 border-dashed rounded-2xl p-8 text-center transition-colors ${
                  isFolderDragOver
                    ? 'border-[#CCFF00] bg-[#CCFF00]/10'
                    : folderError
                    ? 'border-red-500/60 bg-red-950/20'
                    : 'border-[var(--border)] dark:border-white/20 hover:border-[#CCFF00] bg-[var(--surface-2)]/40 dark:bg-black/40'
                }`}
              >
                <FolderGit2
                  size={36}
                  className={`mx-auto mb-3 ${
                    folderError ? 'text-red-400' : 'text-[var(--accent-text)] dark:text-[#CCFF00]'
                  }`}
                />
                <label className="cursor-pointer block">
                  <span className="chrome-btn px-4 py-2 text-xs font-bold inline-block mb-2">
                    SELECT ENTIRE PROJECT FOLDER
                  </span>
                  <input
                    ref={folderInputRef}
                    type="file"
                    data-testid="folder-input"
                    {...({ webkitdirectory: '', directory: '' } as any)}
                    multiple
                    className="hidden"
                    onChange={(e) => {
                      if (e.target.files && e.target.files.length > 0) {
                        handleFolderFiles(Array.from(e.target.files))
                      }
                      e.target.value = ''
                    }}
                  />
                </label>

                {folderStats ? (
                  <div
                    data-testid="folder-info"
                    className="mt-4 max-w-md mx-auto p-4 rounded-xl bg-[var(--surface)] dark:bg-black/70 border border-[var(--border)] dark:border-white/10 text-left space-y-3"
                  >
                    <div className="flex items-center justify-between border-b border-[var(--border)] dark:border-white/10 pb-2">
                      <div className="flex items-center gap-2">
                        <FolderGit2 size={16} className="text-[var(--accent-text)] dark:text-[#CCFF00]" />
                        <span className="font-mono font-bold text-xs text-[var(--text)]" data-testid="folder-name">
                          {folderStats.folderName}
                        </span>
                      </div>
                      <button
                        type="button"
                        onClick={handleClearFolder}
                        className="text-[11px] font-mono text-[var(--text-muted)] hover:text-red-400 cursor-pointer underline"
                      >
                        Change
                      </button>
                    </div>

                    <div className="grid grid-cols-3 gap-2 text-xs font-mono">
                      <div>
                        <span className="text-[10px] text-[var(--text-muted)] block uppercase">In-Scope Files</span>
                        <span className="font-bold text-[var(--accent-text)] dark:text-[#CCFF00]" data-testid="folder-file-count">
                          {folderStats.fileCount}
                        </span>
                      </div>
                      <div>
                        <span className="text-[10px] text-[var(--text-muted)] block uppercase">Ignored</span>
                        <span className="font-bold text-zinc-500" data-testid="folder-ignored-count">
                          {folderStats.ignoredCount}
                        </span>
                      </div>
                      <div>
                        <span className="text-[10px] text-[var(--text-muted)] block uppercase">Total Size</span>
                        <span className="font-bold text-[var(--text)]" data-testid="folder-total-size">
                          {formatFileSize(folderStats.totalSize)}
                        </span>
                      </div>
                    </div>

                    {folderError && (
                      <div data-testid="folder-inline-error" className="text-red-400 font-bold text-xs mt-2 flex items-center gap-1.5 font-mono">
                        <AlertCircle size={14} className="shrink-0" />
                        <span>{folderError}</span>
                      </div>
                    )}
                  </div>
                ) : (
                  <p className="text-xs font-mono text-[var(--text-muted)] dark:text-white/60 mt-1">
                    Drag and drop project folder here or click above to select. Limit: <strong className="text-[var(--text)] dark:text-white">{maxUploadSizeMb} MB</strong>
                  </p>
                )}
              </div>
            </div>
          )}

          {/* TAB 5: SNIPPET */}
          {activeTab === 'snippet' && (
            <div className="space-y-4">
              <div>
                <label className="block text-[11px] font-mono tracking-wider text-[var(--text-secondary)] dark:text-white/70 mb-1.5 uppercase">
                  Paste Source Code Snippet
                </label>
                <textarea
                  rows={8}
                  value={snippetCode}
                  onChange={(e) => setSnippetCode(e.target.value)}
                  className="w-full bg-[var(--surface)] dark:bg-black/90 border border-[var(--border)] dark:border-white/20 focus:border-[#CCFF00] rounded-xl p-4 text-xs font-mono text-[var(--text)] outline-none leading-relaxed"
                />
              </div>
            </div>
          )}

          {/* Optional Sample Presets */}
          <div className="pt-4 border-t border-[var(--border)] dark:border-white/10 flex flex-wrap items-center justify-between gap-3">
            <span className="text-[11px] font-mono text-[var(--text-muted)] dark:text-white/60 uppercase">
              Optional Sample Presets:
            </span>
            <div className="flex flex-wrap gap-2">
              <button
                type="button"
                onClick={() => {
                  loadSample('flask')
                  navigate('/dashboard')
                }}
                className="px-2.5 py-1 rounded-lg text-[10px] font-mono border border-[var(--border)] dark:border-white/15 hover:border-[#CCFF00] hover:text-[#CCFF00] transition-colors bg-[var(--surface-2)] dark:bg-white/5 cursor-pointer"
              >
                Flask Microservice
              </button>
              <button
                type="button"
                onClick={() => {
                  loadSample('spring')
                  navigate('/dashboard')
                }}
                className="px-2.5 py-1 rounded-lg text-[10px] font-mono border border-[var(--border)] dark:border-white/15 hover:border-[#CCFF00] hover:text-[#CCFF00] transition-colors bg-[var(--surface-2)] dark:bg-white/5 cursor-pointer"
              >
                Spring Cloud App
              </button>
              <button
                type="button"
                onClick={() => {
                  loadSample('vulnerable')
                  navigate('/dashboard')
                }}
                className="px-2.5 py-1 rounded-lg text-[10px] font-mono border border-[var(--border)] dark:border-white/15 hover:border-red-400 hover:text-red-400 transition-colors bg-[var(--surface-2)] dark:bg-white/5 cursor-pointer"
              >
                Vulnerable Demo
              </button>
            </div>
          </div>

          {/* Language Selector & Scope Filter Toggle */}
          <div className="flex flex-wrap items-center justify-between gap-4 pt-4 border-t border-[var(--border)] dark:border-white/10">
            <div className="flex flex-wrap items-center gap-6">
              <div className="flex items-center gap-3">
                <span className="text-[11px] font-mono text-[var(--text-muted)] dark:text-white/60 uppercase">Language Parser:</span>
                <div className="flex gap-1.5">
                  {(['auto', 'python', 'java'] as const).map((lang) => (
                    <button
                      key={lang}
                      type="button"
                      onClick={() => setLanguage(lang)}
                      className={`px-3 py-1 rounded-lg text-xs font-mono uppercase transition-colors duration-150 ${
                        language === lang
                          ? 'bg-[#CCFF00] text-black font-bold shadow-[0_0_10px_rgba(204,255,0,0.5)]'
                          : 'bg-[var(--surface-2)] dark:bg-black/60 text-[var(--text-muted)] hover:text-[var(--text)] dark:text-white/60 dark:hover:text-white border border-[var(--border)] dark:border-white/10'
                      }`}
                    >
                      {lang}
                    </button>
                  ))}
                </div>
              </div>

              {/* Include tests toggle */}
              <div className="flex items-center gap-2">
                <label className="flex items-center gap-2 cursor-pointer select-none font-mono text-xs text-[var(--text-secondary)] dark:text-white/80">
                  <input
                    type="checkbox"
                    data-testid="include-tests-toggle"
                    checked={includeTests}
                    onChange={(e) => setIncludeTests(e.target.checked)}
                    className="w-4 h-4 rounded border-zinc-600 text-[#CCFF00] focus:ring-[#CCFF00] focus:ring-offset-0 bg-black/40 cursor-pointer accent-[#CCFF00]"
                  />
                  <span className="font-bold">INCLUDE TESTS</span>
                </label>
                <span className="text-[10px] text-zinc-600 dark:text-zinc-300 font-mono">
                  ({includeTests ? 'Included' : 'Excluded from scope'})
                </span>
              </div>

              {/* AI Enhancement Toggle — default OFF, explicit consent required */}
              <div className="flex flex-col gap-1.5">
                <label
                  className="flex items-center gap-2 cursor-pointer select-none font-mono text-xs text-[var(--text-secondary)] dark:text-white/80"
                  data-testid="ai-toggle-label"
                >
                  <input
                    type="checkbox"
                    data-testid="ai-enabled-toggle"
                    id="ai-enabled-toggle"
                    checked={aiEnabled}
                    onChange={(e) => setAiEnabled(e.target.checked)}
                    className="w-4 h-4 rounded border-zinc-600 text-[#CCFF00] focus:ring-[#CCFF00] focus:ring-offset-0 bg-black/40 cursor-pointer accent-[#CCFF00]"
                    aria-label="Enable AI-powered analysis features"
                  />
                  <span className="font-bold flex items-center gap-1.5" style={{ color: aiEnabled ? 'var(--accent)' : undefined }}>
                    AI-GENERATED INSIGHTS
                    <span className="text-[10px] font-mono font-normal opacity-75">(AI-generated)</span>
                  </span>
                  <span
                    className="text-[9px] px-1.5 py-0.5 rounded font-bold uppercase tracking-widest"
                    style={{
                      background: aiEnabled ? 'rgba(198,244,50,0.15)' : 'var(--surface-2)',
                      color: aiEnabled ? 'var(--accent)' : 'var(--text-muted)',
                      border: `1px solid ${aiEnabled ? 'rgba(198,244,50,0.3)' : 'var(--surface-border)'}`,
                    }}
                  >
                    {aiEnabled ? 'ON' : 'OFF (default)'}
                  </span>
                </label>

                {/* Consent notice — always visible when AI is ON */}
                {aiEnabled && (
                  <div
                    className="rounded-xl px-3 py-2.5 text-[10px] font-mono leading-relaxed max-w-lg"
                    style={{
                      background: 'rgba(198,244,50,0.05)',
                      border: '1px solid rgba(198,244,50,0.2)',
                      color: 'var(--text-secondary)',
                    }}
                    role="alert"
                    aria-label="AI consent notice"
                    data-testid="ai-consent-notice"
                  >
                    <strong style={{ color: 'var(--accent)' }}>AI consent notice: </strong>
                    Sanitised code snippets (file paths, imports, symbol names — no secrets or business logic) will be sent
                    to an external AI provider to generate explanations and suggestions.{' '}
                    <strong>Gemini is automatically skipped</strong> for private repositories, ZIP archives, and folder
                    uploads unless your admin has enabled{' '}
                    <code className="text-[9px]">ARCHLENS_AI_ALLOW_TRAINING_PROVIDERS=true</code>.
                    AI annotations never alter scores, grades, findings, or graph structure.
                  </div>
                )}
              </div>
            </div>

            {/* Launch Ingestion Action & Cancel Button */}
            <div className="flex flex-wrap items-center gap-3">
              {!isInputValid && validationHint && !loading && (
                <span
                  data-testid="run-validation-hint"
                  className="text-xs font-mono text-amber-900 dark:text-amber-300 font-semibold"
                >
                  {validationHint}
                </span>
              )}

              {loading && (
                <button
                  type="button"
                  data-testid="ingestion-cancel-button"
                  onClick={handleCancel}
                  className="px-5 py-3 rounded-xl border border-red-500/50 hover:border-red-500 text-red-400 hover:text-red-300 bg-red-950/20 text-xs font-mono font-bold tracking-wider transition-colors cursor-pointer flex items-center gap-1.5"
                >
                  <XCircle size={14} />
                  <span>CANCEL</span>
                </button>
              )}

              <button
                onClick={handleStartIngest}
                disabled={isRunDisabled}
                data-testid="run-ingestion-button"
                className="chrome-btn px-8 py-3 text-xs font-black tracking-widest flex items-center gap-2 disabled:opacity-40 disabled:cursor-not-allowed cursor-pointer"
              >
                {loading ? (
                  <>
                    <Loader2 size={14} className="animate-spin text-black" />
                    <span>{isUploading ? 'UPLOADING...' : 'PARSING CODEBASE...'}</span>
                  </>
                ) : (
                  <>
                    <span>RUN REAL-TIME INGESTION</span>
                    <ArrowRight size={14} />
                  </>
                )}
              </button>
            </div>
          </div>
        </div>
      </div>

      {/* ── Real-Time Progress & Telemetry Terminal ───────────────────────── */}
      {hasStartedRun && pipelineStage !== 'idle' && (
        <motion.div
          initial={{ opacity: 0, y: 15 }}
          animate={{ opacity: 1, y: 0 }}
          className="liquid-card p-6 border border-[var(--border)] dark:border-white/15"
        >
          {/* Stage progression indicator */}
          <div className="mb-5 flex flex-wrap items-center justify-between gap-2 p-3 rounded-xl bg-zinc-100 dark:bg-black/60 border border-zinc-300 dark:border-white/10 text-[10px] font-mono uppercase tracking-wider">
            {(['uploading', 'extracting', 'parsing', 'analysing', 'done'] as const).map((stage, idx, arr) => {
              const stagesOrder = ['uploading', 'extracting', 'parsing', 'analysing', 'done']
              const currentIdx = stagesOrder.indexOf(pipelineStage)
              const thisIdx = stagesOrder.indexOf(stage)
              const isPast = currentIdx > thisIdx
              const isCurrent = currentIdx === thisIdx

              return (
                <div key={stage} className="flex items-center gap-2">
                  <span
                    className={`px-2.5 py-1 rounded-md font-bold transition-colors ${
                      isCurrent
                        ? 'bg-zinc-900 text-white font-extrabold shadow-sm dark:bg-[#CCFF00] dark:text-black dark:shadow-[0_0_10px_rgba(204,255,0,0.6)]'
                        : isPast
                        ? 'text-emerald-800 bg-emerald-100 border border-emerald-400 dark:text-[#CCFF00] dark:bg-[#CCFF00]/10 dark:border-[#CCFF00]/40'
                        : 'text-zinc-600 bg-zinc-200/60 border border-zinc-300 dark:text-zinc-400 dark:bg-white/5 dark:border-white/10'
                    }`}
                  >
                    {stage === 'uploading' && uploadProgress > 0 ? `UPLOADING (${uploadProgress}%)` : stage}
                  </span>
                  {idx < arr.length - 1 && <span className="text-zinc-400 dark:text-white/40">→</span>}
                </div>
              )
            })}
          </div>

          {/* Progress bar */}
          <div className="mb-4">
            <div className="flex justify-between text-xs font-mono mb-2">
              <span className="text-[var(--accent-text)] dark:text-[#CCFF00] font-bold flex items-center gap-1.5">
                <Activity size={12} className={loading ? 'animate-pulse' : ''} />
                <span>{isUploading ? `UPLOADING ARCHIVE TO SERVER (${uploadProgress}%)` : 'PIPELINE EXECUTION STATUS'}</span>
              </span>
              <span className="text-[var(--text)] dark:text-white font-mono">{progress}%</span>
            </div>
            <div className="w-full h-2 bg-[var(--surface-2)] dark:bg-black rounded-full overflow-hidden border border-[var(--border)] dark:border-white/10">
              <div
                className="h-full bg-gradient-to-r from-[#CCFF00] via-[#FFFFFF] to-[#FF00FF] transition-[width] duration-300 ease-out shadow-[0_0_12px_#CCFF00]"
                style={{ width: `${progress}%` }}
              />
            </div>
          </div>

          {/* Terminal Console */}
          <div className="bg-[var(--surface-2)] dark:bg-[#050505] rounded-xl border border-[var(--border)] dark:border-white/10 p-4 font-mono text-[11px] max-h-56 overflow-y-auto space-y-1.5 shadow-inner">
            <div className="flex items-center gap-2 text-[var(--text-muted)] dark:text-white/40 pb-2 mb-2 border-b border-[var(--border)] dark:border-white/5">
              <Terminal size={12} />
              <span>ARCHLENS_AST_ENGINE_OUTPUT_STREAM</span>
            </div>
            {statusLog.map((log, idx) => (
              <div
                key={idx}
                className={
                  log.includes('ERROR')
                    ? 'text-red-400 font-bold'
                    : log.includes('succeeded') || log.includes('complete')
                    ? 'text-[var(--accent-text)] dark:text-[#CCFF00] font-bold'
                    : 'text-[var(--text)] dark:text-white/80'
                }
              >
                {log}
              </div>
            ))}
          </div>

          {/* Scan Details Summary */}
          {scanDetails && (
            <div
              data-testid="scan-details-panel"
              className="mt-4 p-3.5 rounded-xl bg-[var(--surface-2)] dark:bg-black/60 border border-[var(--border)] dark:border-white/10 flex flex-wrap items-center justify-between text-xs font-mono gap-3"
            >
              <div className="flex items-center gap-3">
                <span><strong>{scanDetails.nodeCount ?? 0}</strong> components</span>
                <span className="opacity-40">•</span>
                <span><strong>{scanDetails.edgeCount ?? 0}</strong> edges</span>
                <span className="opacity-40">•</span>
                <span data-testid="files-excluded-scan-details" className="text-[var(--accent-text)] dark:text-[#CCFF00] font-bold">
                  {scanDetails.filesExcluded ?? 0} files excluded
                </span>
              </div>
              <div className="text-[10px] text-[var(--text-muted)] dark:text-white/50 uppercase tracking-wider">
                SCOPE: {includeTests ? 'ALL FILES' : 'EXCLUDING TESTS & FIXTURES'}
              </div>
            </div>
          )}
        </motion.div>
      )}

      {/* Error Banner */}
      {error && (
        <div className="p-4 rounded-xl border border-red-500/50 bg-red-950/40 text-red-200 text-xs font-mono flex items-start gap-3">
          <AlertCircle size={16} className="text-red-400 shrink-0 mt-0.5" />
          <div>
            <strong className="block text-red-300 font-bold mb-1">ANALYSIS FAILURE</strong>
            <span>{error}</span>
          </div>
        </div>
      )}
    </div>
  )
}
export default IngestionPage
