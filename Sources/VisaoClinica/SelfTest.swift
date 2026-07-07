import Foundation

/// Self-test nativo (sem XCTest, roda com Command Line Tools) — valida o núcleo
/// determinístico. Uso:  VisaoClinica --selftest
enum SelfTest {

    private static var failures = 0

    private static func check(_ ok: Bool, _ name: String, _ detail: String = "") {
        if ok { print("  ✓ \(name)") }
        else { print("  ✗ \(name) \(detail)"); failures += 1 }
    }

    private static func synthROI(hr: Double, rr: Double, fps: Double, seconds: Double) -> [[Double]] {
        let n = Int(fps * seconds)
        return (0..<n).map { i in
            let t = Double(i) / fps
            let pulse = sin(2 * .pi * (hr / 60) * t + 0.1 * sin(2 * .pi * (rr / 60) * t))
            let resp = 0.6 * sin(2 * .pi * (rr / 60) * t)
            let base = 120 + 8 * pulse + resp * 4
            return [base + 2, base + 3 * pulse + resp * 6, base * 0.8]
        }
    }

    static func run() -> Never {
        print("Visão Clínica — self-test (núcleo nativo)")

        let roi = synthROI(hr: 72, rr: 15, fps: 30, seconds: 15)
        let v = VitalsEngine.compute(roi: roi, fps: 30)
        check(abs(v.heartRateBpm - 72) < 8, "FC recupera ~72 bpm", "(\(v.heartRateBpm))")
        check(abs(v.respirationBpm - 15) < 4, "Respiração recupera ~15 rpm", "(\(v.respirationBpm))")
        check(v.quality > 0.15, "Qualidade rPPG > 0.15", "(\(v.quality))")

        let empty = VitalsEngine.compute(roi: [], fps: 30)
        check(empty.heartRateBpm == 0 && empty.respirationBpm == 0, "Sem dados → vitais zerados")

        check(validatePassword("curta") != nil, "Senha curta rejeitada")
        check(validatePassword("semnumeros") != nil, "Senha sem número rejeitada")
        check(validatePassword("boaSenha1") == nil, "Senha válida aceita")

        var f = BiomarkerFeatures()
        f.signalQuality = 0.85; f.rppgQuality = 0.8
        f.heartRateBpm = 68; f.hrvSdnnMs = 45; f.hrvRmssdMs = 55
        f.respirationBpm = 15; f.stressIndex = 120
        f.microexpressionRate = 7; f.blinkRatePerMin = 16
        let w = Clinical.computeWellness(f)
        check(w.reliable && (0...100).contains(w.score), "Bem-estar confiável em 0–100", "(\(w.score))")
        check(["ótimo", "bom", "moderado", "alerta"].contains(w.label), "Rótulo de bem-estar válido")

        var fs = BiomarkerFeatures()
        fs.signalQuality = 0.8; fs.microexpressionRate = 18; fs.blinkRatePerMin = 46
        fs.rppgQuality = 0.8; fs.hrvSdnnMs = 12
        let conds = Clinical.evaluateConditions(fs)
        check(!conds.isEmpty && conds.first?.key == "estresse", "Condições ranqueiam estresse no topo")

        // banco: criação de usuário, verificação e auditoria (em tmp)
        let db = AppDatabase()
        let uniq = "selftest_\(Int(Date().timeIntervalSince1970))"
        let err = db.createUser(uniq, "Senha1234", role: "administrador")
        check(err == nil, "Cria usuário admin", "(\(err ?? ""))")
        check(db.verify(uniq, "Senha1234") == "administrador", "Login válido retorna perfil")
        check(db.verify(uniq, "errada") == nil, "Senha errada rejeitada")
        db.log(uniq, "selftest", "ok")
        check(db.audit(limit: 5).contains { $0.event == "selftest" }, "Auditoria registra evento")

        print(failures == 0 ? "\nOK ✓ — todos os testes passaram." : "\nFALHOU — \(failures) teste(s).")
        exit(failures == 0 ? 0 : 1)
    }
}
