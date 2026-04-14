import { AlertTriangle, FileText, UploadCloud } from "lucide-react";
import { useCallback, useRef, useState } from "react";
import { useDropzone } from "react-dropzone";

function formatSize(bytes) {
  if (!bytes) {
    return "0 KB";
  }
  const kilobytes = bytes / 1024;
  if (kilobytes < 1024) {
    return `${kilobytes.toFixed(1)} KB`;
  }
  return `${(kilobytes / 1024).toFixed(2)} MB`;
}

function CSVUploader({ onUpload, uploading = false }) {
  const timerRef = useRef(null);
  const [selectedFile, setSelectedFile] = useState(null);
  const [progress, setProgress] = useState(0);
  const [error, setError] = useState("");

  const animateProgress = () =>
    new Promise((resolve) => {
      clearInterval(timerRef.current);
      let current = 0;
      timerRef.current = setInterval(() => {
        current += 5;
        setProgress(Math.min(current, 95));
        if (current >= 95) {
          clearInterval(timerRef.current);
          resolve();
        }
      }, 100);
    });

  const beginUpload = useCallback(
    async (file) => {
      setSelectedFile(file);
      setError("");
      setProgress(0);
      try {
        await Promise.all([animateProgress(), onUpload(file)]);
        setProgress(100);
      } catch (uploadError) {
        clearInterval(timerRef.current);
        setProgress(0);
        setError(uploadError?.response?.data?.detail || "Upload failed. Please check the CSV and try again.");
      }
    },
    [onUpload]
  );

  const onDropAccepted = useCallback(
    (files) => {
      if (files[0]) {
        beginUpload(files[0]);
      }
    },
    [beginUpload]
  );

  const onDropRejected = useCallback(() => {
    setError("Only .csv files are supported for bias audits.");
  }, []);

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    accept: {
      "text/csv": [".csv"]
    },
    disabled: uploading,
    maxFiles: 1,
    onDropAccepted,
    onDropRejected
  });

  return (
    <div className="space-y-4">
      <div
        {...getRootProps()}
        className={`relative cursor-pointer rounded-[28px] border-2 border-dashed p-8 transition ${
          error
            ? "border-red-300 bg-red-50"
            : isDragActive
              ? "border-amber bg-amber/10"
              : "border-slate-300 bg-white hover:border-amber/60 hover:bg-amber/5"
        } ${uploading ? "pointer-events-none opacity-75" : ""}`}
      >
        <input {...getInputProps()} />
        <div className="mx-auto flex max-w-xl flex-col items-center text-center">
          <div className="rounded-full bg-navy p-4 text-white shadow-glow">
            <UploadCloud className="h-7 w-7" />
          </div>
          <h3 className="mt-5 text-xl font-bold text-slate-900">
            Drop your hiring CSV here or click to browse
          </h3>
          <p className="mt-3 text-sm leading-6 text-slate-500">
            Upload a candidate decision export to run bias detection, candidate explanations, and
            mitigation analysis in one flow.
          </p>
          <div className="mt-5 rounded-full border border-slate-200 bg-slate-50 px-4 py-2 text-xs font-semibold uppercase tracking-[0.2em] text-slate-500">
            Expected format: .csv
          </div>
        </div>
      </div>

      {selectedFile && (
        <div className="rounded-3xl border border-slate-200 bg-white p-5 shadow-sm">
          <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
            <div className="flex items-center gap-4">
              <div className="rounded-2xl bg-slate-100 p-3 text-navy">
                <FileText className="h-6 w-6" />
              </div>
              <div>
                <p className="text-sm font-semibold text-slate-900">{selectedFile.name}</p>
                <p className="text-sm text-slate-500">{formatSize(selectedFile.size)}</p>
              </div>
            </div>
            <div className="rounded-full bg-slate-100 px-4 py-2 text-sm font-medium text-slate-600">
              {progress === 100 ? "Upload complete" : "Processing upload"}
            </div>
          </div>

          <div className="mt-4">
            <div className="h-3 overflow-hidden rounded-full bg-slate-100">
              <div
                className="h-full rounded-full bg-[linear-gradient(90deg,#f59e0b_0%,#0f172a_100%)] transition-all duration-200"
                style={{ width: `${progress}%` }}
              />
            </div>
            <div className="mt-2 flex items-center justify-between text-xs font-medium text-slate-500">
              <span>Upload progress</span>
              <span>{progress}%</span>
            </div>
          </div>
        </div>
      )}

      {error && (
        <div className="flex items-start gap-3 rounded-3xl border border-red-200 bg-red-50 px-5 py-4 text-red-700">
          <AlertTriangle className="mt-0.5 h-5 w-5 shrink-0" />
          <p className="text-sm leading-6">{error}</p>
        </div>
      )}
    </div>
  );
}

export default CSVUploader;
