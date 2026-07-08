import Foundation
import SQLite3

/// Persistência local (SQLite nativo, offline) — sessões, controle de acesso,
/// auditoria (LGPD) e dados institucionais. Substitui o sqlite3 do Python.
final class AppDatabase {

    struct SessionRow {
        var id: Int
        var createdAt: String
        var mode: String
        var risk: String
        var wellness: Int
        var heartRate: Double
    }

    struct AuditRow { var ts: String; var user: String; var event: String; var detail: String }

    private var db: OpaquePointer?
    private let SQLITE_TRANSIENT = unsafeBitCast(-1, to: sqlite3_destructor_type.self)

    convenience init() {
        let dir = Self.dataDir()
        try? FileManager.default.createDirectory(at: dir, withIntermediateDirectories: true)
        self.init(path: dir.appendingPathComponent("visaoclinica.db").path)
    }

    /// Inicializador com caminho explícito (usado por testes com banco isolado).
    init(path: String) {
        sqlite3_open(path, &db)
        exec("""
        CREATE TABLE IF NOT EXISTS sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT DEFAULT (datetime('now','localtime')),
            mode TEXT, risk TEXT, wellness INTEGER, heart_rate REAL, features_json TEXT);
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT, username TEXT UNIQUE NOT NULL,
            salt TEXT NOT NULL, pwd_hash TEXT NOT NULL, role TEXT NOT NULL,
            active INTEGER NOT NULL DEFAULT 1,
            created_at TEXT DEFAULT (datetime('now','localtime')));
        CREATE TABLE IF NOT EXISTS audit_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts TEXT DEFAULT (datetime('now','localtime')),
            username TEXT, event TEXT NOT NULL, detail TEXT);
        CREATE TABLE IF NOT EXISTS institution (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            nome TEXT, cnpj TEXT, responsavel TEXT, conselho TEXT);
        """)
    }

    static func dataDir() -> URL {
        let base = FileManager.default.urls(for: .applicationSupportDirectory, in: .userDomainMask)[0]
        return base.appendingPathComponent("VisaoClinica")
    }

    private func exec(_ sql: String) { sqlite3_exec(db, sql, nil, nil, nil) }

    // MARK: - Sessões

    func saveSession(mode: String, risk: String, wellness: Int, heartRate: Double, featuresJSON: String) {
        var st: OpaquePointer?
        let sql = "INSERT INTO sessions (mode, risk, wellness, heart_rate, features_json) VALUES (?,?,?,?,?)"
        if sqlite3_prepare_v2(db, sql, -1, &st, nil) == SQLITE_OK {
            sqlite3_bind_text(st, 1, mode, -1, SQLITE_TRANSIENT)
            sqlite3_bind_text(st, 2, risk, -1, SQLITE_TRANSIENT)
            sqlite3_bind_int(st, 3, Int32(wellness))
            sqlite3_bind_double(st, 4, heartRate)
            sqlite3_bind_text(st, 5, featuresJSON, -1, SQLITE_TRANSIENT)
            sqlite3_step(st)
        }
        sqlite3_finalize(st)
    }

    func recentSessions(limit: Int = 50) -> [SessionRow] {
        var rows: [SessionRow] = []
        var st: OpaquePointer?
        let sql = "SELECT id, created_at, mode, risk, wellness, heart_rate FROM sessions ORDER BY id DESC LIMIT ?"
        if sqlite3_prepare_v2(db, sql, -1, &st, nil) == SQLITE_OK {
            sqlite3_bind_int(st, 1, Int32(limit))
            while sqlite3_step(st) == SQLITE_ROW {
                rows.append(SessionRow(
                    id: Int(sqlite3_column_int(st, 0)),
                    createdAt: text(st, 1), mode: text(st, 2), risk: text(st, 3),
                    wellness: Int(sqlite3_column_int(st, 4)),
                    heartRate: sqlite3_column_double(st, 5)))
            }
        }
        sqlite3_finalize(st)
        return rows
    }

    // MARK: - Usuários / controle de acesso

    func userCount() -> Int {
        var st: OpaquePointer?; var n = 0
        if sqlite3_prepare_v2(db, "SELECT COUNT(*) FROM users WHERE active=1", -1, &st, nil) == SQLITE_OK,
           sqlite3_step(st) == SQLITE_ROW { n = Int(sqlite3_column_int(st, 0)) }
        sqlite3_finalize(st)
        return n
    }

