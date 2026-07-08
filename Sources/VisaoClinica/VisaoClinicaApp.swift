import SwiftUI

/// Entrada do processo: intercepta `--selftest` (validação nativa via CLT) antes
/// de subir a GUI SwiftUI.
@main
enum Entry {
    static func main() {
        let args = CommandLine.arguments
        if args.contains("--selftest") {
            SelfTest.run()   // não retorna (exit)
        }
        if let i = args.firstIndex(of: "--make-icon"), i + 1 < args.count {
            IconGenerator.write(to: args[i + 1])   // não retorna (exit)
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
        .commands {
            CommandGroup(replacing: .newItem) {}   // remove "New Window"
            CommandMenu("Análise") {
                Button("Analisar agora") {
                    NotificationCenter.default.post(name: .analyzeNow, object: nil)
                }
                .keyboardShortcut("r", modifiers: .command)
                Button("Histórico & Tendências…") { model.showHistory = true }
                    .keyboardShortcut("h", modifiers: [.command, .shift])
            }
        }
    }
}
