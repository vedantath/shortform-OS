const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

type Video = {
  id: string;
  status: string;
  title: string | null;
  created_at: string;
};

async function getVideos(): Promise<Video[]> {
  try {
    const res = await fetch(`${API_URL}/api/v1/videos/`, {
      cache: "no-store",
    });
    if (!res.ok) return [];
    return res.json();
  } catch {
    return [];
  }
}

const STATUS_COLORS: Record<string, string> = {
  pending: "bg-gray-700",
  scripting: "bg-blue-700",
  voicing: "bg-indigo-700",
  fetching_visuals: "bg-violet-700",
  rendering: "bg-yellow-700",
  uploading: "bg-orange-700",
  live: "bg-green-700",
  failed: "bg-red-700",
};

export default async function DashboardPage() {
  const videos = await getVideos();

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">Pipeline Dashboard</h1>

      {videos.length === 0 ? (
        <p className="text-gray-500">No videos yet. Trigger the pipeline to get started.</p>
      ) : (
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-gray-800 text-gray-400">
                <th className="text-left py-3 pr-4">ID</th>
                <th className="text-left py-3 pr-4">Title</th>
                <th className="text-left py-3 pr-4">Status</th>
                <th className="text-left py-3">Created</th>
              </tr>
            </thead>
            <tbody>
              {videos.map((v) => (
                <tr key={v.id} className="border-b border-gray-900 hover:bg-gray-900">
                  <td className="py-3 pr-4 font-mono text-xs text-gray-500">
                    {v.id.slice(0, 8)}
                  </td>
                  <td className="py-3 pr-4">{v.title ?? "—"}</td>
                  <td className="py-3 pr-4">
                    <span
                      className={`px-2 py-0.5 rounded text-xs font-medium ${
                        STATUS_COLORS[v.status] ?? "bg-gray-700"
                      }`}
                    >
                      {v.status}
                    </span>
                  </td>
                  <td className="py-3 text-gray-400">
                    {new Date(v.created_at).toLocaleString()}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
