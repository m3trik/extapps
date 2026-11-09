using System;

namespace M3trik.UnityScripts
{
    /// <summary>
    /// Marks the method a Unity Scripts script runs: <c>public static void
    /// Run(ScriptArgs args)</c> (or with no parameter) on the class named as its
    /// file, which extapps' Unity Scripts panel lists and sends.
    /// </summary>
    [AttributeUsage(AttributeTargets.Method, Inherited = false, AllowMultiple = false)]
    public sealed class UnityScriptAttribute : Attribute
    {
    }
}
