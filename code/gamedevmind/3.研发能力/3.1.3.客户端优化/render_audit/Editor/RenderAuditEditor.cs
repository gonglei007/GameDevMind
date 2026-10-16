#if UNITY_EDITOR
using System;
using System.Collections.Generic;
using System.Text;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.SceneManagement;

namespace GameDevMind.ClientOptimization
{
    public static class RenderAuditEditor
    {
        // No setters, material instantiation, dirty marking, asset or scene writes.
        public static List<RendererInfo> Collect(Scene scene)
        {
            if (!scene.IsValid() || !scene.isLoaded || EditorSceneManager.IsPreviewScene(scene))
                throw new ArgumentException("Use a loaded, non-preview scene", nameof(scene));
            var rows = new List<RendererInfo>();
            foreach (var root in scene.GetRootGameObjects())
            foreach (var renderer in root.GetComponentsInChildren<MeshRenderer>(true))
            {
                var filter = renderer.GetComponent<MeshFilter>();
                var mesh = filter != null ? filter.sharedMesh : null;
                var materials = renderer.sharedMaterials;
                var ids = new int[materials.Length];
                for (int i = 0; i < ids.Length; i++)
                    ids[i] = materials[i] != null ? materials[i].GetInstanceID() : 0;
                rows.Add(new RendererInfo(HierarchyPath(renderer.transform),
                    mesh != null ? mesh.GetInstanceID() : 0, mesh != null ? mesh.subMeshCount : 0,
                    renderer.enabled && renderer.gameObject.activeInHierarchy,
                    renderer.HasPropertyBlock(), ids));
            }
            return rows;
        }

        private static string HierarchyPath(Transform node)
        {
            string path = "";
            while (node != null)
            {
                path = "/" + node.name + "[" + node.GetSiblingIndex() + "]" + path;
                node = node.parent;
            }
            return path;
        }

        [MenuItem("Tools/GameDevMind/Read-only Render Audit")]
        public static void Run()
        {
            var rows = new List<RendererInfo>();
            for (int i = 0; i < SceneManager.sceneCount; i++)
            {
                var scene = SceneManager.GetSceneAt(i);
                if (!scene.isLoaded || EditorSceneManager.IsPreviewScene(scene)) continue;
                foreach (var row in Collect(scene))
                    rows.Add(new RendererInfo(scene.name + "[" + scene.handle + "]" + row.Path,
                        row.MeshId, row.SubMeshCount, row.Active, row.HasPropertyBlock,
                        CopyIds(row.MaterialIds)));
            }
            var report = RenderAuditCore.Analyze(rows);
            var log = new StringBuilder("Read-only snapshot (session IDs; NOT a batching/performance verdict)\n");
            log.AppendLine($"MeshRenderers={report.Renderers}, materials={report.DistinctMaterials}, " +
                $"inactive/disabled={report.InactiveOrDisabled}, MPB={report.WithPropertyBlock}, " +
                $"unsupported geometry/slots={report.UnsupportedGeometryOrSlots} (counters may overlap)");
            foreach (var group in report.SharingCandidates)
                log.AppendLine($"Shared mesh={group.MeshId}, material={group.MaterialId}: " +
                    string.Join(", ", group.Paths));
            Debug.Log(log.ToString());
        }

        private static int[] CopyIds(IReadOnlyList<int> ids)
        {
            var result = new int[ids.Count];
            for (int i = 0; i < ids.Count; i++) result[i] = ids[i];
            return result;
        }
    }
}
#endif
