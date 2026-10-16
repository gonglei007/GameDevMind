#if UNITY_EDITOR
using System;
using System.Linq;
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.SceneManagement;

namespace GameDevMind.ClientOptimization
{
    public static class UnityRegression
    {
        // Run ONLY in the disposable project described in README: creates test assets.
        public static void Run()
        {
            try
            {
                Verify();
                Debug.Log("PASS: Unity render audit references, MPB, static flags, inactive objects and clean scenes");
                EditorApplication.Exit(0);
            }
            catch (Exception exception)
            {
                Debug.LogException(exception);
                EditorApplication.Exit(1);
            }
        }

        private static void Verify()
        {
            CoreRegression.Run();
            // Unique asset directory permits repeated runs without overwriting earlier fixtures.
            string folder = "Assets/AuditFixture-" + Guid.NewGuid().ToString("N");
            AssetDatabase.CreateFolder("Assets", folder.Substring("Assets/".Length));
            var shader = Shader.Find("Unlit/Color");
            Require(shader != null, "Built-in test shader available");
            var red = new Material(shader) { name = "SameName", color = Color.red };
            var blue = new Material(shader) { name = "SameName", color = Color.blue };
            var mesh = new Mesh { name = "Triangle" };
            mesh.vertices = new[] { Vector3.zero, Vector3.right, Vector3.up };
            mesh.triangles = new[] { 0, 1, 2 };
            AssetDatabase.CreateAsset(red, folder + "/red.mat");
            AssetDatabase.CreateAsset(blue, folder + "/blue.mat");
            AssetDatabase.CreateAsset(mesh, folder + "/triangle.asset");
            var scene = EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Single);
            Require(EditorSceneManager.SaveScene(scene, folder + "/main.unity"), "Initialize saved fixture scene");
            var otherScene = EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Additive);
            Require(EditorSceneManager.SaveScene(otherScene, folder + "/other.unity"), "Initialize additive fixture");
            var preview = EditorSceneManager.NewPreviewScene();
            try
            {
                var a = Add(scene, "A", mesh, red);
                Add(scene, "B", mesh, red);
                var different = Add(scene, "C", mesh, blue);
                Add(scene, "Inactive", mesh, red).gameObject.SetActive(false);
                var blocked = Add(scene, "MPB", mesh, red);
                var block = new MaterialPropertyBlock();
                block.SetColor("_Color", Color.green);
                blocked.SetPropertyBlock(block);
                Add(scene, "NoMesh", null, red);
                Add(scene, "NullMaterial", mesh, (Material)null);
                Add(scene, "Disabled", mesh, red).enabled = false;
                Add(scene, "ExtraSlot", mesh, red, blue);
                Add(otherScene, "OtherScene", mesh, red);
                GameObjectUtility.SetStaticEditorFlags(a.gameObject, StaticEditorFlags.BatchingStatic);
                Require(EditorSceneManager.SaveScene(scene, folder + "/main.unity"), "Save main fixture");
                Require(EditorSceneManager.SaveScene(otherScene, folder + "/other.unity"), "Save additive fixture");
                var before = scene.GetRootGameObjects().Select(Snapshot).ToArray();
                var flags = GameObjectUtility.GetStaticEditorFlags(a.gameObject);
                var rows = RenderAuditEditor.Collect(scene);
                var report = RenderAuditCore.Analyze(rows);
                Require(report.Renderers == 9 && report.DistinctMaterials == 2, "Scene scope and material identities");
                Require(report.InactiveOrDisabled == 2 && report.WithPropertyBlock == 1 &&
                    report.UnsupportedGeometryOrSlots == 3, "Actual Unity state and invalid slots");
                Require(report.SharingCandidates.Count == 1 &&
                    report.SharingCandidates[0].Paths.Count == 2, "Only A/B share eligible references");
                Require(different.sharedMaterial == blue && a.sharedMaterial == red && red.color == Color.red &&
                    blue.color == Color.blue, "Same shader/name/texture must not merge different materials");
                Require(RenderAuditEditor.Collect(otherScene).Count == 1, "Additive scene collected separately");
                bool rejected = false;
                try { RenderAuditEditor.Collect(preview); }
                catch (ArgumentException) { rejected = true; }
                Require(rejected, "Preview scenes excluded");
                RenderAuditEditor.Run(); // Exercise actual menu entry across loaded scenes.
                Require(!scene.isDirty && !otherScene.isDirty, "Read-only audit must leave clean scenes clean");
                Require(red.color == Color.red && blue.color == Color.blue, "Material asset properties unchanged");
                Require(before.SequenceEqual(scene.GetRootGameObjects().Select(Snapshot)), "Serialized state unchanged");
                var afterBlock = new MaterialPropertyBlock();
                blocked.GetPropertyBlock(afterBlock);
                Require(afterBlock.GetColor("_Color") == Color.green && blocked.HasPropertyBlock(), "MPB unchanged");
                Require(GameObjectUtility.GetStaticEditorFlags(a.gameObject) == flags, "Static flags unchanged");
            }
            finally
            {
                EditorSceneManager.ClosePreviewScene(preview);
                EditorSceneManager.CloseScene(otherScene, true);
                EditorSceneManager.CloseScene(scene, true);
            }
        }

        private static MeshRenderer Add(Scene scene, string name, Mesh mesh, params Material[] materials)
        {
            var go = new GameObject(name);
            SceneManager.MoveGameObjectToScene(go, scene);
            go.AddComponent<MeshFilter>().sharedMesh = mesh;
            var renderer = go.AddComponent<MeshRenderer>();
            renderer.sharedMaterials = materials;
            return renderer;
        }

        private static string Snapshot(GameObject go) => EditorJsonUtility.ToJson(go) +
            EditorJsonUtility.ToJson(go.GetComponent<MeshFilter>()) +
            EditorJsonUtility.ToJson(go.GetComponent<MeshRenderer>());

        private static void Require(bool condition, string message)
        {
            if (!condition) throw new InvalidOperationException(message);
        }
    }
}
#endif
