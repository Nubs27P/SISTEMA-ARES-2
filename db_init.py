import sqlite3
from pathlib import Path
import random, hashlib
from datetime import datetime

APP_DIR = Path('app')
APP_DIR.mkdir(exist_ok=True)
DB = APP_DIR / 'ares.db'

def gerar_codigo_acesso():
    return str(100000 + random.randint(0, 899999))

def gerar_matricula(id_aluno):
    ano = datetime.now().year
    return f"ARES-{ano}-{str(id_aluno).zfill(5)}"

con = sqlite3.connect(DB)
cur = con.cursor()

# Administradores
cur.execute("""
CREATE TABLE IF NOT EXISTS administradores (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT NOT NULL UNIQUE,
    senha_hash TEXT NOT NULL,
    mestre INTEGER DEFAULT 0,
    foto TEXT
)
""")

# Professores
cur.execute("""
CREATE TABLE IF NOT EXISTS professores (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome_completo TEXT NOT NULL,
    disciplina TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    codigo_primeiro_acesso TEXT,
    senha_hash TEXT,
    foto TEXT
)
""")

# Professor turmas (vínculo)
cur.execute("""
CREATE TABLE IF NOT EXISTS professor_turmas (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    professor_id INTEGER NOT NULL,
    serie TEXT NOT NULL,
    turma TEXT NOT NULL,
    FOREIGN KEY(professor_id) REFERENCES professores(id)
)
""")

# Alunos
cur.execute("""
CREATE TABLE IF NOT EXISTS alunos (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome_completo TEXT NOT NULL,
    nome_mae TEXT NOT NULL,
    nome_pai TEXT,
    idade INTEGER NOT NULL,
    serie TEXT NOT NULL,
    turma TEXT,
    matricula TEXT UNIQUE,
    codigo_primeiro_acesso TEXT,
    pontos_avaliacoes REAL DEFAULT 0,   -- 0..40
    missoes REAL DEFAULT 0,            -- 0..30
    disciplina REAL DEFAULT 0,         -- 0..20
    presenca REAL DEFAULT 0,           -- 0..10
    pontos_totais REAL DEFAULT 0,
    patente TEXT DEFAULT 'Recruta',
    foto TEXT
)
""")

# Avaliações (detalhe por aluno)
cur.execute("""
CREATE TABLE IF NOT EXISTS avaliacoes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    aluno_id INTEGER NOT NULL,
    prova1 REAL DEFAULT 0,
    prova2 REAL DEFAULT 0,
    prova3 REAL DEFAULT 0,
    prova_final REAL DEFAULT 0,
    pontuacao_total REAL DEFAULT 0,
    FOREIGN KEY(aluno_id) REFERENCES alunos(id)
)
""")

# Missões (registro)
cur.execute("""
CREATE TABLE IF NOT EXISTS missoes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    aluno_id INTEGER,
    descricao TEXT,
    pontos REAL,
    data TEXT DEFAULT CURRENT_TIMESTAMP
)
""")

# Notificações (log)
cur.execute("""
CREATE TABLE IF NOT EXISTS notificacoes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    titulo TEXT,
    mensagem TEXT,
    user_id INTEGER,
    serie TEXT,
    turma TEXT,
    data_envio TEXT DEFAULT CURRENT_TIMESTAMP
)
""")

# Tokens (para push)
cur.execute("""
CREATE TABLE IF NOT EXISTS tokens (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_type TEXT, -- 'aluno','professor','admin'
    user_id INTEGER,
    token TEXT,
    device TEXT,
    criado_em TEXT DEFAULT CURRENT_TIMESTAMP
)
""")

con.commit()

# Create default Admin Mestre if not exists
cur.execute("SELECT id FROM administradores WHERE mestre=1 LIMIT 1")
if not cur.fetchone():
    default_email = 'admin@ares.com'
    default_pass = 'Mestre123'  # DEMO: altere em produção
    senha_hash = hashlib.sha256(default_pass.encode('utf-8')).hexdigest()
    cur.execute("INSERT INTO administradores (email, senha_hash, mestre) VALUES (?,?,1)",
                (default_email, senha_hash))
    print('Administrador mestre criado:', default_email, default_pass)

# Sample professor
cur.execute("SELECT id FROM professores WHERE email='maria@ares.com'")
if not cur.fetchone():
    codigo = gerar_codigo_acesso()
    cur.execute("INSERT INTO professores (nome_completo, disciplina, email, codigo_primeiro_acesso) VALUES (?,?,?,?)",
                ('Prof. Maria Silva','Matemática','maria@ares.com', codigo))
    print('Professor criado:', 'maria@ares.com', 'codigo:', codigo)

# Sample student
cur.execute("SELECT id FROM alunos WHERE nome_completo='Joao Silva'")
if not cur.fetchone():
    cur.execute("INSERT INTO alunos (nome_completo, nome_mae, nome_pai, idade, serie) VALUES (?,?,?,?,?)",
                ('Joao Silva','Maria Aparecida','Carlos Alberto',14,'9º Ano'))
    student_id = cur.lastrowid
    matricula = gerar_matricula(student_id)
    codigo = gerar_codigo_acesso()
    cur.execute("UPDATE alunos SET matricula=?, codigo_primeiro_acesso=? WHERE id=?",
                (matricula, codigo, student_id))
    cur.execute("INSERT INTO avaliacoes (aluno_id) VALUES (?)", (student_id,))
    print('Aluno criado:', matricula, 'codigo:', codigo)

con.commit()
con.close()
print("DB inicializado em", DB)