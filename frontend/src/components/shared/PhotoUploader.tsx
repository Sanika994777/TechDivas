import { useCallback, useState } from "react";
import { Upload, X, Camera } from "lucide-react";
import { cn } from "@/lib/utils";

interface PhotoUploaderProps {
  files: File[];
  onChange: (files: File[]) => void;
  maxFiles?: number;
  maxSizeMB?: number;
}

export function PhotoUploader({
  files,
  onChange,
  maxFiles = 3,
  maxSizeMB = 5,
}: PhotoUploaderProps) {
  const [dragOver, setDragOver] = useState(false);
  const [errors, setErrors] = useState<string[]>([]);

  const validate = useCallback(
    (incoming: File[]): { valid: File[]; errors: string[] } => {
      const errs: string[] = [];
      const valid: File[] = [];
      const allowed = ["image/jpeg", "image/png", "image/webp"];
      incoming.forEach((f) => {
        if (!allowed.includes(f.type)) {
          errs.push(`${f.name}: only JPG, PNG, WEBP allowed`);
        } else if (f.size > maxSizeMB * 1024 * 1024) {
          errs.push(`${f.name}: exceeds ${maxSizeMB} MB limit`);
        } else {
          valid.push(f);
        }
      });
      return { valid, errors: errs };
    },
    [maxSizeMB]
  );

  function addFiles(newFiles: FileList | null) {
    if (!newFiles) return;
    const arr = Array.from(newFiles);
    const { valid, errors: errs } = validate(arr);
    setErrors(errs);
    const combined = [...files, ...valid].slice(0, maxFiles);
    onChange(combined);
  }

  function remove(i: number) {
    onChange(files.filter((_, idx) => idx !== i));
  }

  return (
    <div>
      {/* Drop zone */}
      <label
        className={cn(
          "flex flex-col items-center justify-center gap-3 border-2 border-dashed rounded-card p-8 cursor-pointer transition-colors",
          dragOver
            ? "border-saffron bg-saffron-50"
            : "border-gray-200 bg-gray-50 hover:border-saffron hover:bg-saffron-50"
        )}
        onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
        onDragLeave={() => setDragOver(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragOver(false);
          addFiles(e.dataTransfer.files);
        }}
      >
        <input
          type="file"
          accept="image/jpeg,image/png,image/webp"
          multiple
          className="sr-only"
          onChange={(e) => addFiles(e.target.files)}
          aria-label="Upload photos"
        />
        <Upload size={32} className={dragOver ? "text-saffron" : "text-gray-400"} />
        <div className="text-center">
          <p className="font-semibold text-navy-900">
            Drag &amp; drop photos here
          </p>
          <p className="text-sm text-gray-500 mt-1">
            or tap to browse · {maxFiles} photos max · {maxSizeMB} MB each · JPG / PNG / WEBP
          </p>
        </div>
        <span className="flex items-center gap-2 bg-saffron text-navy-900 font-semibold text-sm px-4 py-2 rounded-badge">
          <Camera size={14} /> Choose Photos
        </span>
      </label>

      {/* Error messages */}
      {errors.length > 0 && (
        <ul className="mt-2 space-y-1">
          {errors.map((e, i) => (
            <li key={i} className="text-red-600 text-xs">{e}</li>
          ))}
        </ul>
      )}

      {/* Thumbnails */}
      {files.length > 0 && (
        <div className="mt-4 flex flex-wrap gap-3">
          {files.map((f, i) => (
            <div key={i} className="relative w-24 h-24 rounded-lg overflow-hidden border border-gray-200 group">
              <img
                src={URL.createObjectURL(f)}
                alt={`Photo ${i + 1}`}
                className="w-full h-full object-cover"
              />
              <button
                onClick={() => remove(i)}
                className="absolute top-1 right-1 bg-red-600 text-white rounded-full p-0.5 opacity-0 group-hover:opacity-100 transition-opacity"
                aria-label={`Remove photo ${i + 1}`}
              >
                <X size={12} />
              </button>
            </div>
          ))}
          {files.length < maxFiles && (
            <label className="w-24 h-24 rounded-lg border-2 border-dashed border-gray-200 flex items-center justify-center cursor-pointer hover:border-saffron transition-colors">
              <input type="file" accept="image/*" className="sr-only" onChange={(e) => addFiles(e.target.files)} />
              <span className="text-2xl text-gray-300">+</span>
            </label>
          )}
        </div>
      )}
    </div>
  );
}
