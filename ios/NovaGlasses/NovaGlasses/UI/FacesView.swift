import PhotosUI
import SwiftUI

/// The people Nova recognizes. Everyone here agreed to it; deleting someone
/// removes every face sample the server holds for them.
struct FacesView: View {
    let api: () -> APIClient
    let camera: DATGlassesCamera

    @State private var people: [APIClient.Person] = []
    @State private var error: String?
    @State private var adding = false

    var body: some View {
        List {
            if let error {
                Text(error).foregroundStyle(.red)
            }
            if people.isEmpty && error == nil {
                Text("No one yet. Add someone who has agreed to be recognized.")
                    .foregroundStyle(.secondary)
            }
            ForEach(people) { person in
                LabeledContent(person.name, value: "\(person.samples) photo\(person.samples == 1 ? "" : "s")")
            }
            .onDelete { offsets in
                let doomed = offsets.map { people[$0] }
                Task { await delete(doomed) }
            }
        }
        .navigationTitle("People Nova knows")
        .toolbar {
            Button { adding = true } label: { Image(systemName: "plus") }
        }
        .sheet(isPresented: $adding, onDismiss: { Task { await load() } }) {
            AddPersonView(api: api, camera: camera)
        }
        .task { await load() }
        .refreshable { await load() }
    }

    private func load() async {
        do {
            people = try await api().people()
            error = nil
        } catch {
            self.error = error.localizedDescription
        }
    }

    private func delete(_ doomed: [APIClient.Person]) async {
        for person in doomed {
            do {
                try await api().deletePerson(id: person.id)
            } catch {
                self.error = error.localizedDescription
            }
        }
        await load()
    }
}

/// Enroll one person: their name, their consent, then a few photos of their
/// face from the glasses or the photo library.
struct AddPersonView: View {
    static let suggestedSamples = 3

    let api: () -> APIClient
    let camera: DATGlassesCamera

    @Environment(\.dismiss) private var dismiss
    @State private var name = ""
    @State private var consented = false
    @State private var person: APIClient.Person?
    @State private var samples = 0
    @State private var busy = false
    @State private var message: String?
    @State private var picked: [PhotosPickerItem] = []

    var body: some View {
        NavigationStack {
            Form {
                Section {
                    TextField("Name", text: $name)
                        .textInputAutocapitalization(.words)
                        .disabled(person != nil)
                    Toggle("\(name.isEmpty ? "They" : name) agreed to be recognized by Nova", isOn: $consented)
                        .disabled(person != nil)
                } footer: {
                    Text("Ask first. Nova will say their name when it sees them through your glasses.")
                }

                if person == nil {
                    Section {
                        Button("Continue") { Task { await create() } }
                            .disabled(busy || !consented || name.trimmingCharacters(in: .whitespaces).isEmpty)
                    }
                } else {
                    Section {
                        Button("Take a photo with the glasses") { Task { await captureFromGlasses() } }
                            .disabled(busy || !camera.state.canCapture)
                        PhotosPicker("Choose photos", selection: $picked, maxSelectionCount: 5, matching: .images)
                            .disabled(busy)
                    } header: {
                        Text("Photos of their face: \(samples) of \(Self.suggestedSamples)")
                    } footer: {
                        Text("One face per photo, clearly visible. A few angles help.")
                    }
                }

                if let message {
                    Section { Text(message) }
                }
            }
            .navigationTitle("Add someone")
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button(person == nil ? "Cancel" : "Done") { dismiss() }
                }
                if busy {
                    ToolbarItem(placement: .principal) { ProgressView() }
                }
            }
            .onChange(of: picked) { _, items in
                guard !items.isEmpty else { return }
                Task { await uploadPicked(items) }
            }
        }
    }

    private func create() async {
        busy = true
        defer { busy = false }
        do {
            person = try await api().addPerson(name: name.trimmingCharacters(in: .whitespaces), consent: consented)
            message = nil
        } catch {
            message = error.localizedDescription
        }
    }

    private func captureFromGlasses() async {
        busy = true
        defer { busy = false }
        do {
            await addSample(try await camera.capturePhoto())
        } catch {
            message = error.localizedDescription
        }
    }

    private func uploadPicked(_ items: [PhotosPickerItem]) async {
        busy = true
        defer {
            busy = false
            picked = []
        }
        for item in items {
            guard let data = try? await item.loadTransferable(type: Data.self),
                  let jpeg = ImagePrep.scaled(data) else {
                message = "Couldn't read one of the photos."
                continue
            }
            await addSample(jpeg)
        }
    }

    private func addSample(_ jpeg: Data) async {
        guard let person else { return }
        do {
            samples = try await api().addFaceSample(personId: person.id, jpeg: jpeg)
            message = samples >= Self.suggestedSamples ? "Nova will recognize \(person.name) now." : nil
        } catch {
            message = error.localizedDescription
        }
    }
}
