import SwiftUI

/// Entrada do processo: intercepta `--selftest` (validação nativa via CLT) antes
/// de subir a GUI SwiftUI.
@main
enum Entry {
    static func main() {
        if CommandLine.arguments.contains("--selftest") {
            SelfTest.run()   // não retorna (exit)
        }
        VisaoClinicaApp.main()
    }
}

/// App nativo macOS (SwiftUI). 100% local, sem Python.
struct VisaoClinicaApp: App {
    @StateObject private var model = AppModel()

    var body: some Scene {
        WindowGroup("Visão Clínica") {
            ContentView().environmentObject(model)
        }
        .windowResizability(.contentMinSize)
    }
}
