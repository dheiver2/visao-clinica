import CommonCrypto
import Foundation
import Security

/// Hash de senha (PBKDF2-HMAC-SHA256) e utilidades de segurança — nativo,
/// via CommonCrypto/Security. Substitui o hashlib do Python.
enum Crypto {

    static let iterations = 200_000
    static let keyLength = 32

    static func pbkdf2(password: String, salt: Data) -> Data {
        var derived = Data(count: keyLength)
        let pw = Array(password.utf8)
        let saltBytes = [UInt8](salt)
        let ok = derived.withUnsafeMutableBytes { (out: UnsafeMutableRawBufferPointer) -> Int32 in
            saltBytes.withUnsafeBufferPointer { sb in
                CCKeyDerivationPBKDF(
                    CCPBKDFAlgorithm(kCCPBKDF2),
                    pw, pw.count,
                    sb.baseAddress, sb.count,
                    CCPseudoRandomAlgorithm(kCCPRFHmacAlgSHA256),
                    UInt32(iterations),
                    out.bindMemory(to: UInt8.self).baseAddress, keyLength)
            }
        }
        return ok == kCCSuccess ? derived : Data()
    }

    static func randomSalt(_ count: Int = 16) -> Data {
        var d = Data(count: count)
        _ = d.withUnsafeMutableBytes { ptr in
            SecRandomCopyBytes(kSecRandomDefault, count, ptr.baseAddress!)
        }
        return d
    }

    static func hex(_ d: Data) -> String { d.map { String(format: "%02x", $0) }.joined() }

    static func data(fromHex hex: String) -> Data {
        var d = Data(); var i = hex.startIndex
        while i < hex.endIndex {
            let j = hex.index(i, offsetBy: 2, limitedBy: hex.endIndex) ?? hex.endIndex
            if let b = UInt8(hex[i..<j], radix: 16) { d.append(b) }
            i = j
        }
        return d
    }
}

/// Política mínima de senha. Retorna mensagem de erro ou nil se válida.
func validatePassword(_ pwd: String) -> String? {
    if pwd.count < 8 { return "A senha deve ter ao menos 8 caracteres." }
    let hasLetter = pwd.contains { $0.isLetter }
    let hasDigit = pwd.contains { $0.isNumber }
    if !hasLetter || !hasDigit { return "A senha deve conter letras e números." }
    return nil
}

let ROLES = ["administrador", "profissional", "pesquisador"]
