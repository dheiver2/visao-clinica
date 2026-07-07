import CoreImage
import Foundation
import Vision

/// Amostra de biomarcadores de um único frame (a partir do Vision framework).
struct FrameSample {
    var ear: Double            // abertura do olho (piscar)
    var asymmetry: Double      // assimetria facial
    var gazeX: Double
    var gazeY: Double
    var mouthOpen: Double
    var browRaise: Double
    var roi: [Double]          // cor média [r,g,b] da testa (rPPG)
    var luminance: Double
}

/// Extração de biomarcadores por frame com o Vision framework (nativo),
/// substituindo o MediaPipe.
enum FaceBiomarkers {

    static func bbox(_ obs: VNFaceObservation) -> CGRect { obs.boundingBox }

    /// Centro e largura de uma região de landmarks (espaço normalizado da bbox).
    private static func centroid(_ pts: [CGPoint]) -> CGPoint {
        guard !pts.isEmpty else { return .zero }
        let sx = pts.reduce(0) { $0 + $1.x }, sy = pts.reduce(0) { $0 + $1.y }
        return CGPoint(x: sx / CGFloat(pts.count), y: sy / CGFloat(pts.count))
    }

    private static func spanY(_ pts: [CGPoint]) -> Double {
        guard let mn = pts.map({ $0.y }).min(), let mx = pts.map({ $0.y }).max() else { return 0 }
        return Double(mx - mn)
    }

    private static func spanX(_ pts: [CGPoint]) -> Double {
        guard let mn = pts.map({ $0.x }).min(), let mx = pts.map({ $0.x }).max() else { return 0 }
        return Double(mx - mn)
    }

    static func extract(_ obs: VNFaceObservation, pixelBuffer: CVPixelBuffer) -> FrameSample? {
        guard let lm = obs.landmarks else { return nil }
        let leftEye = lm.leftEye?.normalizedPoints ?? []
        let rightEye = lm.rightEye?.normalizedPoints ?? []
        guard !leftEye.isEmpty, !rightEye.isEmpty else { return nil }

        // EAR aproximado: razão altura/largura do olho (fecha ao piscar).
        let earL = spanX(leftEye) > 0 ? spanY(leftEye) / spanX(leftEye) : 0
        let earR = spanX(rightEye) > 0 ? spanY(rightEye) / spanX(rightEye) : 0
        let ear = (earL + earR) / 2

        // distância interocular (normalização escala-invariante)
        let cL = centroid(leftEye), cR = centroid(rightEye)
        let iod = max(hypot(Double(cL.x - cR.x), Double(cL.y - cR.y)), 1e-6)

        // assimetria: diferença vertical dos cantos da boca
        var asym = 0.0
        var mouthOpen = 0.0
        if let lips = lm.outerLips?.normalizedPoints, lips.count >= 2 {
            let left = lips.min { $0.x < $1.x }!
            let right = lips.max { $0.x < $1.x }!
            asym = abs(Double(left.y - right.y)) / iod
            mouthOpen = spanY(lips) / iod
        }
        if let inner = lm.innerLips?.normalizedPoints, inner.count >= 2 {
            mouthOpen = max(mouthOpen, spanY(inner) / iod)
        }

        // elevação das sobrancelhas (proxy de microexpressão)
        var brow = 0.0
        if let lb = lm.leftEyebrow?.normalizedPoints, !lb.isEmpty {
            brow = abs(Double(centroid(lb).y - cL.y)) / iod
        }

        // olhar: pupila relativa ao centro do olho
        var gx = 0.0, gy = 0.0
        if let lp = lm.leftPupil?.normalizedPoints.first {
            gx = Double(lp.x - cL.x) / (spanX(leftEye) / 2 + 1e-6)
            gy = Double(lp.y - cL.y) / (spanY(leftEye) / 2 + 1e-6)
        }

        // ROI de pele (testa) para rPPG + luminância
        let (roi, lum) = sampleForehead(obs, pixelBuffer)

        return FrameSample(ear: ear, asymmetry: asym, gazeX: gx, gazeY: gy,
                           mouthOpen: mouthOpen, browRaise: brow, roi: roi, luminance: lum)
    }

    /// Cor média da testa (BGRA) — ROI estável de pele para rPPG.
    private static func sampleForehead(_ obs: VNFaceObservation, _ pb: CVPixelBuffer) -> ([Double], Double) {
        let w = CVPixelBufferGetWidth(pb), h = CVPixelBufferGetHeight(pb)
        let box = obs.boundingBox   // normalizado, origem inferior-esquerda
        // converte p/ pixels (origem superior-esquerda)
        let bx = Int(box.minX * CGFloat(w))
        let byTop = Int((1 - box.maxY) * CGFloat(h))
        let bw = Int(box.width * CGFloat(w))
        let bh = Int(box.height * CGFloat(h))
        let rx0 = max(bx + Int(0.30 * Double(bw)), 0)
        let ry0 = max(byTop + Int(0.06 * Double(bh)), 0)
        let rx1 = min(rx0 + Int(0.40 * Double(bw)), w)
        let ry1 = min(ry0 + Int(0.16 * Double(bh)), h)
        guard rx1 > rx0, ry1 > ry0 else { return ([120, 120, 120], 120) }

        CVPixelBufferLockBaseAddress(pb, .readOnly)
        defer { CVPixelBufferUnlockBaseAddress(pb, .readOnly) }
        guard let base = CVPixelBufferGetBaseAddress(pb) else { return ([120, 120, 120], 120) }
        let bpr = CVPixelBufferGetBytesPerRow(pb)
        let ptr = base.assumingMemoryBound(to: UInt8.self)
        var sr = 0.0, sg = 0.0, sb = 0.0, count = 0.0
        var y = ry0
        while y < ry1 {
            var x = rx0
            let row = y * bpr
            while x < rx1 {
                let px = row + x * 4          // BGRA
                sb += Double(ptr[px + 0])
                sg += Double(ptr[px + 1])
                sr += Double(ptr[px + 2])
                count += 1
                x += 1
            }
            y += 1
        }
        guard count > 0 else { return ([120, 120, 120], 120) }
        let r = sr / count, g = sg / count, b = sb / count
        return ([r, g, b], (r + g + b) / 3)
    }
}
