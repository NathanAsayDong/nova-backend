import Foundation

/// Wake phrase matching for the on-device recognizer. A port of the web
/// client's wakePhrase.ts; the backend has the same rules
/// (nova_controller.split_wake_phrase) for the Whisper side.
enum WakePhrase {
    // How recognizers mishear "Nova": "Noah" above all. Mirrors the backend.
    private static let nameVariants: Set<String> = ["nova", "novah", "nover", "noah", "noba", "novaa"]
    private static let prefixes: Set<String> = ["hey", "hi", "hello", "ok", "okay", "yo", "alright"]

    static func normalize(_ value: String) -> String {
        let lowered = value.lowercased()
        var scalars = String.UnicodeScalarView()
        for scalar in lowered.unicodeScalars {
            let isAlnum = ("a"..."z").contains(scalar) || ("0"..."9").contains(scalar)
            scalars.append(isAlnum || scalar == " " ? scalar : " ")
        }
        return String(scalars)
            .split(separator: " ", omittingEmptySubsequences: true)
            .joined(separator: " ")
    }

    static func canonicalTokens(_ value: String) -> [String] {
        let normalized = normalize(value)
        guard !normalized.isEmpty else { return [] }
        var tokens = normalized.split(separator: " ").map(String.init)
        // "no va" / "no vah" / "no ver" → "nova"
        var merged: [String] = []
        var i = 0
        while i < tokens.count {
            if tokens[i] == "no", i + 1 < tokens.count, ["va", "vah", "ver"].contains(tokens[i + 1]) {
                merged.append("nova")
                i += 2
            } else {
                merged.append(tokens[i])
                i += 1
            }
        }
        tokens = merged.map { nameVariants.contains($0) ? "nova" : $0 }
        return tokens
    }

    /// Whether `value` OPENS with the wake phrase: "Nova, …", "Hey Nova …".
    /// "I asked Nova yesterday" must not wake it.
    static func startsWithWakePhrase(_ value: String) -> Bool {
        let tokens = canonicalTokens(value)
        if tokens.first == "nova" { return true }
        return tokens.count >= 2 && prefixes.contains(tokens[0]) && tokens[1] == "nova"
    }

    /// Looser check: also accepts "nova" anywhere in a short phrase.
    static func containsWakePhrase(_ value: String) -> Bool {
        let tokens = canonicalTokens(value)
        guard !tokens.isEmpty else { return false }
        if startsWithWakePhrase(value) { return true }
        return tokens.count <= 3 && tokens.contains("nova")
    }
}
