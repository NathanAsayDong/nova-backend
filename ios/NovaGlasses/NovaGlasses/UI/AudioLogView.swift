import SwiftUI
import UIKit

/// What the audio stack did recently, newest first.
struct AudioLogView: View {
    private let log = AudioLog.shared

    var body: some View {
        List {
            if log.entries.isEmpty {
                Text("Nothing yet.").foregroundStyle(.secondary)
            }
            ForEach(log.entries.reversed()) { entry in
                VStack(alignment: .leading, spacing: 2) {
                    Text(entry.text)
                    Text(entry.time.formatted(date: .omitted, time: .standard))
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
            }
        }
        .navigationTitle("Audio log")
        .toolbar {
            Button("Copy") {
                UIPasteboard.general.string = log.export()
            }
            .disabled(log.entries.isEmpty)
        }
    }
}
