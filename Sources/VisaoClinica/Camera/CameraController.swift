import AVFoundation
import Foundation
import Vision

/// Captura pela webcam (AVFoundation) + landmarks (Vision), captura guiada em
/// tempo real e agregação de uma janela de análise. Substitui OpenCV+MediaPipe.
final class CameraController: NSObject, AVCaptureVideoDataOutputSampleBufferDelegate {

    let session = AVCaptureSession()
    private let output = AVCaptureVideoDataOutput()
    private let queue = DispatchQueue(label: "camera.frames")
    private let request = VNDetectFaceLandmarksRequest()

    var onGuidance: ((String, Bool) -> Void)?
    var onProgress: ((Double) -> Void)?
    var onResult: ((BiomarkerFeatures) -> Void)?
    var onWaveform: (([Double]) -> Void)?

    private var waveBuf: [Double] = []      // onda de pulso ao vivo (verde da testa)

    private let duration: Double = 12.0
    private var analyzing = false
    private var startTime = Date()

    // séries acumuladas durante a análise
    private var ear: [Double] = [], asym: [Double] = [], gx: [Double] = [], gy: [Double] = []
    private var mouthOpen: [Double] = [], brow: [Double] = [], lum: [Double] = []
    private var roi: [[Double]] = []

    func configure() {
        session.beginConfiguration()
        session.sessionPreset = .high
        let device = AVCaptureDevice.default(.builtInWideAngleCamera, for: .video, position: .front)
            ?? AVCaptureDevice.default(for: .video)
        if let device, let input = try? AVCaptureDeviceInput(device: device),
           session.canAddInput(input) {
            session.addInput(input)
        }
        output.videoSettings = [kCVPixelBufferPixelFormatTypeKey as String: kCVPixelFormatType_32BGRA]
        output.alwaysDiscardsLateVideoFrames = true
        output.setSampleBufferDelegate(self, queue: queue)
        if session.canAddOutput(output) { session.addOutput(output) }
        session.commitConfiguration()
    }

    func start(completion: ((Bool) -> Void)? = nil) {
        AVCaptureDevice.requestAccess(for: .video) { [weak self] ok in
            DispatchQueue.main.async { completion?(ok) }
            guard ok, let self else { return }
            self.queue.async { self.session.startRunning() }
        }
    }

    static var cameraAuthorized: Bool {
        AVCaptureDevice.authorizationStatus(for: .video) != .denied
            && AVCaptureDevice.authorizationStatus(for: .video) != .restricted
    }

    func stop() { queue.async { self.session.stopRunning() } }

    func requestAnalysis() {
        queue.async {
            self.ear = []; self.asym = []; self.gx = []; self.gy = []
            self.mouthOpen = []; self.brow = []; self.lum = []; self.roi = []
            self.startTime = Date()
            self.analyzing = true
        }
    }

    func captureOutput(_ o: AVCaptureOutput, didOutput sb: CMSampleBuffer,
                       from c: AVCaptureConnection) {
        guard let pb = CMSampleBufferGetImageBuffer(sb) else { return }
        let handler = VNImageRequestHandler(cvPixelBuffer: pb, orientation: .up)
        try? handler.perform([request])
        let obs = request.results?.first

        // captura guiada (sempre)
        if let obs {
            let sample = FaceBiomarkers.extract(obs, pixelBuffer: pb)
            let (msg, ok) = guidance(obs, luminance: sample?.luminance ?? 120)
            onGuidance?(msg, ok)
            if let s = sample {
                // onda de pulso ao vivo (canal verde da testa) — sempre
                waveBuf.append(s.roi[1])
                if waveBuf.count > 160 { waveBuf.removeFirst(waveBuf.count - 160) }
                onWaveform?(waveBuf)
                if analyzing {
                    ear.append(s.ear); asym.append(s.asymmetry); gx.append(s.gazeX); gy.append(s.gazeY)
                    mouthOpen.append(s.mouthOpen); brow.append(s.browRaise)
                    lum.append(s.luminance); roi.append(s.roi)
                }
            }
        } else {
            onGuidance?("Rosto não detectado — posicione-se na câmera", false)
        }

        if analyzing {
            let elapsed = Date().timeIntervalSince(startTime)
            onProgress?(min(elapsed / duration, 1))
            if elapsed >= duration { analyzing = false; finish(elapsed: elapsed) }
        }
    }

    private func guidance(_ obs: VNFaceObservation, luminance: Double) -> (String, Bool) {
        let b = obs.boundingBox
        let fw = Double(b.width)
        let cx = Double(b.midX), cy = Double(b.midY)
        if fw < 0.20 { return ("Aproxime-se da câmera", false) }
        if fw > 0.75 { return ("Afaste-se um pouco", false) }
        if abs(cx - 0.5) > 0.18 || abs(cy - 0.5) > 0.20 { return ("Centralize o rosto", false) }
        if luminance < 55 { return ("Ambiente escuro — melhore a iluminação", false) }
        if luminance > 210 { return ("Muita luz — reduza o brilho", false) }
        return ("Enquadramento ótimo — pode analisar", true)
    }

    private func finish(elapsed: Double) {
        let frames = ear.count
        let fps = elapsed > 0 ? Double(frames) / elapsed : 0
        var f = BiomarkerFeatures()
        f.durationS = elapsed
        f.frames = frames
        f.fps = fps

        // piscar: transições abaixo do limiar de EAR
        var blinks = 0
        for i in 1..<max(ear.count, 1) where i < ear.count {
            if ear[i] < 0.20 && ear[i - 1] >= 0.20 { blinks += 1 }
        }
        f.blinkRatePerMin = elapsed > 0 ? Double(blinks) / (elapsed / 60.0) : 0
        f.facialAsymmetry = DSP.mean(asym)
        f.gazeDispersion = (DSP.std(gx) * DSP.std(gx) + DSP.std(gy) * DSP.std(gy)).squareRoot()
        f.microexpressionRate = microexpressionRate(elapsed: elapsed)

        let brightQ = lum.isEmpty ? 0 : Double(lum.filter { $0 >= 55 && $0 <= 210 }.count) / Double(lum.count)
        f.signalQuality = brightQ
        f.faceDetectionRate = frames > 0 ? 1 : 0

        let v = VitalsEngine.compute(roi: roi, fps: fps)
        f.heartRateBpm = v.heartRateBpm
        f.hrvSdnnMs = v.hrvSdnnMs
        f.hrvRmssdMs = v.hrvRmssdMs
        f.hrvPnn50 = v.hrvPnn50
        f.respirationBpm = v.respirationBpm
        f.lfHfRatio = v.lfHfRatio
        f.stressIndex = v.stressIndex
        f.rppgQuality = v.quality

        onResult?(f)
    }

    private func microexpressionRate(elapsed: Double) -> Double {
        guard elapsed > 0 else { return 0 }
        var events = 0
        for series in [mouthOpen, brow] where series.count >= 5 {
            let base = DSP.median(series)
            let mad = max(DSP.median(series.map { abs($0 - base) }), 1e-6)
            for i in 1..<series.count {
                if abs(series[i] - base) > 4 * mad && abs(series[i - 1] - base) <= 4 * mad { events += 1 }
            }
        }
        return Double(events) / (elapsed / 60.0)
    }
}
