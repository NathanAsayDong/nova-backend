import Foundation
import ImageIO
import UIKit

/// Sizes a photo for the trip to the server: Claude reads about 1.2k tokens
/// from a 720×1280 frame, and nothing is gained by sending more pixels.
enum ImagePrep {
    static let maxEdge = 1280
    static let quality = 0.8

    /// The JPEG unchanged if it already fits, else scaled (EXIF orientation
    /// applied) and re-encoded. Nil if the data is not an image.
    static func scaled(_ data: Data, maxEdge: Int = maxEdge, quality: Double = quality) -> Data? {
        guard let source = CGImageSourceCreateWithData(data as CFData, nil),
              let properties = CGImageSourceCopyPropertiesAtIndex(source, 0, nil) as? [CFString: Any],
              let width = properties[kCGImagePropertyPixelWidth] as? Int,
              let height = properties[kCGImagePropertyPixelHeight] as? Int else { return nil }
        if max(width, height) <= maxEdge {
            return data
        }
        let options: [CFString: Any] = [
            kCGImageSourceCreateThumbnailFromImageAlways: true,
            kCGImageSourceCreateThumbnailWithTransform: true,
            kCGImageSourceThumbnailMaxPixelSize: maxEdge,
        ]
        guard let thumbnail = CGImageSourceCreateThumbnailAtIndex(source, 0, options as CFDictionary) else { return nil }
        return UIImage(cgImage: thumbnail).jpegData(compressionQuality: quality)
    }
}
