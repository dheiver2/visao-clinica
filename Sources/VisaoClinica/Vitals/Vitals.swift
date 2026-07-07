import Foundation

/// Biomarcadores agregados de uma sessão de captura (equivalente ao
/// BiomarkerFeatures do app Python).
struct BiomarkerFeatures: Codable {
    var durationS: Double = 0
    var frames: Int = 0
    var fps: Double = 0

    var signalQuality: Double = 1
    var faceDetectionRate: Double = 1

    // rPPG / vitais
    var heartRateBpm: Double = 0
    var respirationBpm: Double = 0
    var hrvSdnnMs: Double = 0
    var hrvRmssdMs: Double = 0
    var hrvPnn50: Double = 0
    var lfHfRatio: Double = 0
    var stressIndex: Double = 0
    var rppgQuality: Double = 0

    // faciais / oculomotores
    var blinkRatePerMin: Double = 0
    var facialAsymmetry: Double = 0
    var gazeDispersion: Double = 0
    var microexpressionRate: Double = 0
}

/// Sinais vitais estimados sem contato.
struct Vitals {
    var heartRateBpm: Double = 0
    var respirationBpm: Double = 0
    var hrvSdnnMs: Double = 0
    var hrvRmssdMs: Double = 0
    var hrvPnn50: Double = 0
    var lfHfRatio: Double = 0
    var stressIndex: Double = 0
    var quality: Double = 0
}

enum VitalsEngine {

    /// Estima todos os vitais a partir da série de cor da pele (ROI) e do fps.
    static func compute(roi: [[Double]], fps: Double) -> Vitals {
        var v = Vitals()
        guard roi.count >= Int(fps * 4), fps > 0 else { return v }

        let pulse = DSP.smoothBandpass(DSP.posPulse(roi, fps: fps), fps: fps, lo: 0.7, hi: 4.0)
        guard DSP.std(pulse) > 1e-8 else { return v }

        let (hrFreq, snr) = DSP.dominantFrequency(pulse, fps: fps, lo: 0.7, hi: 4.0, step: 0.01)
        v.heartRateBpm = hrFreq * 60.0
        v.quality = max(0, min(1, (snr - 2.0) / 8.0))

        // intervalos entre batimentos (ms)
        let minDist = max(Int(fps * 60.0 / 200.0), 1)
        let peaks = DSP.detectPeaks(pulse, minDistance: minDist)
        var ibi: [Double] = []
        if peaks.count >= 3 {
            for i in 1..<peaks.count {
                let d = Double(peaks[i] - peaks[i - 1]) / fps * 1000.0
                if d > 300 && d < 1500 { ibi.append(d) }
            }
        }
        if v.quality > 0.2 {
            (v.hrvSdnnMs, v.hrvRmssdMs, v.hrvPnn50) = timeDomain(ibi)
            v.lfHfRatio = lfhf(ibi)
            v.stressIndex = baevsky(ibi)
        }
        v.respirationBpm = respiration(roi: roi, fps: fps)
        return v
    }

    private static func timeDomain(_ ibi: [Double]) -> (Double, Double, Double) {
        guard ibi.count >= 2 else { return (0, 0, 0) }
        let sdnn = DSP.std(ibi)
        var diffs: [Double] = []
        for i in 1..<ibi.count { diffs.append(ibi[i] - ibi[i - 1]) }
        guard !diffs.isEmpty else { return (sdnn, 0, 0) }
        let rmssd = (diffs.reduce(0) { $0 + $1 * $1 } / Double(diffs.count)).squareRoot()
        let pnn50 = Double(diffs.filter { abs($0) > 50 }.count) / Double(diffs.count)
        return (sdnn, rmssd, pnn50)
    }

    /// Razão LF/HF via periodograma do tacograma reamostrado a 4 Hz.
    private static func lfhf(_ ibi: [Double]) -> Double {
        guard ibi.count >= 8 else { return 0 }
        // instantes acumulados (s)
        var t: [Double] = []
        var acc = 0.0
        for d in ibi { acc += d / 1000.0; t.append(acc) }
        let fsI = 4.0
        let start = t.first!, end = t.last!
        guard end > start else { return 0 }
        var tt: [Double] = []
        var x = start
        while x < end { tt.append(x); x += 1.0 / fsI }
        guard tt.count >= 16 else { return 0 }
        // interpolação linear do tacograma
        var tach = [Double](repeating: 0, count: tt.count)
        var j = 0
        for (k, ti) in tt.enumerated() {
            while j < t.count - 1 && t[j + 1] < ti { j += 1 }
            let t0 = j == 0 ? start : t[j]
            let t1 = t[min(j + 1, t.count - 1)]
            let v0 = ibi[min(j, ibi.count - 1)]
            let v1 = ibi[min(j + 1, ibi.count - 1)]
            tach[k] = t1 > t0 ? v0 + (v1 - v0) * (ti - t0) / (t1 - t0) : v0
        }
        let m = DSP.mean(tach)
        tach = tach.map { $0 - m }
        let lf = bandPower(tach, fps: fsI, lo: 0.04, hi: 0.15)
        let hf = bandPower(tach, fps: fsI, lo: 0.15, hi: 0.40)
        return hf > 1e-9 ? lf / hf : 0
    }

    private static func bandPower(_ x: [Double], fps: Double, lo: Double, hi: Double) -> Double {
        var f = lo, total = 0.0
        let n = x.count
        while f <= hi {
            var re = 0.0, im = 0.0
            let c = 2 * Double.pi * f / fps
            for nn in 0..<n { re += x[nn] * cos(c * Double(nn)); im -= x[nn] * sin(c * Double(nn)) }
            total += re * re + im * im
            f += 0.01
        }
        return total
    }

    /// Índice de estresse de Baevsky: SI = AMo / (2·Mo·MxDMn).
    private static func baevsky(_ ibi: [Double]) -> Double {
        guard ibi.count >= 5 else { return 0 }
        let lo = ibi.min()!, hi = ibi.max()!
        guard hi - lo > 1e-6 else { return 0 }
        let binW = 50.0
        let nbins = max(Int((hi - lo) / binW) + 1, 1)
        var hist = [Int](repeating: 0, count: nbins)
        for v in ibi {
            let idx = min(Int((v - lo) / binW), nbins - 1)
            hist[idx] += 1
        }
        let k = hist.indices.max(by: { hist[$0] < hist[$1] })!
        let mo = (lo + (Double(k) + 0.5) * binW) / 1000.0
        let amo = 100.0 * Double(hist[k]) / Double(ibi.count)
        let mxdmn = (hi - lo) / 1000.0
        guard mo > 0, mxdmn > 0 else { return 0 }
        return amo / (2.0 * mo * mxdmn)
    }

    /// Frequência respiratória (rpm) pela modulação lenta do canal verde (RIIV).
    private static func respiration(roi: [[Double]], fps: Double) -> Double {
        guard roi.count >= Int(fps * 8) else { return 0 }
        let g = roi.map { $0[1] }
        let (f, snr) = DSP.dominantFrequency(g, fps: fps, lo: 0.1, hi: 0.5, step: 0.005)
        guard f > 0, snr >= 3.0 else { return 0 }
        return f * 60.0
    }
}
