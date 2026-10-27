import { useState, useRef } from 'react';
import { UploadCloud, File, X } from 'lucide-react';
import { formatFileSize } from '../../utils/format';

export interface FileDropzoneProps {
  onFileSelect: (file: File | null) => void;
  accept?: string;
  maxSizeMB?: number;
  label?: string;
  sublabel?: string;
  className?: string;
}

export const FileDropzone: React.FC<FileDropzoneProps> = ({
  onFileSelect,
  accept = '.zip,.tar,.gz,.tar.gz,.java,.py,.js,.ts',
  maxSizeMB = 100,
  label = 'Drag and drop your project repository or archive here',
  sublabel = 'Supports ZIP, TAR, TAR.GZ, Java, Python and codebases up to 100MB',
  className = ''
}) => {
  const [isDragOver, setIsDragOver] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [error, setError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(true);
  };

  const handleDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
  };

  const validateAndSetFile = (file: File) => {
    setError(null);
    if (file.size > maxSizeMB * 1024 * 1024) {
      setError(`File size exceeds maximum limit of ${maxSizeMB}MB`);
      return;
    }
    setSelectedFile(file);
    onFileSelect(file);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      validateAndSetFile(e.dataTransfer.files[0]);
    }
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      validateAndSetFile(e.target.files[0]);
    }
  };

  const handleRemove = (e: React.MouseEvent) => {
    e.stopPropagation();
    setSelectedFile(null);
    setError(null);
    if (fileInputRef.current) fileInputRef.current.value = '';
    onFileSelect(null);
  };

  return (
    <div className={`w-full ${className}`}>
      <div
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={() => fileInputRef.current?.click()}
        className={`relative flex flex-col items-center justify-center p-8 rounded-2xl border-2 border-dashed cursor-pointer transition-[transform,border-color,background-color] duration-200 will-change-transform ${
          isDragOver
            ? 'border-[var(--agencia-lime)] bg-[var(--agencia-lime)]/5 scale-[1.01]'
            : selectedFile
            ? 'border-[var(--agencia-lime)] bg-[var(--agencia-surface)]'
            : 'border-[var(--agencia-border)] hover:border-[var(--agencia-lime)]/60 bg-[var(--agencia-surface)]/50'
        }`}
      >
        <input
          ref={fileInputRef}
          type="file"
          accept={accept}
          onChange={handleInputChange}
          className="hidden"
        />

        {selectedFile ? (
          <div className="flex items-center gap-4 w-full max-w-md p-4 rounded-xl bg-[var(--agencia-glass-border)] border border-[var(--agencia-border)]">
            <div className="p-3 rounded-lg bg-[var(--agencia-lime)]/10 text-[var(--accent-text)]">
              <File className="w-6 h-6" />
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-sm font-semibold text-[var(--agencia-text)] truncate">
                {selectedFile.name}
              </p>
              <p className="text-xs text-[var(--agencia-text-muted)] font-mono">
                {formatFileSize(selectedFile.size)} • Ready
              </p>
            </div>
            <button
              onClick={handleRemove}
              className="p-1.5 rounded-lg text-[var(--agencia-text-muted)] hover:text-[var(--agencia-red)] hover:bg-[var(--agencia-surface)] transition-colors"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        ) : (
          <div className="flex flex-col items-center text-center space-y-3">
            <div className="p-4 rounded-full bg-[var(--agencia-glass-border)] border border-[var(--agencia-border)] text-[var(--accent-text)]">
              <UploadCloud className="w-8 h-8" />
            </div>
            <div>
              <p className="text-sm font-semibold text-[var(--agencia-text)]">{label}</p>
              <p className="text-xs text-[var(--agencia-text-muted)] mt-1">{sublabel}</p>
            </div>
            <span className="inline-block px-3 py-1 text-[11px] font-mono rounded-full bg-[var(--agencia-border)] text-[var(--agencia-text-muted)]">
              Browse Files
            </span>
          </div>
        )}
      </div>

      {error && (
        <p className="mt-2 text-xs font-mono text-[var(--agencia-red)] flex items-center gap-1.5">
          <span>✕</span> {error}
        </p>
      )}
    </div>
  );
};
