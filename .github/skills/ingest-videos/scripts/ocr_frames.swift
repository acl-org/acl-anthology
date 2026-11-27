import Foundation
import Vision
import Darwin

struct OCRText: Codable {
    let text: String
    let confidence: Float
}

struct OCRFrame: Codable {
    let path: String
    let observations: [OCRText]
    let error: String?
}

var failed = false
let encoder = JSONEncoder()
while let path = readLine() {
    if path.isEmpty { continue }
    let result: OCRFrame
    do {
        let observations = try autoreleasepool { () throws -> [OCRText] in
            let request = VNRecognizeTextRequest()
            request.recognitionLevel = .accurate
            request.usesLanguageCorrection = false
            request.recognitionLanguages = ["en-US"]
            request.minimumTextHeight = 0.006
            let handler = VNImageRequestHandler(url: URL(fileURLWithPath: path), options: [:])
            try handler.perform([request])
            return (request.results ?? []).compactMap { observation in
                guard let candidate = observation.topCandidates(1).first else { return nil }
                return OCRText(text: candidate.string, confidence: candidate.confidence)
            }
        }
        result = OCRFrame(path: path, observations: observations, error: nil)
    } catch {
        failed = true
        FileHandle.standardError.write(Data("\(path): \(error)\n".utf8))
        result = OCRFrame(path: path, observations: [], error: String(describing: error))
    }
    do {
        FileHandle.standardOutput.write(try encoder.encode(result))
        FileHandle.standardOutput.write(Data("\n".utf8))
    } catch {
        FileHandle.standardError.write(Data("Cannot encode OCR result: \(error)\n".utf8))
        exit(2)
    }
}
exit(failed ? 1 : 0)
