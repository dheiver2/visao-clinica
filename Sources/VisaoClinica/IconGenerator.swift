import CoreGraphics
import Foundation
import ImageIO

/// Desenha o ícone do app com CoreGraphics (nativo) e o salva como PNG 1024².
/// Usado pelo build script para gerar o `.icns`.  Uso:  VisaoClinica --make-icon <arquivo.png>
enum IconGenerator {

    static func write(to path: String) -> Never {
        let s = 1024
        let cs = CGColorSpaceCreateDeviceRGB()
        guard let ctx = CGContext(data: nil, width: s, height: s, bitsPerComponent: 8,
                                  bytesPerRow: 0, space: cs,
                                  bitmapInfo: CGImageAlphaInfo.premultipliedLast.rawValue) else {
            FileHandle.standardError.write(Data("Falha ao criar contexto do ícone\n".utf8)); exit(1)
        }

        func color(_ hex: UInt32) -> CGColor {
            CGColor(red: CGFloat((hex >> 16) & 0xff) / 255, green: CGFloat((hex >> 8) & 0xff) / 255,
                    blue: CGFloat(hex & 0xff) / 255, alpha: 1)
        }

        // fundo arredondado com gradiente escuro
        let inset: CGFloat = 60
        let rect = CGRect(x: inset, y: inset, width: CGFloat(s) - 2 * inset, height: CGFloat(s) - 2 * inset)
        let round = CGPath(roundedRect: rect, cornerWidth: 210, cornerHeight: 210, transform: nil)
        ctx.addPath(round); ctx.clip()
        let grad = CGGradient(colorsSpace: cs,
                              colors: [color(0x121722), color(0x05070b)] as CFArray,
                              locations: [0, 1])!
        ctx.drawLinearGradient(grad, start: CGPoint(x: 0, y: CGFloat(s)),
                               end: CGPoint(x: CGFloat(s), y: 0), options: [])

        // brilho radial sutil atrás da onda
        let glow = CGGradient(colorsSpace: cs,
                              colors: [color(0x1b3b7a), color(0x05070b)] as CFArray,
                              locations: [0, 1])!
        ctx.drawRadialGradient(glow, startCenter: CGPoint(x: CGFloat(s) / 2, y: CGFloat(s) / 2),
                               startRadius: 0, endCenter: CGPoint(x: CGFloat(s) / 2, y: CGFloat(s) / 2),
                               endRadius: CGFloat(s) / 2, options: [])

        // onda de ECG/pulso (azul → verde)
        let midY = CGFloat(s) / 2
        let pts: [(CGFloat, CGFloat)] = [
            (150, midY), (330, midY), (400, midY + 40), (450, midY - 210),
            (520, midY + 260), (580, midY - 60), (640, midY), (874, midY),
        ]
        let wave = CGMutablePath()
        wave.move(to: CGPoint(x: pts[0].0, y: pts[0].1))
        for p in pts.dropFirst() { wave.addLine(to: CGPoint(x: p.0, y: p.1)) }
        ctx.setLineCap(.round); ctx.setLineJoin(.round); ctx.setLineWidth(34)
        ctx.setStrokeColor(color(0x4c8dff)); ctx.addPath(wave); ctx.strokePath()
        // realce verde do pico
        ctx.setLineWidth(14); ctx.setStrokeColor(color(0x3ecf8e))
        ctx.addPath(wave); ctx.strokePath()

        guard let img = ctx.makeImage() else {
            FileHandle.standardError.write(Data("Falha ao gerar imagem\n".utf8)); exit(1)
        }
        let url = URL(fileURLWithPath: path)
        guard let dest = CGImageDestinationCreateWithURL(url as CFURL, "public.png" as CFString, 1, nil) else {
            FileHandle.standardError.write(Data("Falha ao criar PNG\n".utf8)); exit(1)
        }
        CGImageDestinationAddImage(dest, img, nil)
        CGImageDestinationFinalize(dest)
        print("Ícone salvo em \(path)")
        exit(0)
    }
}
