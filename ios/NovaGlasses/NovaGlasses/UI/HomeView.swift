import SwiftUI

struct HomeView: View {
    @Bindable var model: AppModel

    private var controller: ConversationController { model.controller }

    var body: some View {
        NavigationStack {
            List {
                Section {
                    HStack(spacing: 12) {
                        Circle()
                            .fill(phaseColor)
                            .frame(width: 14, height: 14)
                        VStack(alignment: .leading, spacing: 2) {
                            Text(controller.betweenLines ? "Working" : controller.phase.rawValue.capitalized)
                                .font(.headline)
                            Text(controller.statusMessage)
                                .font(.subheadline)
                                .foregroundStyle(.secondary)
                        }
                        Spacer()
                        if controller.userSpeaking {
                            Image(systemName: "waveform")
                                .foregroundStyle(.tint)
                        }
                    }
                    Toggle("Listening for \"Hey Nova\"", isOn: Binding(
                        get: { model.listeningEnabled },
                        set: { on in Task { await model.setListening(on) } }
                    ))
                    Toggle(isOn: Binding(
                        get: { model.sidekick.isOn },
                        set: { on in model.setSidekick(on) }
                    )) {
                        VStack(alignment: .leading, spacing: 2) {
                            Text("Sidekick")
                            Text(model.sidekick.isOn ? "Listening to everything · off after an hour" : "Nova listens in and chimes in on its own")
                                .font(.caption)
                                .foregroundStyle(.secondary)
                        }
                    }
                    .disabled(!model.listeningEnabled)
                    if model.sidekick.isOn {
                        LabeledContent("Overheard", value: model.sidekick.lastHeard.isEmpty ? "—" : model.sidekick.lastHeard)
                        if !model.sidekick.lastRemark.isEmpty {
                            LabeledContent("Sidekick said", value: model.sidekick.lastRemark)
                        }
                    }
                }

                Section("Connection") {
                    LabeledContent("Server", value: connectionText)
                    LabeledContent("Audio", value: model.routeSummary)
                    LabeledContent("Glasses camera", value: cameraText)
                    if model.camera.state == .unregistered {
                        Button("Connect glasses camera in Meta AI") { model.camera.register() }
                    }
                    NavigationLink("Audio log") { AudioLogView() }
                    if model.listeningEnabled && !model.wakeAvailable {
                        Text("Wake phrase unavailable on this device.")
                            .foregroundStyle(.orange)
                    }
                }

                if let error = model.errorMessage {
                    Section {
                        Text(error).foregroundStyle(.red)
                    }
                }

                Section("You said") {
                    Text(youSaid)
                        .foregroundStyle(youSaid == "—" ? .secondary : .primary)
                }

                Section("Nova said") {
                    Text(controller.lastReply.isEmpty ? "—" : controller.lastReply)
                        .foregroundStyle(controller.lastReply.isEmpty ? .secondary : .primary)
                }

                Section {
                    NavigationLink("People Nova knows") { FacesView(api: { model.api }, camera: model.camera) }
                } footer: {
                    Text("Only people who agreed to be recognized. Nova never stores faces of anyone else.")
                }

                Section {
                    Button("Log out", role: .destructive) {
                        Task { await model.logout() }
                    }
                }
            }
            .navigationTitle("Nova")
        }
    }

    private var youSaid: String {
        if !controller.partialTranscript.isEmpty { return controller.partialTranscript }
        return controller.lastTranscript.isEmpty ? "—" : controller.lastTranscript
    }

    private var cameraText: String {
        switch model.camera.state {
        case .unavailable: "Unavailable"
        case .unregistered: "Not connected"
        case .registering: "Connecting in Meta AI…"
        case .ready: "Ready"
        case .streaming: "On"
        }
    }

    private var connectionText: String {
        switch controller.connection {
        case .connected: "Connected"
        case .connecting: "Connecting…"
        case .disconnected: model.listeningEnabled ? "Reconnecting…" : "Disconnected"
        case .unauthorized: "Signed out"
        }
    }

    private var phaseColor: Color {
        if controller.betweenLines { return .orange }
        return switch controller.phase {
        case .off: .gray
        case .idle: .blue
        case .listening: .green
        case .thinking: .orange
        case .speaking: .purple
        }
    }
}
