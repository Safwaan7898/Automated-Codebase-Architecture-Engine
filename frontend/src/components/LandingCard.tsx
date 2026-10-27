import React, { useState } from 'react'
import {
  GitBranch,
  UploadCloud,
  FolderUp,
  FileCode2,
  Lock,
  ArrowRight,
  AlertCircle,
  CheckCircle2,
  Loader2,
  Sparkles,
} from 'lucide-react'
import type { IngestionTab, IngestionEvent } from '../types'
import { formatFileSize } from '../utils/format'

interface LandingCardProps {
  onSubmitGit: (data: { url: string; branch?: string; subpath?: string; access_token?: string }) => void
  onSubmitArchive: (file: File) => void
  onSubmitFolder: (files: File[], paths: string[]) => void
  onSubmitSnippet: (code: string, language: string, filename?: string) => void
  loading: boolean
  ingestionEvents: IngestionEvent[]
  currentStage: string
  progressPercent: number
  error: string | null
}

export const LandingCard: React.FC<LandingCardProps> = ({
  onSubmitGit,
  onSubmitArchive,
  onSubmitFolder,
  onSubmitSnippet,
  loading,
  ingestionEvents,
  currentStage,
  progressPercent,
  error,
}) => {
  const [activeTab, setActiveTab] = useState<IngestionTab>('git')

  // Git form state
  const [gitUrl, setGitUrl] = useState('')
  const [branch, setBranch] = useState('')
  const [subpath, setSubpath] = useState('')
  const [accessToken, setAccessToken] = useState('')
  const [gitErrors, setGitErrors] = useState<{ url?: string }>({})

  // Archive state
  const [archiveFile, setArchiveFile] = useState<File | null>(null)
  const [archiveDragOver, setArchiveDragOver] = useState(false)

  // Folder state
  const [folderFiles, setFolderFiles] = useState<{ files: File[]; paths: string[] }>({ files: [], paths: [] })

  // Snippet state
  const [snippetCode, setSnippetCode] = useState(`import os
import subprocess

def execute_user_query(user_id, raw_query):
    # Potential SQL injection vulnerability
    query = f"SELECT * FROM users WHERE id = '{user_id}' AND active = 1"
    
    # Potential Command injection vulnerability
    cmd = f"ping -c 1 {raw_query}"
    subprocess.Popen(cmd, shell=True)
    
    return query
`)
  const [snippetLang, setSnippetLang] = useState('python')
  const [snippetFilename, setSnippetFilename] = useState('vulnerable_service.py')

  // Git validation
  const handleGitSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    const errors: { url?: string } = {}
    if (!gitUrl.trim()) {
      errors.url = 'Repository URL is required.'
    } else if (!gitUrl.startsWith('http://') && !gitUrl.startsWith('https://') && !gitUrl.startsWith('git@')) {
      errors.url = 'Please enter a valid Git URL (https://github.com/... or git@...)'
    }

    setGitErrors(errors)
    if (Object.keys(errors).length === 0) {
      onSubmitGit({
        url: gitUrl.trim(),
        branch: branch.trim() || undefined,
        subpath: subpath.trim() || undefined,
        access_token: accessToken.trim() || undefined,
      })
    }
  }

  // Archive drop handlers
  const handleArchiveDrop = (e: React.DragEvent) => {
    e.preventDefault()
    setArchiveDragOver(false)
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const file = e.dataTransfer.files[0]
      if (file.name.endsWith('.zip') || file.name.endsWith('.tar') || file.name.endsWith('.tar.gz') || file.name.endsWith('.tgz')) {
        setArchiveFile(file)
      } else {
        alert('Please upload an archive file (.zip, .tar, .tar.gz)')
      }
    }
  }

  // Folder input handler
  const handleFolderChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      const files: File[] = []
      const paths: string[] = []
      for (let i = 0; i < e.target.files.length; i++) {
        const f = e.target.files[i]
        files.push(f)
        paths.push(f.webkitRelativePath || f.name)
      }
      setFolderFiles({ files, paths })
    }
  }

  return (
    <div id="ingestion-section" className="w-full max-w-4xl mx-auto px-4 py-8">
      {/* Container Card with luxury-brutalist Agencia styling */}
      <div className="agencia-card rounded-2xl overflow-hidden border border-white/10 transition-colors duration-300">
        {/* Card Header & Tabs */}
        <div className="border-b border-white/10 p-6 flex flex-col md:flex-row md:items-center justify-between gap-4 bg-black/40">
          <div>
            <h2 className="agencia-display text-3xl tracking-wider text-white">
              CODEBASE INGESTION ENGINE
            </h2>
            <p className="text-xs text-white/50 font-mono">
              UNIVERSAL AST PARSING · CYCLE ISOLATION · LOUVAIN CLUSTERING
            </p>
          </div>

          {/* Tab Navigation */}
          <div className="flex items-center gap-1 p-1 bg-white/5 rounded-full border border-white/10 self-start md:self-auto">
            <button
              onClick={() => setActiveTab('git')}
              className={`px-4 py-2 rounded-full text-xs font-mono uppercase tracking-wider flex items-center gap-2 transition-colors duration-150 ${
                activeTab === 'git'
                  ? 'bg-white text-black font-semibold shadow-sm'
                  : 'text-white/60 hover:text-white'
              }`}
            >
              <GitBranch className="w-3.5 h-3.5" />
              Git URL
            </button>

            <button
              onClick={() => setActiveTab('archive')}
              className={`px-4 py-2 rounded-full text-xs font-mono uppercase tracking-wider flex items-center gap-2 transition-colors duration-150 ${
                activeTab === 'archive'
                  ? 'bg-white text-black font-semibold shadow-sm'
                  : 'text-white/60 hover:text-white'
              }`}
            >
              <UploadCloud className="w-3.5 h-3.5" />
              ZIP Archive
            </button>

            <button
              onClick={() => setActiveTab('folder')}
              className={`px-4 py-2 rounded-full text-xs font-mono uppercase tracking-wider flex items-center gap-2 transition-colors duration-150 ${
                activeTab === 'folder'
                  ? 'bg-white text-black font-semibold shadow-sm'
                  : 'text-white/60 hover:text-white'
              }`}
            >
              <FolderUp className="w-3.5 h-3.5" />
              Upload Folder
            </button>

            <button
              onClick={() => setActiveTab('snippet')}
              className={`px-4 py-2 rounded-full text-xs font-mono uppercase tracking-wider flex items-center gap-2 transition-colors duration-150 ${
                activeTab === 'snippet'
                  ? 'bg-white text-black font-semibold shadow-sm'
                  : 'text-white/60 hover:text-white'
              }`}
            >
              <FileCode2 className="w-3.5 h-3.5" />
              Paste Code
            </button>
          </div>
        </div>

        {/* Card Body */}
        <div className="p-6 md:p-8">
          {/* Error Banner */}
          {error && (
            <div className="mb-6 p-4 rounded-xl bg-red-500/10 border border-red-500/30 text-red-300 text-xs font-mono flex items-start gap-3">
              <AlertCircle className="w-4 h-4 text-red-400 shrink-0 mt-0.5" />
              <div>
                <span className="font-semibold block mb-0.5">Ingestion Pipeline Error</span>
                <span>{error}</span>
              </div>
            </div>
          )}

          {/* TAB 1: GIT URL */}
          {activeTab === 'git' && (
            <form onSubmit={handleGitSubmit} className="space-y-6">
              <div>
                <label className="block text-xs font-mono uppercase tracking-widest text-white/70 mb-2">
                  Repository Git / GitHub URL <span className="text-red-400">*</span>
                </label>
                <div className="relative">
                  <input
                    type="text"
                    value={gitUrl}
                    onChange={(e) => {
                      setGitUrl(e.target.value)
                      if (gitErrors.url) setGitErrors({})
                    }}
                    placeholder="https://github.com/pallets/flask.git or https://github.com/spring-projects/spring-petclinic"
                    className={`w-full bg-[#0a0a0a] border rounded-xl px-4 py-3.5 text-sm font-mono text-white placeholder-white/65 focus:outline-none focus:ring-1 focus:ring-blue-500 transition-colors duration-150 ${
                      gitErrors.url ? 'border-red-500/60' : 'border-white/10 hover:border-white/20'
                    }`}
                  />
                  {gitErrors.url && (
                    <span className="text-xs text-red-400 font-mono mt-1.5 flex items-center gap-1">
                      <AlertCircle className="w-3 h-3" />
                      {gitErrors.url}
                    </span>
                  )}
                </div>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-mono uppercase tracking-widest text-white/70 mb-2">
                    Branch or Tag (Optional)
                  </label>
                  <input
                    type="text"
                    value={branch}
                    onChange={(e) => setBranch(e.target.value)}
                    placeholder="main, master, v2.1.0"
                    className="w-full bg-[#0a0a0a] border border-white/10 rounded-xl px-4 py-3 text-sm font-mono text-white placeholder-white/65 focus:outline-none focus:border-white/30"
                  />
                </div>

                <div>
                  <label className="block text-xs font-mono uppercase tracking-widest text-white/70 mb-2">
                    Subfolder Path (Monorepo)
                  </label>
                  <input
                    type="text"
                    value={subpath}
                    onChange={(e) => setSubpath(e.target.value)}
                    placeholder="packages/backend, src/"
                    className="w-full bg-[#0a0a0a] border border-white/10 rounded-xl px-4 py-3 text-sm font-mono text-white placeholder-white/65 focus:outline-none focus:border-white/30"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-mono uppercase tracking-widest text-white/70 mb-2 flex items-center justify-between">
                  <span className="flex items-center gap-1.5">
                    <Lock className="w-3.5 h-3.5 text-white/40" />
                    Personal Access Token (Private Repositories)
                  </span>
                  <span className="text-[10px] text-white/40 font-mono lowercase">optional</span>
                </label>
                <input
                  type="password"
                  value={accessToken}
                  onChange={(e) => setAccessToken(e.target.value)}
                  placeholder="ghp_xxxxxxxxxxxxxxxxxxxx"
                  className="w-full bg-[#0a0a0a] border border-white/10 rounded-xl px-4 py-3 text-sm font-mono text-white placeholder-white/65 focus:outline-none focus:border-white/30"
                />
                <p className="text-[11px] text-white/40 font-mono mt-1.5">
                  🛡️ Access tokens are never stored on disk. They are held in memory exclusively for authenticated Git operations.
                </p>
              </div>

              <button
                type="submit"
                disabled={loading}
                className="agencia-glass-btn w-full flex items-center justify-center gap-3 py-4 text-xs font-mono uppercase tracking-widest text-white font-semibold cursor-pointer group"
              >
                {loading ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin text-blue-400" />
                    <span>STREAMING INGESTION PIPELINE…</span>
                  </>
                ) : (
                  <>
                    <span>START ARCHITECTURAL INGESTION</span>
                    <ArrowRight className="w-4 h-4 agencia-btn-icon transition-transform duration-300 group-hover:translate-x-1" />
                  </>
                )}
              </button>
            </form>
          )}

          {/* TAB 2: ARCHIVE UPLOAD */}
          {activeTab === 'archive' && (
            <div className="space-y-6">
              <div
                onDragOver={(e) => {
                  e.preventDefault()
                  setArchiveDragOver(true)
                }}
                onDragLeave={() => setArchiveDragOver(false)}
                onDrop={handleArchiveDrop}
                className={`border-2 border-dashed rounded-2xl p-10 flex flex-col items-center justify-center text-center cursor-pointer transition-colors duration-150 ${
                  archiveDragOver
                    ? 'border-blue-500 bg-blue-500/10'
                    : archiveFile
                    ? 'border-emerald-500/50 bg-emerald-500/5'
                    : 'border-white/15 hover:border-white/30 bg-[#0a0a0a]'
                }`}
                onClick={() => document.getElementById('archive-file-input')?.click()}
              >
                <input
                  id="archive-file-input"
                  type="file"
                  accept=".zip,.tar,.tar.gz,.tgz"
                  className="hidden"
                  onChange={(e) => {
                    if (e.target.files && e.target.files[0]) {
                      setArchiveFile(e.target.files[0])
                    }
                  }}
                />

                <UploadCloud className="w-12 h-12 text-white/40 mb-3" />
                {archiveFile ? (
                  <div>
                    <span className="text-emerald-400 font-mono text-sm block font-medium">
                      ✓ {archiveFile.name} ({formatFileSize(archiveFile.size)})
                    </span>
                    <span className="text-white/40 text-xs font-mono mt-1 block">
                      Click or drop another file to replace
                    </span>
                  </div>
                ) : (
                  <div>
                    <p className="text-sm font-mono text-white/80 mb-1">
                      Drag & drop your codebase archive here, or <span className="text-blue-400 underline">browse</span>
                    </p>
                    <p className="text-xs font-mono text-white/40">
                      Supports .zip, .tar, .tar.gz up to 250MB
                    </p>
                  </div>
                )}
              </div>

              <button
                type="button"
                disabled={!archiveFile || loading}
                onClick={() => archiveFile && onSubmitArchive(archiveFile)}
                className={`agencia-glass-btn w-full flex items-center justify-center gap-3 py-4 text-xs font-mono uppercase tracking-widest text-white font-semibold cursor-pointer group ${
                  !archiveFile || loading ? 'opacity-40 pointer-events-none' : ''
                }`}
              >
                {loading ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin text-blue-400" />
                    <span>UNPACKING & ANALYZING ARCHIVE…</span>
                  </>
                ) : (
                  <>
                    <span>UPLOAD & ANALYZE ARCHIVE</span>
                    <ArrowRight className="w-4 h-4 agencia-btn-icon transition-transform duration-300 group-hover:translate-x-1" />
                  </>
                )}
              </button>
            </div>
          )}

          {/* TAB 3: FOLDER UPLOAD */}
          {activeTab === 'folder' && (
            <div className="space-y-6">
              <div
                className="border-2 border-dashed border-white/15 hover:border-white/30 rounded-2xl p-10 flex flex-col items-center justify-center text-center cursor-pointer bg-[#0a0a0a] transition-colors duration-150"
                onClick={() => document.getElementById('folder-input')?.click()}
              >
                {/* Standard webkitdirectory input */}
                <input
                  id="folder-input"
                  type="file"
                  // @ts-expect-error webkitdirectory is standard browser extension
                  webkitdirectory=""
                  multiple
                  className="hidden"
                  onChange={handleFolderChange}
                />

                <FolderUp className="w-12 h-12 text-white/40 mb-3" />
                {folderFiles.files.length > 0 ? (
                  <div>
                    <span className="text-emerald-400 font-mono text-sm block font-medium">
                      ✓ Selected {folderFiles.files.length} files in folder
                    </span>
                    <span className="text-white/40 text-xs font-mono mt-1 block">
                      Click to choose a different directory
                    </span>
                  </div>
                ) : (
                  <div>
                    <p className="text-sm font-mono text-white/80 mb-1">
                      Select a local repository folder from your computer
                    </p>
                    <p className="text-xs font-mono text-white/40">
                      Files are transferred directly with relative directory structure preserved
                    </p>
                  </div>
                )}
              </div>

              <button
                type="button"
                disabled={folderFiles.files.length === 0 || loading}
                onClick={() => onSubmitFolder(folderFiles.files, folderFiles.paths)}
                className={`agencia-glass-btn w-full flex items-center justify-center gap-3 py-4 text-xs font-mono uppercase tracking-widest text-white font-semibold cursor-pointer group ${
                  folderFiles.files.length === 0 || loading ? 'opacity-40 pointer-events-none' : ''
                }`}
              >
                {loading ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin text-blue-400" />
                    <span>PARSING CODEBASE HIERARCHY…</span>
                  </>
                ) : (
                  <>
                    <span>INGEST LOCAL FOLDER HIERARCHY</span>
                    <ArrowRight className="w-4 h-4 agencia-btn-icon transition-transform duration-300 group-hover:translate-x-1" />
                  </>
                )}
              </button>
            </div>
          )}

          {/* TAB 4: CODE SNIPPET */}
          {activeTab === 'snippet' && (
            <div className="space-y-6">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-mono uppercase tracking-widest text-white/70 mb-2">
                    Source Language
                  </label>
                  <select
                    value={snippetLang}
                    onChange={(e) => setSnippetLang(e.target.value)}
                    className="w-full bg-[#0a0a0a] border border-white/10 rounded-xl px-4 py-3 text-sm font-mono text-white focus:outline-none"
                  >
                    <option value="python">Python 3.x</option>
                    <option value="java">Java 17/21</option>
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-mono uppercase tracking-widest text-white/70 mb-2">
                    Simulated Filename
                  </label>
                  <input
                    type="text"
                    value={snippetFilename}
                    onChange={(e) => setSnippetFilename(e.target.value)}
                    className="w-full bg-[#0a0a0a] border border-white/10 rounded-xl px-4 py-3 text-sm font-mono text-white placeholder-white/65 focus:outline-none"
                  />
                </div>
              </div>

              <div>
                <label className="block text-xs font-mono uppercase tracking-widest text-white/70 mb-2">
                  Source Code Text
                </label>
                <textarea
                  rows={8}
                  value={snippetCode}
                  onChange={(e) => setSnippetCode(e.target.value)}
                  className="w-full bg-[#0a0a0a] border border-white/10 rounded-xl p-4 text-xs font-mono text-white/90 placeholder-white/65 focus:outline-none focus:border-white/30 resize-y"
                  placeholder="Paste Python or Java source code..."
                />
              </div>

              <button
                type="button"
                disabled={!snippetCode.trim() || loading}
                onClick={() => onSubmitSnippet(snippetCode, snippetLang, snippetFilename)}
                className={`agencia-glass-btn w-full flex items-center justify-center gap-3 py-4 text-xs font-mono uppercase tracking-widest text-white font-semibold cursor-pointer group ${
                  !snippetCode.trim() || loading ? 'opacity-40 pointer-events-none' : ''
                }`}
              >
                {loading ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin text-blue-400" />
                    <span>EVALUATING AST & SECURITY RULES…</span>
                  </>
                ) : (
                  <>
                    <span>ANALYZE CODE SNIPPET</span>
                    <ArrowRight className="w-4 h-4 agencia-btn-icon transition-transform duration-300 group-hover:translate-x-1" />
                  </>
                )}
              </button>
            </div>
          )}

          {/* Live Ingestion Stage Stream View (WebSocket Events) */}
          {(loading || ingestionEvents.length > 0) && (
            <div className="mt-8 pt-8 border-t border-white/10 animate-fade-in">
              <div className="flex items-center justify-between mb-3">
                <span className="text-xs font-mono uppercase tracking-wider text-white/80 flex items-center gap-2">
                  <Sparkles className="w-4 h-4 text-blue-400 animate-pulse" />
                  Live Ingestion Pipeline Stream
                </span>
                <span className="text-xs font-mono text-blue-400 font-bold">
                  {progressPercent}%
                </span>
              </div>

              {/* Progress Bar */}
              <div className="w-full h-1.5 bg-white/10 rounded-full overflow-hidden mb-4">
                <div
                  className="h-full bg-gradient-to-r from-blue-600 via-blue-400 to-emerald-400 transition-[width] duration-300 ease-out will-change-[width]"
                  style={{ width: `${Math.max(5, progressPercent)}%` }}
                />
              </div>

              {/* Stage Events Log */}
              <div className="bg-[#050505] border border-white/10 rounded-xl p-4 max-h-48 overflow-y-auto font-mono text-xs space-y-2">
                {ingestionEvents.map((evt, idx) => (
                  <div key={idx} className="flex items-center gap-2.5 text-white/70">
                    <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
                    <span className="text-white/40 text-[10px]">[{evt.stage}]</span>
                    <span className="text-white/90">{evt.message}</span>
                  </div>
                ))}
                {loading && (
                  <div className="flex items-center gap-2.5 text-blue-400 animate-pulse">
                    <Loader2 className="w-3.5 h-3.5 animate-spin shrink-0" />
                    <span>{currentStage || 'Processing AST & graph topology…'}</span>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
