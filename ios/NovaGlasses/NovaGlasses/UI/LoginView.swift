import SwiftUI

struct LoginView: View {
    @Bindable var model: AppModel
    @State private var username = ""
    @State private var password = ""
    @State private var busy = false

    var body: some View {
        NavigationStack {
            Form {
                Section {
                    TextField("Username", text: $username)
                        .textContentType(.username)
                        .textInputAutocapitalization(.never)
                        .autocorrectionDisabled()
                    SecureField("Password", text: $password)
                        .textContentType(.password)
                }
                Section {
                    TextField("Server", text: $model.serverURLString)
                        .keyboardType(.URL)
                        .textInputAutocapitalization(.never)
                        .autocorrectionDisabled()
                } footer: {
                    Text("https://api.nova-api.us, or http://<mac-ip>:8000 for a local backend.")
                }
                if let error = model.errorMessage {
                    Section {
                        Text(error).foregroundStyle(.red)
                    }
                }
                Section {
                    Button {
                        busy = true
                        Task {
                            await model.login(username: username, password: password)
                            password = ""
                            busy = false
                        }
                    } label: {
                        if busy { ProgressView() } else { Text("Log in") }
                    }
                    .disabled(busy || username.isEmpty || password.isEmpty)
                }
            }
            .navigationTitle("Nova")
        }
    }
}
