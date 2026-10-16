using System;
using System.Collections.Generic;
using System.Linq;

namespace GameDevMind.ClientOptimization
{
    // IDs identify actual objects in ONE snapshot, not equivalent material values.
    public sealed class RendererInfo
    {
        public string Path { get; }
        public int MeshId { get; }
        public int SubMeshCount { get; }
        public bool Active { get; }
        public bool HasPropertyBlock { get; }
        public IReadOnlyList<int> MaterialIds { get; }

        public RendererInfo(string path, int meshId, int subMeshCount, bool active,
            bool hasPropertyBlock, params int[] materialIds)
        {
            Path = path ?? throw new ArgumentNullException(nameof(path));
            MeshId = meshId;
            SubMeshCount = subMeshCount;
            Active = active;
            HasPropertyBlock = hasPropertyBlock;
            MaterialIds = Array.AsReadOnly((int[])(materialIds ??
                throw new ArgumentNullException(nameof(materialIds))).Clone());
        }
    }

    public sealed class SharingGroup
    {
        public int MeshId { get; }
        public int MaterialId { get; }
        public IReadOnlyList<string> Paths { get; }

        internal SharingGroup(int meshId, int materialId, IEnumerable<string> paths)
        {
            MeshId = meshId;
            MaterialId = materialId;
            Paths = Array.AsReadOnly(paths.OrderBy(p => p, StringComparer.Ordinal).ToArray());
        }
    }

    public sealed class AuditReport
    {
        public int Renderers { get; internal set; }
        public int DistinctMaterials { get; internal set; }
        // These counters can overlap; they are diagnostic dimensions, not a partition.
        public int InactiveOrDisabled { get; internal set; }
        public int WithPropertyBlock { get; internal set; }
        public int UnsupportedGeometryOrSlots { get; internal set; }
        public IReadOnlyList<SharingGroup> SharingCandidates { get; internal set; }
    }

    public static class RenderAuditCore
    {
        public static AuditReport Analyze(IEnumerable<RendererInfo> source)
        {
            if (source == null) throw new ArgumentNullException(nameof(source));
            var rows = source.ToArray();
            if (rows.Any(r => r == null)) throw new ArgumentException("Null renderer record", nameof(source));
            bool Supported(RendererInfo r) => r.MeshId != 0 && r.SubMeshCount == 1 &&
                r.MaterialIds.Count == 1 && r.MaterialIds[0] != 0;
            var groups = rows.Where(r => r.Active && !r.HasPropertyBlock && Supported(r))
                .GroupBy(r => (r.MeshId, MaterialId: r.MaterialIds[0]))
                .Where(g => g.Count() > 1)
                .OrderBy(g => g.Key.MeshId).ThenBy(g => g.Key.MaterialId)
                .Select(g => new SharingGroup(g.Key.MeshId, g.Key.MaterialId, g.Select(r => r.Path)))
                .ToArray();
            return new AuditReport
            {
                Renderers = rows.Length,
                DistinctMaterials = rows.SelectMany(r => r.MaterialIds).Where(id => id != 0).Distinct().Count(),
                InactiveOrDisabled = rows.Count(r => !r.Active),
                WithPropertyBlock = rows.Count(r => r.HasPropertyBlock),
                UnsupportedGeometryOrSlots = rows.Count(r => !Supported(r)),
                SharingCandidates = Array.AsReadOnly(groups)
            };
        }
    }
}
