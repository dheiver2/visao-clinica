// swift-tools-version:5.9
import PackageDescription

// Visão Clínica — app 100% nativo macOS (Swift/SwiftUI). Sem Python.
// Frameworks nativos: SwiftUI, AVFoundation, Vision, Accelerate, PDFKit,
// CryptoKit/CommonCrypto, SQLite3 — todos do SDK, sem dependências externas.
let package = Package(
    name: "VisaoClinica",
    platforms: [.macOS(.v13)],
    targets: [
        .executableTarget(
            name: "VisaoClinica",
            path: "Sources/VisaoClinica"
        ),
    ]
)