    @discardableResult
    func createUser(_ username: String, _ password: String, role: String) -> String? {
        let u = username.trimmingCharacters(in: .whitespaces)
        if u.isEmpty { return "Informe um nome de usuário." }
        if !ROLES.contains(role) { return "Perfil inválido." }
        if let e = validatePassword(password) { return e }
        return insertUser(u, password, role: role) ? nil : "Já existe um usuário com esse nome."
    }

    /// Inserção direta (sem política de senha) — usada pelo seed do admin padrão.
    @discardableResult
    private func insertUser(_ username: String, _ password: String, role: String) -> Bool {
        let salt = Crypto.randomSalt()
        let hash = Crypto.pbkdf2(password: password, salt: salt)
        var st: OpaquePointer?
        let sql = "INSERT INTO users (username, salt, pwd_hash, role) VALUES (?,?,?,?)"
        guard sqlite3_prepare_v2(db, sql, -1, &st, nil) == SQLITE_OK else { return false }
        sqlite3_bind_text(st, 1, username, -1, SQLITE_TRANSIENT)
        sqlite3_bind_text(st, 2, Crypto.hex(salt), -1, SQLITE_TRANSIENT)
        sqlite3_bind_text(st, 3, Crypto.hex(hash), -1, SQLITE_TRANSIENT)
        sqlite3_bind_text(st, 4, role, -1, SQLITE_TRANSIENT)
        let rc = sqlite3_step(st)
        sqlite3_finalize(st)
        return rc == SQLITE_DONE
    }

    /// Semeia um administrador padrão (admin/admin) se não houver nenhum usuário.
    /// ⚠️ Credencial de conveniência — recomenda-se trocar no primeiro acesso.
    func ensureDefaultAdmin() {
        if userCount() == 0 { insertUser("admin", "admin", role: "administrador") }
    }

    /// Retorna o perfil se as credenciais conferem; caso contrário, nil.
    func verify(_ username: String, _ password: String) -> String? {
        var st: OpaquePointer?
        let sql = "SELECT salt, pwd_hash, role FROM users WHERE username=? AND active=1"
        guard sqlite3_prepare_v2(db, sql, -1, &st, nil) == SQLITE_OK else { return nil }
        sqlite3_bind_text(st, 1, username.trimmingCharacters(in: .whitespaces), -1, SQLITE_TRANSIENT)
        var role: String?
        if sqlite3_step(st) == SQLITE_ROW {
            let salt = Crypto.data(fromHex: text(st, 0))
            let stored = text(st, 1)
            if Crypto.hex(Crypto.pbkdf2(password: password, salt: salt)) == stored { role = text(st, 2) }
        }
        sqlite3_finalize(st)
        return role
    }

    // MARK: - Auditoria (append-only)

    func log(_ username: String, _ event: String, _ detail: String = "") {
        var st: OpaquePointer?
        let sql = "INSERT INTO audit_log (username, event, detail) VALUES (?,?,?)"
        if sqlite3_prepare_v2(db, sql, -1, &st, nil) == SQLITE_OK {
            sqlite3_bind_text(st, 1, username, -1, SQLITE_TRANSIENT)
            sqlite3_bind_text(st, 2, event, -1, SQLITE_TRANSIENT)
            sqlite3_bind_text(st, 3, detail, -1, SQLITE_TRANSIENT)
            sqlite3_step(st)
        }
        sqlite3_finalize(st)
    }

    func audit(limit: Int = 500) -> [AuditRow] {
        var rows: [AuditRow] = []
        var st: OpaquePointer?
        let sql = "SELECT ts, username, event, detail FROM audit_log ORDER BY id DESC LIMIT ?"
        if sqlite3_prepare_v2(db, sql, -1, &st, nil) == SQLITE_OK {
            sqlite3_bind_int(st, 1, Int32(limit))
            while sqlite3_step(st) == SQLITE_ROW {
                rows.append(AuditRow(ts: text(st, 0), user: text(st, 1),
                                     event: text(st, 2), detail: text(st, 3)))
            }
        }
        sqlite3_finalize(st)
        return rows
    }

    private func text(_ st: OpaquePointer?, _ col: Int32) -> String {
        guard let c = sqlite3_column_text(st, col) else { return "" }
        return String(cString: c)
    }

    deinit { sqlite3_close(db) }
}
