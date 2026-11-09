// Reimport Folder: reimport everything under a folder of the project's Assets, as Unity's Reimport does.
// SOURCES = ()
// Rows: __ASSETS_SUBDIR__
using System;
using M3trik.UnityScripts;
using UnityEditor;

public static class ReimportFolder
{
    [UnityScript]
    public static void Run(ScriptArgs args)
    {
        string folder = ScriptHost.AssetsFolder(args.GetString("ASSETS_SUBDIR", "Imported"));
        if (!AssetDatabase.IsValidFolder(folder))
            throw new InvalidOperationException($"No folder {folder} in the project.");
        AssetDatabase.ImportAsset(folder, ImportAssetOptions.ImportRecursive | ImportAssetOptions.ForceUpdate);
        args.Report($"Reimported {folder}.");
    }
}
