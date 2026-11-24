---
name: dotnet-refpack-api-probing
description: Use when checking .NET/WPF API signatures headless.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [dotnet, wpf, windows, refpack, cross-compile, macos, api]
    related_skills: [swift-coretext-offline-pdf, winui-dotnet-development]
---

# Probing .NET / WPF API Signatures from Ref Packs (no Windows box)

Cross-compiling `net8.0-windows` WPF/WinUI projects on macOS (`dotnet build -p:EnableWindowsTargeting=true`) validates signatures but NOT runtime behavior, and WPF API surfaces in .NET 8 differ from old .NET Framework-era blog code. Instead of guessing and burning build cycles, probe the real API surface from the NuGet ref packs on the dev machine.

## When to Use

- Writing WPF/WinForms/XPS/WinUI code on a non-Windows host and unsure of the exact constructor/method/property signatures.
- A build throws CS0117/CS1061/CS1503 on UI-framework types and the online docs you trust describe an older API generation.
- Validating that a hand-written cross-compiled Windows file will compile before the 3-5 min dotnet build round-trip.

Don't use for: pure-BCL code (Json/BCL APIs are version-stable, just compile) or when a Windows machine/CI is available (compile-check there instead).

## Probe 1 — XML doc grep (fastest, read-only)

Ref packs ship `.xml` doc files next to each ref assembly, one line per member:

```bash
REF=~/.nuget/packages/microsoft.windowsdesktop.app.ref/*/ref/net8.0
# exact-member grep — ALWAYS anchor so "XpsDocument" does not also match
# "XpsDocumentWriter" / "VisualsToXpsDocument" (same-assembly siblings):
grep -oE '"M:System\.Windows\.Xps\.XpsDocument\.[A-Za-z]+' $REF/System.Printing.xml
grep -oE '"P:System\.Windows\.Documents\.FixedPage\.[A-Za-z]+' $REF/PresentationFramework.xml
```

Which xml file holds a type: `grep -rl "T:Full.Type.Name" $REF/*.xml` (in .NET 8 WPF: `XpsDocument`/`DocumentReference` members live in `System.Printing.xml` + `PresentationFramework.xml`; `FixedPage`/`FixedDocument` in `PresentationFramework.xml`).

## Probe 2 — MetadataLoadContext reflection (full member dump incl. ctors)

Template: `templates/refpack-probe.cs` — a self-contained console program.

```bash
dotnet new console -n RefProbe && dotnet add package System.Reflection.MetadataLoadContext
# then drop the template in and set the two ref-dir paths for your SDK:
#   wdp = ~/.nuget/packages/microsoft.windowsdesktop.app.ref/<v>/ref/net8.0
#   net = ~/.dotnet-local/packs/Microsoft.NETCore.App.Ref/<v>/ref/net8.0
dotnet run
```

Pitfalls (each cost a round this session):
- Constructor: `new MetadataLoadContext(new PathAssemblyResolver(files), "System.Runtime")` — the **2-arg form with core-assembly name is required**; the 1-arg form throws `FileNotFoundException: Could not find core assembly` on a host that lacks the target framework's shared framework.
- `mlc.Assemblies` does NOT exist — enumerate the ref dir and `mlc.LoadFromAssemblyPath(path)` each DLL, then walk `asm.DefinedTypes.ToList()` (`DefinedTypes` is `IEnumerable<TypeInfo>`, not an array — `var ts` + LINQ, not `Type[]`).
- `mlc.GetType(fullName)` single-arg overload does not exist either.
- Warnings CS8600 on `Type t = null` are cosmetic; ignore or suppress.

## Known-good .NET 8 findings (session-verified)

- **WPF XPS is the NEW `System.Windows.Xps.Packaging.XpsDocument` API**, not the legacy pattern from pre-.NET-CORE docs: no 0-arg `new XpsDocument()`, no `XpsDocument.Create(path)`, no `DocumentSequence.Add(ref)`, no `SaveAs(uri)`, no `FixedPage.Content` property, no `FixedDocument.AddFixedPage(page)`.
  - Ctor: `new XpsDocument(string path, FileAccess)` (+optional `CompressionOption`).
  - `AddFixedDocumentSequence()` → `IXpsFixedDocumentSequenceWriter.AddFixedDocument()` → `IXpsFixedDocumentWriter.AddFixedPage()` (streaming XML writers — a deliberately awkward surface).
  - In-memory side: `FixedDocument.Pages` is `PageContentCollection` (add via `IAddChild`), `FixedPage.Children` is `UIElementCollection` + `FixedPage.SetLeft/SetTop` attached properties.
  - `DocumentReference` has `SetDocument(FixedDocument)` + `Source` property, not `DocumentSource`.
  - `FormattedText`: 7-arg ctor ends with `pixelsPerDip`; width is `WidthIncludingPadding`/`Extent` — **`WidthIncludingDescenders` does not exist** (pre-.NET 5 name).
  - XPS write path also needs `PageContent` (`System.Windows.Controls`) wrapping each `FixedPage`.
  - Full verified member list (props/ctors/attached + XML-grep cheat sheet): `references/xps-dotnet8-members.md`.
  - Re-probe with `templates/refpack-probe.cs` if your SDK's ref pack differs from 8.0.11.
- **Runtime caveat**: even when WPF/XPS cross-compiles cleanly, the output path is untestable headless (no display, no Windows) — signature checks ≠ it works.

## Decision heuristic from the WeChatExporter session

When the *user-facing artifact* of a Windows feature is "a printable/shareable document", generating a **print-optimized HTML** (`@page{size:A4;margin:14mm}`, semantic `.msg/.who/.ts` markup, zero UI dependencies) beats generating XPS/PDF via UI frameworks: pure-BCL code, cross-compiles with 0 warnings, and the logic (JSON parsing, ZIP writing) can actually be smoke-tested on macOS via `dotnet new console` running the same source file. Reserve WPF output for features where XPS/PDF is the only acceptable format.

## C# gotchas that surfaced alongside

- `out var x` declared inside a `&&` chain can hit CS0165 "use of unassigned local" when the compiler can't prove assignment across short-circuit paths → pre-declare: `JsonElement m1 = default;` then `TryGetProperty("message", out m1)`.
- JSON kind literals: it's `JsonValueKind.Object`, not `JsonObject` (missing-namespace errors read as "JsonObject does not exist in the current context").
- Millis/seconds timestamps: `> 10_000_000_000L` → divide by 1000 before `DateTimeOffset.FromUnixTimeSeconds`.

## Verification

- Probe output lists the exact ctors/methods/props you intend to call; every call in your code maps 1:1 to a probed member.
- `dotnet build -p:EnableWindowsTargeting=true` → 0 errors.
- Any pure-BCL subset: run it on the dev host (`dotnet run` with a 5-line driver) to verify logic, not just compilation.
