import Foundation

/// Resultado de triagem por condição (determinístico, sem LLM).
struct ConditionResult: Identifiable {
    let id = UUID()
    var key: String
    var name: String
    var score: Double          // 0..1
    var level: String          // baixo | moderado | alto | indeterminado
    var factors: [String]
    var rationale: String
    var confidence: Double     // 0..1 (qualidade do sinal)
}

/// Índice de bem-estar (0–100) — síntese estilo apps de vitais.
struct Wellness {
    var score: Int = 0
    var label: String = "indeterminado"
    var stress: Int = 0
    var components: [String: Double] = [:]
    var reliable: Bool = false
}

enum Clinical {

    static func clamp(_ x: Double, _ lo: Double = 0, _ hi: Double = 1) -> Double {
        max(lo, min(hi, x))
    }

    /// Rampa: 0 abaixo de lo, 1 acima de hi.
    static func ramp(_ x: Double, _ lo: Double, _ hi: Double) -> Double {
        hi <= lo ? 0 : clamp((x - lo) / (hi - lo))
    }

    static func level(_ score: Double) -> String {
        if score >= 0.66 { return "alto" }
        if score >= 0.33 { return "moderado" }
        return "baixo"
    }

    // MARK: - Condições

    static func evaluateConditions(_ f: BiomarkerFeatures) -> [ConditionResult] {
        let conf = clamp(f.signalQuality)
        var out: [ConditionResult] = []

        // Estresse / ansiedade: microexpressões + piscar acelerado + VFC reduzida.
        do {
            let micro = ramp(f.microexpressionRate, 6, 20)
            let blink = ramp(f.blinkRatePerMin, 25, 50)
            let hrvGate = ramp(f.rppgQuality, 0.3, 0.7)
            let lowHrv = ramp(40 - f.hrvSdnnMs, 0, 40) * hrvGate
            let score = clamp(0.45 * micro + 0.3 * blink + 0.25 * lowHrv)
            var factors: [String] = []
            if micro > 0.3 { factors.append(String(format: "microexpressões %.0f/min", f.microexpressionRate)) }
            if blink > 0.3 { factors.append("piscar acelerado") }
            if lowHrv > 0.3 { factors.append(String(format: "VFC reduzida (SDNN %.0f ms)", f.hrvSdnnMs)) }
            out.append(ConditionResult(key: "estresse", name: "Estresse / ansiedade",
                                       score: score, level: level(score), factors: factors,
                                       rationale: factors.isEmpty ? "Sem sinais relevantes." :
                                        "Sustentado por: " + factors.joined(separator: "; "),
                                       confidence: conf))
        }

        // Sonolência: piscar muito reduzido ou muito prolongado + pouca movimentação.
        do {
            let lowBlink = ramp(10 - f.blinkRatePerMin, 0, 10)
            let score = clamp(lowBlink)
            var factors: [String] = []
            if lowBlink > 0.3 { factors.append("piscar reduzido") }
            out.append(ConditionResult(key: "sonolencia", name: "Sonolência / fadiga",
                                       score: score, level: level(score), factors: factors,
                                       rationale: factors.isEmpty ? "Sem sinais relevantes." :
                                        "Sustentado por: " + factors.joined(separator: "; "),
                                       confidence: conf))
        }

        // Assimetria facial (indício de paralisia): assimetria dos cantos da boca.
        do {
            let score = clamp(ramp(f.facialAsymmetry, 0.15, 0.5))
            var factors: [String] = []
            if score > 0.3 { factors.append(String(format: "assimetria facial %.2f", f.facialAsymmetry)) }
            out.append(ConditionResult(key: "assimetria", name: "Assimetria facial",
                                       score: score, level: level(score), factors: factors,
                                       rationale: factors.isEmpty ? "Sem sinais relevantes." :
                                        "Sustentado por: " + factors.joined(separator: "; "),
                                       confidence: conf))
        }

        return out.sorted { $0.score > $1.score }
    }

    static func overallRisk(_ conditions: [ConditionResult]) -> String {
        let order = ["indeterminado": -1, "baixo": 0, "moderado": 1, "alto": 2]
        return conditions.map { $0.level }.max { (order[$0] ?? -1) < (order[$1] ?? -1) } ?? "indeterminado"
    }

    // MARK: - Bem-estar

    static func computeWellness(_ f: BiomarkerFeatures) -> Wellness {
        let reliable = f.rppgQuality >= 0.3 && f.signalQuality >= 0.40
        var comp: [String: Double] = [:]

        if let hr = hrNormalcy(f.heartRateBpm) { comp["cardíaco"] = hr }
        if f.hrvRmssdMs > 0 { comp["autonômico"] = clamp(f.hrvRmssdMs / 60.0) }
        else if f.hrvSdnnMs > 0 { comp["autonômico"] = clamp(f.hrvSdnnMs / 60.0) }
        if f.respirationBpm > 0 {
            let rr = f.respirationBpm
            comp["respiratório"] = (12...20).contains(rr) ? 1.0 : clamp(1 - abs(rr - 16) / 16)
        }
        let facial = clamp(0.5 * ramp(f.microexpressionRate, 6, 20) + 0.5 * ramp(f.blinkRatePerMin, 25, 55))
        let stress01 = f.stressIndex > 0 ? clamp(0.6 * ramp(f.stressIndex, 80, 500) + 0.4 * facial) : facial
        comp["calma"] = 1 - stress01

        guard !comp.isEmpty else { return Wellness() }
        let score = Int((100 * comp.values.reduce(0, +) / Double(comp.count)).rounded())
        let stress = Int((100 * stress01).rounded())
        var label = score >= 80 ? "ótimo" : score >= 65 ? "bom" : score >= 45 ? "moderado" : "alerta"
        if !reliable { label = "indeterminado" }
        return Wellness(score: score, label: label, stress: stress,
                        components: comp.mapValues { ($0 * 1000).rounded() / 1000 }, reliable: reliable)
    }

    private static func hrNormalcy(_ hr: Double) -> Double? {
        guard hr > 0 else { return nil }
        if (60...75).contains(hr) { return 1.0 }
        if hr < 60 { return clamp(1 - (60 - hr) / 25) }
        return clamp(1 - (hr - 75) / 45)
    }
}
