import Charts
import SwiftUI

/// Onda de pulso ao vivo (estilo ECG) desenhada com Canvas nativo.
struct WaveformView: View {
    let samples: [Double]

    var body: some View {
        Canvas { ctx, size in
            guard samples.count > 2 else { return }
            let lo = samples.min() ?? 0
            let hi = samples.max() ?? 1
            let rng = (hi - lo) == 0 ? 1 : (hi - lo)
            let dx = size.width / CGFloat(samples.count - 1)
            var path = Path()
            for (i, v) in samples.enumerated() {
                let x = CGFloat(i) * dx
                let y = size.height - CGFloat((v - lo) / rng) * (size.height - 8) - 4
                if i == 0 { path.move(to: CGPoint(x: x, y: y)) }
                else { path.addLine(to: CGPoint(x: x, y: y)) }
            }
            ctx.stroke(path, with: .color(Palette.green), lineWidth: 2)
            // ponto final destacado
            if let last = samples.last {
                let x = size.width
                let y = size.height - CGFloat((last - lo) / rng) * (size.height - 8) - 4
                ctx.fill(Path(ellipseIn: CGRect(x: x - 4, y: y - 4, width: 8, height: 8)),
                         with: .color(Palette.green))
            }
        }
    }
}

/// Tela de permissão de câmera negada com atalho para os Ajustes do Sistema.
struct PermissionDeniedView: View {
    @EnvironmentObject var m: AppModel
    var body: some View {
        VStack(spacing: 14) {
            Image(systemName: "video.slash.fill").font(.system(size: 40)).foregroundColor(Palette.amber)
            Text("Acesso à câmera negado").font(.system(size: 16, weight: .bold))
            Text("O Visão Clínica precisa da câmera para a triagem. Autorize em Ajustes do Sistema › Privacidade e Segurança › Câmera.")
                .font(.system(size: 12)).foregroundColor(Palette.muted)
                .multilineTextAlignment(.center).frame(maxWidth: 320)
            Button {
                m.openSystemCameraSettings()
            } label: {
                Label("Abrir Ajustes do Sistema", systemImage: "gearshape")
            }.buttonStyle(.borderedProminent)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .background(Color.black)
        .clipShape(RoundedRectangle(cornerRadius: 16))
    }
}

/// Histórico & tendências das sessões (Swift Charts).
struct HistoryView: View {
    @EnvironmentObject var m: AppModel
    @Environment(\.dismiss) private var dismiss

    private struct Point: Identifiable { let id: Int; let wellness: Int; let hr: Double; let date: String }

    var body: some View {
        let rows = m.recentSessions()
        let points = rows.reversed().enumerated().map {
            Point(id: $0.offset, wellness: $0.element.wellness, hr: $0.element.heartRate, date: $0.element.createdAt)
        }
        VStack(alignment: .leading, spacing: 14) {
            HStack {
                Label("Histórico & Tendências", systemImage: "clock.arrow.circlepath")
                    .font(.system(size: 16, weight: .bold))
                Spacer()
                Button { dismiss() } label: { Image(systemName: "xmark.circle.fill") }
                    .buttonStyle(.plain).foregroundColor(Palette.muted)
            }

            if points.isEmpty {
                Text("Nenhuma sessão salva ainda. Faça uma análise para começar a acompanhar suas tendências.")
                    .foregroundColor(Palette.muted).frame(maxWidth: .infinity, maxHeight: .infinity)
            } else {
                let avgW = points.map { Double($0.wellness) }.reduce(0, +) / Double(points.count)
                let avgHR = points.map { $0.hr }.filter { $0 > 0 }
                Text("\(points.count) sessões · bem-estar médio \(Int(avgW))/100"
                     + (avgHR.isEmpty ? "" : " · FC média \(Int(avgHR.reduce(0, +) / Double(avgHR.count))) bpm"))
                    .font(.system(size: 12)).foregroundColor(Palette.muted)

                Text("BEM-ESTAR (0–100)").font(.system(size: 10, weight: .bold)).foregroundColor(Palette.muted)
                Chart(points) { p in
                    LineMark(x: .value("Sessão", p.id), y: .value("Bem-estar", p.wellness))
                        .foregroundStyle(Palette.green).interpolationMethod(.catmullRom)
                    PointMark(x: .value("Sessão", p.id), y: .value("Bem-estar", p.wellness))
                        .foregroundStyle(Palette.green)
                }
                .chartYScale(domain: 0...100).frame(height: 150)

                Text("FREQUÊNCIA CARDÍACA (bpm)").font(.system(size: 10, weight: .bold)).foregroundColor(Palette.muted)
                Chart(points.filter { $0.hr > 0 }) { p in
                    LineMark(x: .value("Sessão", p.id), y: .value("FC", p.hr))
                        .foregroundStyle(Palette.accent).interpolationMethod(.catmullRom)
                }
                .frame(height: 130)
            }
        }
        .padding(20)
        .frame(width: 640, height: 560)
        .background(Palette.bg)
    }
}
