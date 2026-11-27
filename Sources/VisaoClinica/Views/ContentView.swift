import SwiftUI

struct ContentView: View {
    @EnvironmentObject var m: AppModel
    var body: some View {
        Group {
            if m.isAuthenticated { MainView() } else { LoginView() }
        }
        .frame(minWidth: 1000, minHeight: 640)
        .background(Palette.bg)
        .preferredColorScheme(.dark)
    }
}

// MARK: - Login / controle de acesso

struct LoginView: View {
    @EnvironmentObject var m: AppModel
    @State private var user = ""
    @State private var pw = ""

    var body: some View {
        VStack(spacing: 16) {
            Spacer()
            Image(systemName: "waveform.path.ecg.rectangle.fill")
                .font(.system(size: 48)).foregroundColor(Palette.accent)
            Text("Visão Clínica").font(.system(size: 30, weight: .bold))
            Text("Sign in to continue")
                .foregroundColor(Palette.muted)
            VStack(spacing: 10) {
                TextField("Username", text: $user).textFieldStyle(.roundedBorder)
                SecureField("Password", text: $pw).textFieldStyle(.roundedBorder)
            }.frame(width: 320)
            if !m.loginError.isEmpty {
                Text(m.loginError).foregroundColor(Palette.red).font(.system(size: 12))
            }
            Button("Sign in") {
                m.login(user: user, password: pw)
            }
            .keyboardShortcut(.defaultAction)
            .buttonStyle(.borderedProminent)
            Spacer()
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .background(Palette.bg)
    }
}

// MARK: - Tela principal

struct MainView: View {
    @EnvironmentObject var m: AppModel
    var body: some View {
        VStack(spacing: 14) {
            HStack {
                Image(systemName: "waveform.path.ecg.rectangle")
                    .font(.system(size: 26)).foregroundColor(Palette.accent)
                VStack(alignment: .leading, spacing: 2) {
                    Text("Visão Clínica").font(.system(size: 22, weight: .bold))
                    Text("Computer-vision screening — 100% local · native macOS")
                        .font(.system(size: 12)).foregroundColor(Palette.muted)
                }
                Spacer()
                Button { m.showHistory = true } label: {
                    Label("History", systemImage: "clock.arrow.circlepath")
                }.buttonStyle(.bordered)
                Label("\(m.currentUser) · \(Clinical.display(m.role))", systemImage: "person.crop.circle")
                    .font(.system(size: 12)).foregroundColor(Palette.muted)
            }

            HStack(alignment: .top, spacing: 16) {
                cameraColumn
                panelColumn.frame(width: 420)
            }

            Text("⚠️ Screening and research-support tool — not a medical diagnosis.")
                .font(.system(size: 11)).italic().foregroundColor(Palette.red)
        }
        .padding(18)
        .background(Palette.bg)
        .sheet(isPresented: $m.showHistory) { HistoryView().environmentObject(m) }
    }

    private var cameraColumn: some View {
        VStack(spacing: 10) {
            ZStack(alignment: .top) {
                if m.cameraDenied {
                    PermissionDeniedView().frame(minHeight: 420)
                } else {
                    CameraPreview(session: m.camera.session)
                        .clipShape(RoundedRectangle(cornerRadius: 16))
                        .overlay(RoundedRectangle(cornerRadius: 16).stroke(Palette.border))
                        .overlay(alignment: .bottom) {
                            WaveformView(samples: m.waveform)
                                .frame(height: 56)
                                .padding(10)
                                .background(Color.black.opacity(0.35))
                                .clipShape(RoundedRectangle(cornerRadius: 10))
                                .padding(10)
                        }
                    HStack(spacing: 8) {
                        Image(systemName: m.guidanceOK ? "checkmark.circle.fill" : "exclamationmark.triangle.fill")
                            .foregroundColor(m.guidanceOK ? Palette.green : Palette.amber)
                        Text(m.guidanceText).font(.system(size: 13, weight: .semibold))
                            .foregroundColor(m.guidanceOK ? Palette.green : Palette.amber)
                        Spacer()
                    }
                    .padding(10)
                    .background(Color.black.opacity(0.55))
                    .clipShape(RoundedRectangle(cornerRadius: 10))
                    .padding(10)
                }
            }
            .frame(minHeight: 420)

            ProgressView(value: m.progress).tint(Palette.accent)
            HStack {
                Button { m.analyze() } label: {
                    Label(m.isAnalyzing ? "Analyzing…" : "Analyze (12s)",
                          systemImage: "waveform.path.ecg")
                }
                .disabled(m.isAnalyzing || m.cameraDenied)
                .buttonStyle(.borderedProminent)
                .keyboardShortcut(.return, modifiers: .command)
                Text(m.statusText).font(.system(size: 12)).foregroundColor(Palette.muted)
                Spacer()
            }
        }
    }

