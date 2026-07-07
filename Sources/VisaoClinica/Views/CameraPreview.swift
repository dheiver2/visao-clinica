import AVFoundation
import SwiftUI

/// Preview ao vivo da câmera (AVCaptureVideoPreviewLayer) embutido no SwiftUI.
struct CameraPreview: NSViewRepresentable {
    let session: AVCaptureSession

    func makeNSView(context: Context) -> PreviewNSView {
        let view = PreviewNSView()
        view.wantsLayer = true
        let layer = AVCaptureVideoPreviewLayer(session: session)
        layer.videoGravity = .resizeAspectFill
        view.previewLayer = layer
        view.layer = layer
        return view
    }

    func updateNSView(_ nsView: PreviewNSView, context: Context) {}
}

final class PreviewNSView: NSView {
    var previewLayer: AVCaptureVideoPreviewLayer?
    override func layout() {
        super.layout()
        previewLayer?.frame = bounds
    }
}

extension Color {
    init(hex: String) {
        var s = hex; if s.hasPrefix("#") { s.removeFirst() }
        var v: UInt64 = 0; Scanner(string: s).scanHexInt64(&v)
        self.init(.sRGB,
                  red: Double((v >> 16) & 0xff) / 255,
                  green: Double((v >> 8) & 0xff) / 255,
                  blue: Double(v & 0xff) / 255)
    }
}

/// Paleta do app (alinhada ao tema premium black).
enum Palette {
    static let bg = Color(hex: "0a0c10")
    static let panel = Color(hex: "0f1216")
    static let panel2 = Color(hex: "161a20")
    static let border = Color(hex: "23272f")
    static let text = Color(hex: "eef0f3")
    static let muted = Color(hex: "878d99")
    static let accent = Color(hex: "5b8cff")
    static let green = Color(hex: "3ddc97")
    static let amber = Color(hex: "ffb84d")
    static let red = Color(hex: "ff5d6c")

    static func level(_ l: String) -> Color {
        switch l {
        case "alto": return red
        case "moderado": return amber
        case "baixo": return green
        default: return muted
        }
    }
}
