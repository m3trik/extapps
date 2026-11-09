// Send to Unity: import the delivered model and show it in the open scene, selected and framed.
// SOURCES = ("scene", "file")
// Rows: __ASSETS_SUBDIR__ __ASSET_NAME__ __PLACE_IN_SCENE__ __FRAME_SELECTION__
//
// A model sent again updates in place: Unity reimports the file and every
// instance in the scene follows, so a scene that holds one gets no second.
using M3trik.UnityScripts;
using UnityEngine;

public static class SendToUnity
{
    [UnityScript]
    public static void Run(ScriptArgs args)
    {
        GameObject model = ScriptHost.LoadModel(args.Asset);
        args.Created(args.Asset);
        var instances = ScriptHost.Instances(model);
        GameObject shown = instances.Count > 0 ? instances[0] : null;
        if (shown != null)
        {
            args.Report($"{model.name} updated in place ({instances.Count} instance(s) in the open scenes).");
        }
        else if (args.GetBool("PLACE_IN_SCENE", true))
        {
            shown = ScriptHost.Place(model);
            string scene = string.IsNullOrEmpty(shown.scene.name) ? "the open (untitled) scene" : shown.scene.name;
            args.Report($"Placed {model.name} in {scene}.");
        }
        ScriptHost.Show(shown != null ? (Object)shown : model, args.GetBool("FRAME_SELECTION", true));
    }
}
