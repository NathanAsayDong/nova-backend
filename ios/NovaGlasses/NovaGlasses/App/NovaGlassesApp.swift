import SwiftUI

@main
struct NovaGlassesApp: App {
    /// Unit tests run inside this app; don't open the mic or the socket then.
    private static let isRunningTests = ProcessInfo.processInfo.environment["XCTestConfigurationFilePath"] != nil

    var body: some Scene {
        WindowGroup {
            if Self.isRunningTests {
                Text("Running tests")
            } else {
                RootView()
            }
        }
    }
}

private struct RootView: View {
    @State private var model = AppModel()

    var body: some View {
        Group {
            if model.isLoggedIn {
                HomeView(model: model)
            } else {
                LoginView(model: model)
            }
        }
        .task { await model.bootstrap() }
    }
}
