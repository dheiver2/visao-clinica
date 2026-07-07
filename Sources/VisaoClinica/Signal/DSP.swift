import Foundation

/// Processamento de sinal nativo (Swift) para os biomarcadores — equivalente ao
/// que antes era feito em NumPy/SciPy. Sem dependências externas.
enum DSP {

    static func mean(_ x: [Double]) -> Double {
        x.isEmpty ? 0 : x.reduce(0, +) / Double(x.count)
    }

    static func std(_ x: [Double]) -> Double {
        guard x.count > 1 else { return 0 }
        let m = mean(x)
        let v = x.reduce(0) { $0 + ($1 - m) * ($1 - m) } / Double(x.count)
        return v.squareRoot()
    }

    /// Remove tendência linear (deriva lenta de iluminação/pose).
    static func detrend(_ x: [Double]) -> [Double] {
        let n = x.count
        guard n >= 2 else { return x.map { $0 - mean(x) } }
        let t = (0..<n).map { Double($0) }
        let mt = mean(t), mx = mean(x)
        var num = 0.0, den = 0.0
        for i in 0..<n {
            num += (t[i] - mt) * (x[i] - mx)
            den += (t[i] - mt) * (t[i] - mt)
        }
        let a = den == 0 ? 0 : num / den
        let b = mx - a * mt
        return (0..<n).map { x[$0] - (a * Double($0) + b) }
    }

    /// Frequência dominante (Hz) e SNR numa banda, via periodograma direto com
    /// janela de Hann. `step` controla a resolução (fina p/ respiração).
    static func dominantFrequency(_ x0: [Double], fps: Double, lo: Double, hi: Double,
                                  step: Double = 0.02) -> (freq: Double, snr: Double) {
        let x = detrend(x0)
        let n = x.count
        guard n >= 16, fps > 0, hi > lo else { return (0, 0) }
        // janela de Hann
        var w = [Double](repeating: 0, count: n)
        for i in 0..<n {
            let h = 0.5 - 0.5 * cos(2 * Double.pi * Double(i) / Double(n - 1))
            w[i] = x[i] * h
        }
        var freqs: [Double] = []
        var f = lo
        while f <= hi { freqs.append(f); f += step }
        var powers = [Double](repeating: 0, count: freqs.count)
        for (k, fr) in freqs.enumerated() {
            var re = 0.0, im = 0.0
            let c = 2 * Double.pi * fr / fps
            for nn in 0..<n {
                let ang = c * Double(nn)
                re += w[nn] * cos(ang)
                im -= w[nn] * sin(ang)
            }
            powers[k] = re * re + im * im
        }
        guard let peakIdx = powers.indices.max(by: { powers[$0] < powers[$1] }) else { return (0, 0) }
        let med = median(powers)
        let snr = med > 0 ? powers[peakIdx] / med : 0
        return (freqs[peakIdx], snr)
    }

    static func median(_ x: [Double]) -> Double {
        guard !x.isEmpty else { return 0 }
        let s = x.sorted()
        let m = s.count / 2
        return s.count % 2 == 0 ? (s[m - 1] + s[m]) / 2 : s[m]
    }

    /// Sinal de pulso rPPG pelo método POS (Plane-Orthogonal-to-Skin, Wang 2017).
    /// `rgb`: N amostras de cor média [r,g,b] da ROI de pele.
    static func posPulse(_ rgb: [[Double]], fps: Double) -> [Double] {
        let n = rgb.count
        guard n >= 16 else { return [Double](repeating: 0, count: max(n, 0)) }
        let winLen = max(Int(fps * 1.6), 8)
        var h = [Double](repeating: 0, count: n)
        var m = 0
        while m < n - winLen {
            var mu = [0.0, 0.0, 0.0]
            for k in 0..<winLen { for c in 0..<3 { mu[c] += rgb[m + k][c] } }
            for c in 0..<3 { mu[c] /= Double(winLen); if mu[c] == 0 { mu[c] = 1e-9 } }
            var s0 = [Double](repeating: 0, count: winLen)
            var s1 = [Double](repeating: 0, count: winLen)
            for k in 0..<winLen {
                let r = rgb[m + k][0] / mu[0]
                let g = rgb[m + k][1] / mu[1]
                let b = rgb[m + k][2] / mu[2]
                s0[k] = g - b             // linha [0, 1, -1]
                s1[k] = -2 * r + g + b    // linha [-2, 1, 1]
            }
            let sd1 = std(s1) == 0 ? 1e-9 : std(s1)
            let alpha = std(s0) / sd1
            var p = [Double](repeating: 0, count: winLen)
            for k in 0..<winLen { p[k] = s0[k] + alpha * s1[k] }
            let pm = mean(p)
            for k in 0..<winLen { h[m + k] += (p[k] - pm) }
            m += 1
        }
        return h
    }

    /// Passa-banda simples (média móvel de remoção de baixa freq + suavização) para
    /// preparar a detecção de picos do pulso na banda cardíaca.
    static func smoothBandpass(_ x: [Double], fps: Double, lo: Double, hi: Double) -> [Double] {
        let d = detrend(x)
        // suavização por média móvel curta (remove ruído de alta freq)
        let win = max(Int(fps / hi / 2), 1)
        guard win > 1 else { return d }
        var out = [Double](repeating: 0, count: d.count)
        for i in 0..<d.count {
            let a = max(0, i - win), b = min(d.count - 1, i + win)
            var s = 0.0
            for j in a...b { s += d[j] }
            out[i] = d[i] - s / Double(b - a + 1) + d[i]  // realça oscilação na banda
        }
        return out
    }

    /// Índices de picos (máximos locais) com distância mínima entre picos.
    static func detectPeaks(_ x: [Double], minDistance: Int) -> [Int] {
        guard x.count >= 3 else { return [] }
        var peaks: [Int] = []
        var i = 1
        while i < x.count - 1 {
            if x[i] > x[i - 1] && x[i] >= x[i + 1] {
                if let last = peaks.last, i - last < max(minDistance, 1) {
                    if x[i] > x[last] { peaks[peaks.count - 1] = i }
                } else {
                    peaks.append(i)
                }
            }
            i += 1
        }
        return peaks
    }
}
