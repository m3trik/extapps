using System;
using System.Collections.Generic;
using System.IO;
using UnityEditor;
using UnityEngine;
using UnityEngine.SceneManagement;
using Object = UnityEngine.Object;

namespace M3trik.UnityScripts
{
    /// <summary>
    /// What the built-in scripts do, for any script to call: load a delivered
    /// model, find its instances in the open scene, place one through Undo,
    /// select and frame it, save a prefab variant of it.
    /// </summary>
    public static class ScriptHost
    {
        /// <summary>The model <paramref name="assetPath"/> imports as.</summary>
        /// <exception cref="InvalidOperationException">Unity imported nothing a scene can hold there.</exception>
        public static GameObject LoadModel(string assetPath)
        {
            if (string.IsNullOrEmpty(assetPath))
                throw new InvalidOperationException("This script takes an asset: pick a Source in the panel.");
            var model = AssetDatabase.LoadAssetAtPath<GameObject>(assetPath);
            if (model == null)
                throw new InvalidOperationException(
                    $"{assetPath} imported as nothing a scene can hold (is it a model file, and did it import without errors?).");
            return model;
        }

        /// <summary>The open scenes' outermost instances of <paramref name="model"/>.
        /// A re-delivered model updates these by itself: Unity reimports the file
        /// in place and every instance follows.</summary>
        public static List<GameObject> Instances(GameObject model)
        {
            var found = new List<GameObject>();
            for (int i = 0; i < SceneManager.sceneCount; i++)
            {
                Scene scene = SceneManager.GetSceneAt(i);
                if (!scene.isLoaded) continue;
                foreach (GameObject root in scene.GetRootGameObjects())
                {
                    foreach (Transform t in root.GetComponentsInChildren<Transform>(true))
                    {
                        GameObject go = t.gameObject;
                        if (PrefabUtility.IsOutermostPrefabInstanceRoot(go)
                            && PrefabUtility.GetCorrespondingObjectFromOriginalSource(go) == model)
                            found.Add(go);
                    }
                }
            }
            return found;
        }

        /// <summary>An instance of <paramref name="model"/> in the active scene, one undo step.</summary>
        public static GameObject Place(GameObject model)
        {
            var go = (GameObject)PrefabUtility.InstantiatePrefab(model, SceneManager.GetActiveScene());
            Undo.RegisterCreatedObjectUndo(go, "Place " + model.name);
            return go;
        }

        /// <summary>Select <paramref name="go"/>, ping it in the Hierarchy and, when
        /// <paramref name="frame"/>, frame it in the last active Scene view.</summary>
        public static void Show(Object go, bool frame)
        {
            if (go == null) return;
            Selection.activeObject = go;
            EditorGUIUtility.PingObject(go);
            if (!frame) return;
            SceneView view = SceneView.lastActiveSceneView;
            if (view != null) view.FrameSelected();
        }

        /// <summary>A prefab variant of <paramref name="model"/> at
        /// <c>&lt;folder&gt;/&lt;model&gt;.prefab</c>; one there already is kept (a
        /// variant follows its model). Returns its path.</summary>
        public static string SaveVariant(GameObject model, string folder)
        {
            EnsureFolder(folder);
            string path = folder.TrimEnd('/') + "/" + model.name + ".prefab";
            if (AssetDatabase.LoadAssetAtPath<GameObject>(path) != null) return path;
            var instance = (GameObject)PrefabUtility.InstantiatePrefab(model);
            try
            {
                PrefabUtility.SaveAsPrefabAsset(instance, path);
            }
            finally
            {
                Object.DestroyImmediate(instance);
            }
            return path;
        }

        /// <summary>The project folder <paramref name="path"/> (<c>Assets/A/B</c>), made
        /// folder by folder where missing.</summary>
        public static void EnsureFolder(string path)
        {
            path = (path ?? "").Replace('\\', '/').TrimEnd('/');
            if (path != "Assets" && !path.StartsWith("Assets/", StringComparison.Ordinal))
                throw new ArgumentException($"'{path}' is no project folder: it starts with Assets/.");
            string current = "Assets";
            foreach (string part in path.Split('/'))
            {
                if (part == "Assets" && current == "Assets") continue;
                string next = current + "/" + part;
                if (!AssetDatabase.IsValidFolder(next)) AssetDatabase.CreateFolder(current, part);
                current = next;
            }
        }

        /// <summary><paramref name="sub"/> as a project folder under Assets/: blank
        /// gives <paramref name="fallback"/>, "/" gives Assets/ itself.</summary>
        public static string AssetsFolder(string sub, string fallback = "Imported")
        {
            sub = (sub ?? "").Trim().Replace('\\', '/');
            if (sub == "/") return "Assets";
            if (sub.Length == 0) sub = fallback;
            sub = sub.Trim('/');
            if (sub.StartsWith("Assets/", StringComparison.Ordinal) || sub == "Assets") return sub;
            return "Assets/" + sub;
        }

        /// <summary>The project path of <paramref name="file"/> under this project, or null.</summary>
        public static string ProjectPath(string file)
        {
            string root = Path.GetFullPath(".").Replace('\\', '/').TrimEnd('/') + "/";
            string full = Path.GetFullPath(file).Replace('\\', '/');
            return full.StartsWith(root, StringComparison.OrdinalIgnoreCase) ? full.Substring(root.Length) : null;
        }
    }
}
