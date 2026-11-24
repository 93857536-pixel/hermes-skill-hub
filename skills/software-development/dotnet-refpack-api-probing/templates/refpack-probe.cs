// Self-contained ref-pack probe: dumps ctors/methods/props of WPF/XPS types
// using MetadataLoadContext against the NuGet ref assemblies (no Windows, no
// Windows runtime — pure metadata, runs on macOS/Linux).
//
// Setup:
//   dotnet new console -n RefProbe
//   dotnet add package System.Reflection.MetadataLoadContext
//   replace this Program.cs, fix the two ref-dir paths, `dotnet run`
//
// Known-good paths (this user's machine):
//   wdp = /Users/yourname/.nuget/packages/microsoft.windowsdesktop.app.ref/8.0.11/ref/net8.0
//   net = /Users/yourname/.dotnet-local/packs/Microsoft.NETCore.App.Ref/8.0.31/ref/net8.0
// Discover your own: `ls ~/.nuget/packages/microsoft.windowsdesktop.app.ref/*/ref/net8.0 | head`
//                     `ls ~/.dotnet-local/packs/Microsoft.NETCore.App.Ref/*/ref/net8.0`

using System;
using System.IO;
using System.Linq;
using System.Reflection;

class P
{
    static void Main()
    {
        string wdp = "/ABSOLUTE/PATH/to/microsoft.windowsdesktop.app.ref/<v>/ref/net8.0";
        string net = "/ABSOLUTE/PATH/to/Microsoft.NETCore.App.Ref/<v>/ref/net8.0";
        var files = new List<string>();
        void Add(string d) { if (Directory.Exists(d)) files.AddRange(Directory.GetFiles(d, "*.dll")); }
        Add(net); Add(wdp);

        // 2-ARG ctor with core-assembly name is REQUIRED (1-arg throws
        // FileNotFoundException 'Could not find core assembly' on non-Windows hosts).
        var mlc = new MetadataLoadContext(new PathAssemblyResolver(files.Distinct().ToArray()), "System.Runtime");

        foreach (var tn in new[]
        {
            "System.Windows.Xps.Packaging.XpsDocument",
            "System.Windows.Xps.Packaging.IXpsFixedDocumentSequenceWriter",
            "System.Windows.Xps.Packaging.IXpsFixedDocumentWriter",
            "System.Windows.Documents.FixedDocument",
            "System.Windows.Documents.FixedPage",
            "System.Windows.Documents.DocumentReference",
            "System.Windows.Media.FormattedText",
        })
        {
            Type t = null;
            foreach (var f in files)
            {
                try
                {
                    var asm = mlc.LoadFromAssemblyPath(f);
                    t = asm.GetType(tn);
                    if (t != null) break;
                }
                catch { /* ref pack may not contain the assembly — skip */ }
            }
            Console.WriteLine($"\n=== {tn} {(t == null ? "[NOT FOUND]" : "")}");
            if (t == null) continue;
            foreach (var c in t.GetConstructors())
                Console.WriteLine("  Ctor(" + string.Join(", ", c.GetParameters().Select(p => p.ParameterType.ToString() + " " + p.Name)) + ")");
            foreach (var m in t.GetMethods(BindingFlags.Public | BindingFlags.Static | BindingFlags.Instance | BindingFlags.DeclaredOnly))
                if (!m.IsSpecialName)
                    Console.WriteLine("  " + (m.IsStatic ? "static " : "") + m.ReturnType.Name + " " + m.Name + "(" + string.Join(", ", m.GetParameters().Select(p => p.ParameterType.Name + " " + p.Name)) + ")");
            foreach (var p in t.GetProperties(BindingFlags.Public | BindingFlags.Instance | BindingFlags.DeclaredOnly))
                Console.WriteLine("  prop " + p.PropertyType.Name + " " + p.Name + " " + (p.CanRead ? "get" : "") + (p.CanWrite ? " set" : ""));
        }
    }
}
