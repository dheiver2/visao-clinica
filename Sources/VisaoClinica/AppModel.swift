import AppKit
import Foundation
import SwiftUI

extension Notification.Name {
    static let analyzeNow = Notification.Name("VisaoClinica.analyzeNow")
}

/// Estado central do app (MVVM) — autenticação, câmera e resultado clínico.
@MainActor
final class AppModel: ObservableObject {

    // autenticação / controle de acesso (barreira simples local — credenciais
    // fixas admin/admin, sem hash/persistência; login é exigido a cada abertura)
    @Published var isAuthenticated = false
    @Published var currentUser = ""
    @Published var role = ""
    @Published var loginError = ""

    // câmera / captura guiada
    @Published var guidanceText = "Iniciando câmera…"
    @Published var guidanceOK = false
    @Published var isAnalyzing = false
    @Published var progress = 0.0
    @Published var statusText = "Faça login para começar."
    @Published var waveform: [Double] = []
    @Published var cameraDenied = false
    @Published var showHistory = false

    // resultado
    @Published var features: BiomarkerFeatures?
    @Published var wellness: Wellness?
    @Published var conditions: [ConditionResult] = []
    @Published var risk = "—"
    @Published var hasResult = false

    let db = AppDatabase()
    let camera = CameraController()

    init() {
        camera.onGuidance = { [weak self] msg, ok in
            Task { @MainActor in self?.guidanceText = msg; self?.guidanceOK = ok }
        }
        camera.onProgress = { [weak self] p in
            Task { @MainActor in self?.progress = p }
        }
        camera.onResult = { [weak self] f in
            Task { @MainActor in self?.handleResult(f) }
        }
        camera.onWaveform = { [weak self] w in
            Task { @MainActor in self?.waveform = w }
        }
        NotificationCenter.default.addObserver(forName: .analyzeNow, object: nil, queue: .main) {
            [weak self] _ in
            MainActor.assumeIsolated { self?.analyzeIfPossible() }   // já na fila .main
        }
    }

    func analyzeIfPossible() {
        if isAuthenticated && !isAnalyzing { analyze() }
    }

    func recentSessions() -> [AppDatabase.SessionRow] { db.recentSessions(limit: 60) }

    func openSystemCameraSettings() {
        if let url = URL(string: "x-apple.systempreferences:com.apple.preference.security?Privacy_Camera") {
            NSWorkspace.shared.open(url)
        }
    }

    // MARK: - Autenticação
    // Barreira de acesso simples e local: credenciais fixas ("admin"/"admin",
    // case-sensitive), sem hash, sem Keychain, sem persistência entre execuções.
    // isAuthenticated nasce false a cada abertura do app — login é sempre exigido.

    func login(user: String, password: String) {
        if user == "admin" && password == "admin" {
            currentUser = user; role = "administrador"; isAuthenticated = true; loginError = ""
            db.log(user, "login", "perfil=\(role)")
            statusText = "Câmera ativa — clique em Analisar."
            startCamera()
        } else {
            db.log(user, "login_falha")
            loginError = "Usuário ou senha inválidos."
        }
    }

    // MARK: - Câmera / análise

    func startCamera() {
        camera.configure()
        camera.start { [weak self] granted in
            self?.cameraDenied = !granted
            if granted { self?.guidanceText = "Posicione o rosto na câmera" }
        }
    }

    func analyze() {
        isAnalyzing = true
        hasResult = false
        progress = 0
        statusText = "Analisando… olhe para a câmera (12s)."
        camera.requestAnalysis()
    }

    private func handleResult(_ f: BiomarkerFeatures) {
        isAnalyzing = false
        progress = 1
        features = f
        let conds = Clinical.evaluateConditions(f)
        let well = Clinical.computeWellness(f)
        let riskLevel = Clinical.overallRisk(conds)
        conditions = conds
        wellness = well
        risk = riskLevel
        hasResult = true
        statusText = String(format: "Concluído — qualidade do sinal %.0f%%.", f.signalQuality * 100)

        let json = (try? JSONEncoder().encode(f)).flatMap { String(data: $0, encoding: .utf8) } ?? ""
        db.saveSession(mode: "triagem", risk: riskLevel, wellness: well.score,
                       heartRate: f.heartRateBpm, featuresJSON: json)
        db.log(currentUser, "analise", "risco=\(riskLevel) bem-estar=\(well.score)")
    }
}
