using System;
using System.Linq;

namespace GameDevMind.ClientOptimization
{
    public static class CoreRegression
    {
        public static void Run()
        {
            var slots = new[] { 10 };
            var b = new RendererInfo("B", 1, 1, true, false, slots);
            slots[0] = 99; // Caller mutation must not rewrite the snapshot.
            var rows = new[]
            {
                b, new RendererInfo("A", 1, 1, true, false, 10),
                // Even if shader/name/texture match, distinct material/mesh IDs stay distinct.
                new RendererInfo("other-material", 1, 1, true, false, 11),
                new RendererInfo("other-mesh", 2, 1, true, false, 10),
                new RendererInfo("mpb", 1, 1, true, true, 10),
                new RendererInfo("inactive", 1, 1, false, false, 10),
                new RendererInfo("no-mesh", 0, 0, true, false, 10),
                new RendererInfo("null-material", 1, 1, true, false, 0),
                new RendererInfo("empty-slots", 1, 1, true, false),
                new RendererInfo("extra-slot", 1, 1, true, false, 10, 11),
                new RendererInfo("multi-submesh", 1, 2, true, false, 10)
            };
            var report = RenderAuditCore.Analyze(rows);
            Require(report.Renderers == 11 && report.DistinctMaterials == 2, "Identity inventory");
            Require(report.WithPropertyBlock == 1 && report.InactiveOrDisabled == 1, "State inventory");
            Require(report.UnsupportedGeometryOrSlots == 5, "Conservative geometry/slot filtering");
            Require(report.SharingCandidates.Count == 1, "No false material/mesh equivalence");
            var group = report.SharingCandidates.Single();
            Require(group.MeshId == 1 && group.MaterialId == 10 &&
                group.Paths.SequenceEqual(new[] { "A", "B" }), "Only eligible shared references, ordinal order");
            Require(RenderAuditCore.Analyze(rows.Reverse()).SharingCandidates.Single().Paths
                .SequenceEqual(group.Paths), "Input traversal order independence");
            Require(RenderAuditCore.Analyze(Array.Empty<RendererInfo>()).SharingCandidates.Count == 0,
                "Empty scene");
            Require(b.MaterialIds[0] == 10, "Snapshot isolation");
            bool rejected = false;
            try { RenderAuditCore.Analyze(new RendererInfo[] { null }); }
            catch (ArgumentException) { rejected = true; }
            Require(rejected, "Reject missing snapshot records");
        }

        private static void Require(bool condition, string message)
        {
            if (!condition) throw new InvalidOperationException(message);
        }

        public static int Main()
        {
            Run();
            Console.WriteLine("PASS: render audit identity, exclusions, ordering and snapshot regression");
            return 0;
        }
    }
}
