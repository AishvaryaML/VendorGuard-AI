function LoadingSpinner({ label = "Loading..." }) {
  return (
    <div className="flex items-center justify-center gap-3 py-2">
      <span className="h-4 w-4 animate-spin rounded-full border-2 border-white/30 border-t-white" />
      <span className="text-sm font-medium text-white">{label}</span>
    </div>
  );
}

export default LoadingSpinner;
