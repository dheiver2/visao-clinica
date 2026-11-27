import Foundation

/// Suíte de testes nativa (sem XCTest — roda com Command Line Tools).
/// Uso:  VisaoClinica --selftest
enum SelfTest {

    private static var passed = 0
    private static var failed = 0

    private static func check(_ ok: Bool, _ name: String, _ detail: String = "") {
        if ok { passed += 1; print("  ✓ \(name)") }
        else { failed += 1; print("  ✗ \(name)  \(detail)") }
    }

    private static func near(_ a: Double, _ b: Double, _ tol: Double) -> Bool { abs(a - b) <= tol }

    private static func section(_ title: String) { print("\n▸ \(title)") }

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
        print("Visão Clínica — native test suite (Swift)")

        testDSP()
        testVitals()
        testClinical()
        testWellness()
        testCrypto()
        testDatabase()

        let total = passed + failed
        print("\n" + (failed == 0
            ? "OK ✓ — \(passed)/\(total) tests passed."
            : "FAILED — \(failed) of \(total) tests."))
        exit(failed == 0 ? 0 : 1)
    }

    // MARK: - DSP

    private static func testDSP() {
        section("DSP (signal processing)")
        check(near(DSP.mean([1, 2, 3, 4]), 2.5, 1e-9), "mean")
        check(near(DSP.median([3, 1, 2]), 2, 1e-9), "median (odd)")
        check(near(DSP.median([4, 1, 2, 3]), 2.5, 1e-9), "median (par)")
        check(DSP.std([2, 2, 2]) == 0, "std of constant = 0")

        // detrend remove tendência linear
        let ramp = (0..<50).map { Double($0) * 2 + 5 }
        let dt = DSP.detrend(ramp)
        check(dt.allSatisfy { abs($0) < 1e-6 }, "detrend zera rampa linear")

        // dominantFrequency recovers 1.2 Hz (72 bpm)
        let fps = 30.0
        let sig = (0..<Int(fps * 10)).map { sin(2 * .pi * 1.2 * Double($0) / fps) }
        let (f, snr) = DSP.dominantFrequency(sig, fps: fps, lo: 0.5, hi: 4, step: 0.01)
        check(near(f, 1.2, 0.05), "dominantFrequency recovers 1.2 Hz", "(\(f))")
        check(snr > 5, "High SNR for pure sine", "(\(snr))")

        // detectPeaks conta ~10 picos numa senoide de 1 Hz por 10 s
        let s1 = (0..<Int(fps * 10)).map { sin(2 * .pi * 1.0 * Double($0) / fps) }
        let peaks = DSP.detectPeaks(s1, minDistance: Int(fps / 3))
        check((8...12).contains(peaks.count), "detectPeaks ~10 peaks in 10 s @1 Hz", "(\(peaks.count))")

        // posPulse produz sinal não-trivial
        let pulse = DSP.posPulse(synthROI(hr: 72, rr: 15, fps: fps, seconds: 8), fps: fps)
        check(DSP.std(pulse) > 1e-6, "posPulse produces a non-trivial signal")
    }

    // MARK: - Vitais

    private static func testVitals() {
        section("Vitals (rPPG)")
        for hr in [60.0, 72.0, 90.0] {
            let v = VitalsEngine.compute(roi: synthROI(hr: hr, rr: 15, fps: 30, seconds: 15), fps: 30)
            check(near(v.heartRateBpm, hr, 8), "HR recovers ~\(Int(hr)) bpm", "(\(Int(v.heartRateBpm)))")
        }
        let v = VitalsEngine.compute(roi: synthROI(hr: 72, rr: 15, fps: 30, seconds: 15), fps: 30)
        check(near(v.respirationBpm, 15, 4), "Respiration ~15 rpm", "(\(v.respirationBpm))")
        check(v.hrvSdnnMs > 0, "HRV SDNN > 0")
        check(v.hrvRmssdMs > 0, "HRV RMSSD > 0")
        check(v.hrvPnn50 >= 0 && v.hrvPnn50 <= 1, "pNN50 in [0,1]")
        check(v.stressIndex >= 0, "Stress index ≥ 0")
        check(v.quality > 0.15, "rPPG quality > 0.15", "(\(v.quality))")

        let empty = VitalsEngine.compute(roi: [], fps: 30)
        check(empty.heartRateBpm == 0 && empty.respirationBpm == 0, "No data → zeroed vitals")
        let short = VitalsEngine.compute(roi: synthROI(hr: 72, rr: 15, fps: 30, seconds: 2), fps: 30)
        check(short.heartRateBpm == 0, "Short capture (<4 s) → no HR")
    }

    // MARK: - Clínica

    private static func testClinical() {
        section("Deterministic clinical engine")
        check(Clinical.level(0.1) == "baixo", "level baixo")
        check(Clinical.level(0.5) == "moderado", "level moderado")
        check(Clinical.level(0.8) == "alto", "level alto")
        check(near(Clinical.ramp(15, 10, 20), 0.5, 1e-9), "ramp interpolates")
        check(Clinical.ramp(5, 10, 20) == 0, "ramp below floor = 0")
        check(Clinical.ramp(25, 10, 20) == 1, "ramp above ceiling = 1")

        var stress = BiomarkerFeatures()
        stress.signalQuality = 0.8; stress.rppgQuality = 0.8
        stress.microexpressionRate = 18; stress.blinkRatePerMin = 46; stress.hrvSdnnMs = 12
        let conds = Clinical.evaluateConditions(stress)
        check(!conds.isEmpty, "Conditions returned")
        check(conds.first?.key == "estresse", "Stress ranked on top")
        check(conds.first?.level == "alto" || conds.first?.level == "moderado", "Stress at elevated level")
        check(conds.allSatisfy { $0.confidence == stress.signalQuality }, "Confidence = signal quality")
        check(Clinical.overallRisk(conds) != "indeterminado", "Aggregated overall risk")

        // rosto simétrico e calmo → tudo baixo
        var calm = BiomarkerFeatures()
        calm.signalQuality = 0.9; calm.rppgQuality = 0.9
        calm.microexpressionRate = 2; calm.blinkRatePerMin = 15; calm.hrvSdnnMs = 60
        calm.facialAsymmetry = 0.02
        let calmConds = Clinical.evaluateConditions(calm)
        check(calmConds.allSatisfy { $0.level == "baixo" }, "Calm signals → all low")

        // assimetria alta detectada
        var asym = BiomarkerFeatures()
        asym.signalQuality = 0.8; asym.facialAsymmetry = 0.6
        let asymCond = Clinical.evaluateConditions(asym).first { $0.key == "assimetria" }
        check(asymCond?.level == "alto", "High facial asymmetry detected")
    }

    // MARK: - Bem-estar

    private static func testWellness() {
        section("Wellness score")
        var good = BiomarkerFeatures()
        good.signalQuality = 0.9; good.rppgQuality = 0.85
        good.heartRateBpm = 68; good.hrvSdnnMs = 50; good.hrvRmssdMs = 55
        good.respirationBpm = 15; good.stressIndex = 90
        good.microexpressionRate = 5; good.blinkRatePerMin = 15
        let wg = Clinical.computeWellness(good)
        check(wg.reliable, "Good signal → reliable")
        check((0...100).contains(wg.score), "Score in 0–100")
        check(["ótimo", "bom"].contains(wg.label), "Healthy profile → great/good", "(\(wg.label))")

        var bad = BiomarkerFeatures()
        bad.signalQuality = 0.8; bad.rppgQuality = 0.8
        bad.heartRateBpm = 110; bad.hrvSdnnMs = 8; bad.hrvRmssdMs = 6
        bad.respirationBpm = 28; bad.stressIndex = 600
        bad.microexpressionRate = 20; bad.blinkRatePerMin = 55
        let wb = Clinical.computeWellness(bad)
        check(wb.score < wg.score, "Stressed profile scores lower than the healthy one", "(\(wb.score) < \(wg.score))")
        check(wb.stress > wg.stress, "Higher stress in the stressed profile")

        var poor = BiomarkerFeatures()
        poor.signalQuality = 0.2; poor.rppgQuality = 0.1
        let wp = Clinical.computeWellness(poor)
        check(!wp.reliable && wp.label == "indeterminado", "Poor signal → undetermined")
    }

    // MARK: - Cripto

    private static func testCrypto() {
        section("Crypto / password policy")
        let salt = Crypto.randomSalt()
        let h1 = Crypto.pbkdf2(password: "Senha1234", salt: salt)
        let h2 = Crypto.pbkdf2(password: "Senha1234", salt: salt)
        check(h1 == h2, "PBKDF2 deterministic (same salt)")
        check(h1.count == Crypto.keyLength, "Hash with \(Crypto.keyLength) bytes")
        let h3 = Crypto.pbkdf2(password: "Senha1234", salt: Crypto.randomSalt())
        check(h1 != h3, "Salt diferente → hash diferente")
        check(Crypto.pbkdf2(password: "outra9999", salt: salt) != h1, "Senha diferente → hash diferente")
        let hex = Crypto.hex(h1)
        check(Crypto.data(fromHex: hex) == h1, "hex ↔ data roundtrip")

        check(validatePassword("curta") != nil, "Senha curta rejeitada")
        check(validatePassword("semnumeros") != nil, "Password without digits rejected")
        check(validatePassword("12345678") != nil, "Digits-only password rejected")
        check(validatePassword("boaSenha1") == nil, "Valid password accepted")
    }

    // MARK: - Banco (SQLite, isolado)

    private static func testDatabase() {
        section("Database (isolated SQLite)")
        let path = NSTemporaryDirectory() + "vc_selftest_\(UInt64(Date().timeIntervalSince1970 * 1000)).db"
        defer { try? FileManager.default.removeItem(atPath: path) }
        let db = AppDatabase(path: path)

        check(db.userCount() == 0, "New database has no users")
        check(db.createUser("admin", "Admin1234", role: "administrador") == nil, "Cria admin")
        check(db.userCount() == 1, "userCount = 1 after creation")
        check(db.createUser("admin", "Outro1234", role: "administrador") != nil, "Rejects duplicate user")
        check(db.createUser("x", "fraca", role: "administrador") != nil, "Rejeita senha fraca")
        check(db.createUser("y", "Boa12345", role: "invalido") != nil, "Rejects invalid role")

        check(db.verify("admin", "Admin1234") == "administrador", "Valid login returns role")
        check(db.verify("admin", "errada") == nil, "Senha errada rejeitada")
        check(db.verify("naoexiste", "Admin1234") == nil, "Nonexistent user rejected")

        db.log("admin", "login", "perfil=administrador")
        db.log("admin", "analise", "risco=baixo")
        let audit = db.audit(limit: 10)
        check(audit.count == 2, "Audit log has 2 events")
        check(audit.first?.event == "analise", "Audit log sorts newest first")

        db.saveSession(mode: "triagem", risk: "baixo", wellness: 78, heartRate: 70, featuresJSON: "{}")
        let rows = db.recentSessions(limit: 5)
        check(rows.count == 1, "Session persisted")
        check(rows.first?.wellness == 78 && rows.first?.risk == "baixo", "Session retrieved with correct values")
    }
}
