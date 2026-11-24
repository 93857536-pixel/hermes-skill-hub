# .NET 8 WPF XPS — verified member list (WeChatExporter session, 2026-09)

Probed via MetadataLoadContext against `microsoft.windowsdesktop.app.ref` 8.0.11.
The OLD API surface (0-arg `new XpsDocument()`, `DocumentSequence.Add`, `FixedPage.Content`,
`SaveAs`, `FormattedText.WidthIncludingDescenders`) is GONE in .NET 8. Do not port legacy docs.

## XpsDocument (System.Windows.Xps.Packaging, in System.Printing.xml)
- `Ctor(Package)`, `Ctor(Package, CompressionOption)`, `Ctor(Package, CompressionOption, string path)`,
  `Ctor(string path, FileAccess)`, `Ctor(string path, FileAccess, CompressionOption)`
- `IXpsFixedDocumentSequenceWriter AddFixedDocumentSequence()`
- `FixedDocumentSequence GetFixedDocumentSequence()`
- `XpsDocumentWriter` static: `XpsDocument.CreateXpsDocumentWriter(XpsDocument)` → `Write(...)`/`WriteAsync(...)`
- props: `FixedDocumentSequenceReader`, `IsReader`, `IsWriter`, `Signatures`, `Thumbnail`, `CoreDocumentProperties`
- `Close()`

## IXpsFixedDocumentSequenceWriter
- `IXpsFixedDocumentWriter AddFixedDocument()`
- `XpsThumbnail AddThumbnail(XpsImageType)`
- `void Commit()`
- props: `PrintTicket set`, `Uri get`

## IXpsFixedDocumentWriter
- `IXpsFixedPageWriter AddFixedPage()`
- `void Commit()`, props `DocumentNumber`, `PrintTicket set`, `Uri get`

## IXpsFixedPageWriter (streaming surface — deliberately awkward)
- `XpsColorContext AddColorContext()`, `XpsFont AddFont([bool obfuscate][, bool])`,
  `XpsImage AddImage(string mimeType)` / `AddImage(XpsImageType)`,
  `XpsResourceDictionary AddResourceDictionary()`, `void Commit()`
- props: `XmlWriter` (raw XPS XML), `LinkTargetStream`, `PageNumber`, `PrintTicket set`, `Uri get`

## FixedDocument (PresentationFramework.xml)
- `Ctor()` only
- props: `DocumentPaginator get`, `Pages get` (PageContentCollection), `PrintTicket get/set`

## FixedPage
- `Ctor()` only; NO `Content` property, NO `Width`/`Height` DPs exposed as props in this ref pack listing
- `UIElementCollection Children get`
- attached: `SetLeft/SetRight/SetTop/SetBottom(UIElement, double)`, `GetLeft/...`, `SetNavigateUri`
- props: `Background`, `BleedBox`, `ContentBox`, `PrintTicket`
- pages are added to `FixedDocument.Pages` (PageContentCollection via IAddChild) — `PageContent`
  (System.Windows.Controls) wraps each `FixedPage`.

## DocumentReference
- `Ctor()`, `SetDocument(FixedDocument)`, `GetDocument(bool)`
- props: `Source` (object), `Name`

## FormattedText (PresentationCore.xml)
- 7-arg ctor: `(string, CultureInfo, FlowDirection, Typeface, double fontSize, Brush, double pixelsPerDip)`
  (+ optional NumberSubstitution / TextFormattingMode overloads)
- width/height: `Extent`, `WidthIncludingPadding`, `LineHeight`, `Baseline` —
  `WidthIncludingDescenders` does NOT exist (renamed pre-.NET 5).
- measuring text headless: `new TextBlock{Text=...,FontFamily=...,FontSize=...}.Measure(inf)` → `DesiredSize`
  works but needs a render-context-safe call; for cross-compiled code prefer estimating or HTML output.

## XML-grep cheat sheet (fast path, read-only)
```bash
REF=~/.nuget/packages/microsoft.windowsdesktop.app.ref/*/ref/net8.0
grep -rl "T:System.Windows.Xps.Packaging.XpsDocument" $REF/*.xml        # locate owning xml
grep -oE '"M:System\.Windows\.Xps\.XpsDocument\.[A-Za-z]+' $F           # methods (anchor! avoids *Writer)
grep -oE '"P:System\.Windows\.Documents\.FixedPage\.[A-Za-z]+' $F      # properties
grep -oE '"M:#1System\.Windows\.Xps\.XpsDocument\.[^"]*"' $F          # ctors (C# generic/ctor marker form)
```

## Decision heuristic
For "printable/shareable document" features on Windows cross-compiled from macOS: emit print-optimized
HTML (pure BCL, logic smoke-testable headless) instead of XPS. XPS is only worth the streaming
writer complexity when XPS is the only acceptable output format.
