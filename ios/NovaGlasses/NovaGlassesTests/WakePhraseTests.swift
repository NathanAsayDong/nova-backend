import XCTest
@testable import NovaGlasses

final class WakePhraseTests: XCTestCase {
    func testOpensWithWakePhrase() {
        for phrase in ["Nova", "Hey Nova", "hey nova what's the weather", "OK, Nova.", "Hi Noah, call mom",
                       "Hey no va set a timer", "Alright nova"] {
            XCTAssertTrue(WakePhrase.startsWithWakePhrase(phrase), phrase)
        }
    }

    func testMentionsAreNotWakes() {
        for phrase in ["I asked Nova yesterday", "the supernova", "hey there nova", "", "  ", "Hey"] {
            XCTAssertFalse(WakePhrase.startsWithWakePhrase(phrase), phrase)
        }
    }

    func testContainsAcceptsShortPhrases() {
        XCTAssertTrue(WakePhrase.containsWakePhrase("thanks nova"))
        XCTAssertTrue(WakePhrase.containsWakePhrase("hey nova"))
        XCTAssertFalse(WakePhrase.containsWakePhrase("I told my friend about nova"))
    }

    func testNormalization() {
        XCTAssertEqual(WakePhrase.normalize("  Hey,   NOVA!! "), "hey nova")
        XCTAssertEqual(WakePhrase.canonicalTokens("no vah please"), ["nova", "please"])
    }
}
