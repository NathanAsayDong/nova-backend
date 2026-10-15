import Foundation

/// Spots a request to look ("what do you see", "who's this") in a live
/// caption, so the glasses can take the photo while the user is still talking
/// instead of after Nova has heard the whole question. A miss costs nothing:
/// Nova can still call its `look` tool once it has the transcript.
enum VisionIntent {
    /// Matched as whole words in the normalized caption.
    static let phrases: [String] = [
        "what do you see", "what can you see", "can you see", "do you see",
        "what am i looking at", "who am i looking at", "what are we looking at",
        "what is this", "what is that", "whats this", "whats that",
        "who is this", "who is that", "whos this", "whos that",
        "look at this", "look at that", "look at him", "look at her", "look at them",
        "take a look", "have a look",
        "read this", "read that", "what does this say", "what does that say",
        "describe what", "what is in front of me", "whats in front of me",
        "do you recognize", "do you know who",
    ]

    static func wantsToSee(_ caption: String) -> Bool {
        let text = " " + normalize(caption) + " "
        return phrases.contains { text.contains(" \($0) ") }
    }

    /// Lowercase words separated by single spaces; apostrophes dropped so
    /// "what's" and "whats" are the same word, other punctuation as spaces.
    static func normalize(_ caption: String) -> String {
        let lowered = caption.lowercased().replacingOccurrences(of: "’", with: "'")
        var out = ""
        for character in lowered {
            if character == "'" { continue }
            out.append(character.isLetter || character.isNumber ? character : " ")
        }
        return out.split(separator: " ").joined(separator: " ")
    }
}