    private var panelColumn: some View {
        VStack(alignment: .leading, spacing: 10) {
            Text("CLINICAL SCREENING INDICATORS")
                .font(.system(size: 10, weight: .bold)).foregroundColor(Palette.muted)
            Text("Overall level: \(Clinical.display(m.risk).uppercased())")
                .font(.system(size: 14, weight: .bold))
                .foregroundColor(Palette.level(m.risk))

            if let f = m.features { VitalsGrid(features: f, wellness: m.wellness) }

            ScrollView {
                VStack(spacing: 8) {
                    if m.hasResult {
                        ForEach(m.conditions) { ConditionCard(cond: $0) }
                    } else {
                        Text("Click Analyze to start the screening.")
                            .foregroundColor(Palette.muted).font(.system(size: 13))
                            .frame(maxWidth: .infinity, alignment: .leading).padding(.top, 8)
                    }
                }
            }
        }
        .frame(maxHeight: .infinity, alignment: .top)
    }
}

// MARK: - Componentes

struct VitalsGrid: View {
    let features: BiomarkerFeatures
    let wellness: Wellness?
    private let cols = [GridItem(.flexible()), GridItem(.flexible())]

    var body: some View {
        LazyVGrid(columns: cols, spacing: 8) {
            if let w = wellness, w.reliable {
                chip("WELLNESS", "\(w.score) · \(Clinical.display(w.label))",
                     w.score >= 65 ? Palette.green : w.score >= 45 ? Palette.amber : Palette.red)
                chip("STRESS", "\(w.stress)%", w.stress >= 60 ? Palette.red : Palette.muted)
            } else {
                chip("WELLNESS", "— weak signal", Palette.muted)
            }
            if features.heartRateBpm > 0 {
                chip("HEART RATE", String(format: "%.0f bpm", features.heartRateBpm), Palette.text)
            }
            if features.respirationBpm > 0 {
                chip("RESPIRATION", String(format: "%.0f rpm", features.respirationBpm), Palette.text)
            }
            if features.hrvSdnnMs > 0 {
                chip("HRV (SDNN)", String(format: "%.0f ms", features.hrvSdnnMs), Palette.text)
            }
            if features.lfHfRatio > 0 {
                chip("LF/HF BALANCE", String(format: "%.2f", features.lfHfRatio), Palette.text)
            }
        }
    }

    private func chip(_ label: String, _ value: String, _ color: Color) -> some View {
        VStack(alignment: .leading, spacing: 2) {
            Text(value).font(.system(size: 17, weight: .heavy)).foregroundColor(color)
            Text(label).font(.system(size: 10, weight: .bold)).foregroundColor(Palette.muted)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(10)
        .background(Palette.panel2)
        .overlay(RoundedRectangle(cornerRadius: 12).stroke(Palette.border))
        .clipShape(RoundedRectangle(cornerRadius: 12))
    }
}

struct ConditionCard: View {
    let cond: ConditionResult
    var body: some View {
        let color = Palette.level(cond.level)
        VStack(alignment: .leading, spacing: 8) {
            HStack {
                Circle().fill(color).frame(width: 9, height: 9)
                Text(cond.name).font(.system(size: 13, weight: .bold))
                Spacer()
                Text(Clinical.display(cond.level).uppercased())
                    .font(.system(size: 10, weight: .heavy)).foregroundColor(color)
                    .padding(.horizontal, 10).padding(.vertical, 2)
                    .overlay(RoundedRectangle(cornerRadius: 9).stroke(color))
            }
            GeometryReader { geo in
                ZStack(alignment: .leading) {
                    RoundedRectangle(cornerRadius: 4).fill(Palette.panel2).frame(height: 7)
                    RoundedRectangle(cornerRadius: 4).fill(color)
                        .frame(width: geo.size.width * max(0.02, cond.score), height: 7)
                }
            }.frame(height: 7)
            Text(cond.rationale).font(.system(size: 11)).foregroundColor(Palette.muted)
        }
        .padding(14)
        .background(Palette.panel)
        .overlay(RoundedRectangle(cornerRadius: 14).stroke(Palette.border))
        .clipShape(RoundedRectangle(cornerRadius: 14))
    }
}
