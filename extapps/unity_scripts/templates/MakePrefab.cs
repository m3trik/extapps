// Make Prefab: import the delivered model and save a prefab variant of it that follows the model.
// SOURCES = ("scene", "file")
// Rows: __ASSETS_SUBDIR__ __ASSET_NAME__ __PREFAB_FOLDER__
//
// A variant follows its model, so a model sent again updates the prefab too;
// one already at the path is kept as it is, with your overrides on it.
using M3trik.UnityScripts;
using UnityEditor;
using UnityEngine;

public static class MakePrefab
{
    [UnityScript]
    public static void Run(ScriptArgs args)
    {
        GameObject model = ScriptHost.LoadModel(args.Asset);
        args.Created(args.Asset);
        string folder = ScriptHost.AssetsFolder(args.GetString("PREFAB_FOLDER", "Prefabs"), "Prefabs");
        string path = ScriptHost.SaveVariant(model, folder);
        args.Created(path);
        args.Report($"{model.name}'s prefab: {path}");
        ScriptHost.Show(AssetDatabase.LoadAssetAtPath<GameObject>(path), false);
    }
}
