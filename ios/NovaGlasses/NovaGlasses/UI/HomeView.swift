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
                            Text(controller.phase.rawValue.capitalized)
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
                }

                Section("Connection") {
                    LabeledContent("Server", value: connectionText)
                    LabeledContent("Audio", value: model.routeSummary)
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

    private var connectionText: String {
        switch controller.connection {
        case .connected: "Connected"
        case .connecting: "Connecting…"
        case .disconnected: model.listeningEnabled ? "Reconnecting…" : "Disconnected"
        case .unauthorized: "Signed out"
        }
    }

    private var phaseColor: Color {
        switch controller.phase {
        case .off: .gray
        case .idle: .blue
        case .listening: .green
        case .thinking: .orange
        case .speaking: .purple
        }
    }
}
