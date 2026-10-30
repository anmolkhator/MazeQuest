"""Accounts, scores and leaderboard in a local SQLite file. Passwords: PBKDF2-SHA256 + random salt."""
import hashlib, hmac, os, re, sqlite3, time

DB = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "mazequest.db")


def _db():
    con = sqlite3.connect(DB)
    con.executescript("""CREATE TABLE IF NOT EXISTS users(name TEXT PRIMARY KEY COLLATE NOCASE, salt BLOB, hash BLOB);
        CREATE TABLE IF NOT EXISTS scores(user TEXT, score INT, size INT, eff INT, ts REAL);""")
    return con


def _hash(pw, salt):
    return hashlib.pbkdf2_hmac("sha256", pw.encode(), salt, 120_000)


def register(user, pw):
    if not re.fullmatch(r"\w{3,16}", user):
        return False, "Username: 3 to 16 letters, numbers or _"
    if len(pw) < 6:
        return False, "Password needs at least 6 characters"
    salt = os.urandom(16)
    try:
        with _db() as con:
            con.execute("INSERT INTO users VALUES(?,?,?)", (user, salt, _hash(pw, salt)))
    except sqlite3.IntegrityError:
        return False, "That username is taken"
    return True, ""


def login(user, pw):
    row = _db().execute("SELECT name,salt,hash FROM users WHERE name=?", (user,)).fetchone()
    if row and hmac.compare_digest(row[2], _hash(pw, row[1])):
        return True, row[0]
    return False, "Wrong username or password"


def record_win(user, score, size, eff):
    with _db() as con:
        con.execute("INSERT INTO scores VALUES(?,?,?,?,?)", (user, score, size, eff, time.time()))


def stats(user):                                 # (wins, best score)
    return _db().execute("SELECT COUNT(*), COALESCE(MAX(score),0) FROM scores WHERE user=?", (user,)).fetchone()


def leaderboard(n=8):
    return _db().execute("SELECT user,score,size,eff FROM scores ORDER BY score DESC LIMIT ?", (n,)).fetchall()


def canon(user):                                 # the stored spelling of a username, or None
    row = _db().execute("SELECT name FROM users WHERE name=?", (user,)).fetchone()
    return row[0] if row else None
