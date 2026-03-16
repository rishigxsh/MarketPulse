export default function SkeletonCard() {
  return (
    <div className="rounded-xl border border-gray-800 bg-gray-900 p-4 animate-pulse">
      <div className="h-4 w-16 rounded bg-gray-700 mb-3" />
      <div className="h-6 w-28 rounded bg-gray-700 mb-2" />
      <div className="h-3 w-20 rounded bg-gray-700" />
    </div>
  );
}
