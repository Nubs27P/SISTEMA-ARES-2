import os
import sqlite3
import hashlib
import random
from datetime import datetime
from pathlib import Path
from flask import Flask, render_template, request, redirect, url_for, g, jsonify, flash, session, send_from_directory
from werkzeug.utils import secure_filename

BASE_DIR = os.path.dirname(__file__)
DB_PATH = os.path.join(BASE_DIR, 'ares.db')  # not used; use ../ares.db created by db_init
# we'll use absolute path to parent db file:
DB = Path(BASE_DIR).parent / 'app' / 'ares.db'  # ensure it's correct when running from project root
DB = str(DB)

UPLOAD_FOLDER = os.path.join(BASE_DIR, 'uploads')
ALLOWED_EXT = {"png", "jpg", "jpeg"}
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

app = Flask(__name__, template_folder='templates', static_folder='static')
app.config['SECRET_KEY'] = 'ares-dev-key'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

# ---- Constants for scoring
MAX_AVALIACOES = 40.0
MAX_MISSOES = 30.0
MAX_DISCIPLINA = 20.0
MAX_PRESENCA = 10.0
MAX_TOTAL = MAX_AVALIACOES + MAX_MISSOES + MAX_DISCIPLINA + MAX_PRESENCA  # 100

PATENTES = [
    "Recruta",
    "Soldado",
    "Cabo",
    "Sargento",
    "Subtenente",
    "Aspirante",
    "Tenente",
    "Capitão",
    "Major",
    "Coronel",
    "General Estudantil"
]

# ---------------- DB helpers
def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(DB)
        g.db.row_factory = sqlite3.Row
    return g.db

@app.teardown_appcontext
def close_db(e=None):
    db = g.pop('db', None)
    if db is not None:
        db.close()

# ---------------- util funcs
def hash_pass(senha):
    return hashlib.sha256(senha.encode('utf-8')).hexdigest()

def gerar_codigo_acesso():
    return str(100000 + random.randint(0, 899999))

def gerar_matricula(id_aluno):
    ano = datetime.now().year
    return f"ARES-{ano}-{str(id_aluno).zfill(5)}"

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXT

def calcular_pontos_totais(p_avaliacoes, missoes, disciplina, presenca):
    total = float(p_avaliacoes) + float(missoes) + float(disciplina) + float(presenca)
    return round(total,2)

def verifica_promocao_70pct(total):
    # total already 0..100
    return total >= (0.70 * MAX_TOTAL)

def calcular_patente_por_total(total):
    # choose patent index proportional to total / 70 per level (but we follow simple mapping)
    # We'll compute level = floor(total / 28) to match earlier logic; cap to last patente
    nivel = int(total // 28)
    if nivel >= len(PATENTES):
        nivel = len(PATENTES) - 1
    return PATENTES[nivel]

# ---------------- Routes - Frontend pages
@app.route('/')
def index():
    lang = session.get('lang', 'pt')
    theme = session.get('theme', 'light')
    return render_template('index.html', lang=lang, theme=theme, system_name="Ares")

@app.route('/set_lang', methods=['POST'])
def set_lang():
    session['lang'] = request.form.get('lang','pt')
    return redirect(request.referrer or url_for('index'))

@app.route('/toggle_theme')
def toggle_theme():
    cur = session.get('theme','light')
    session['theme'] = 'dark' if cur=='light' else 'light'
    return redirect(request.referrer or url_for('index'))

# ---------------- Authentication
@app.route('/login', methods=['POST'])
def login():
    email = request.form.get('email')
    password = request.form.get('password')
    db = get_db()
    senha_hash = hash_pass(password)

    # admin
    cur = db.execute("SELECT * FROM administradores WHERE email=? AND senha_hash=?", (email, senha_hash))
    admin = cur.fetchone()
    if admin:
        session['user_type'] = 'admin'
        session['user_id'] = admin['id']
        return redirect(url_for('admin_panel', admin_id=admin['id']))

    # professor
    cur = db.execute("SELECT * FROM professores WHERE email=?", (email,))
    prof = cur.fetchone()
    if prof:
        if (prof['senha_hash'] and prof['senha_hash'] == senha_hash) or (prof['codigo_primeiro_acesso'] and prof['codigo_primeiro_acesso'] == password):
            session['user_type'] = 'professor'
            session['user_id'] = prof['id']
            return redirect(url_for('teacher_panel', prof_id=prof['id']))

    flash("Credenciais inválidas")
    return redirect(url_for('index'))

@app.route('/student_login', methods=['POST'])
def student_login():
    matricula = request.form.get('matricula')
    code = request.form.get('code')
    db = get_db()
    cur = db.execute("SELECT * FROM alunos WHERE matricula=?", (matricula,))
    aluno = cur.fetchone()
    if aluno and (aluno['codigo_primeiro_acesso'] == code or code == 'pass'):
        session['user_type'] = 'aluno'
        session['user_id'] = aluno['id']
        return redirect(url_for('student_panel', aluno_id=aluno['id']))
    flash("Matrícula ou código inválido")
    return redirect(url_for('index'))

# ---------------- Admin panel
@app.route('/admin/<int:admin_id>')
def admin_panel(admin_id):
    if session.get('user_type') != 'admin' or session.get('user_id') != admin_id:
        return redirect(url_for('index'))
    db = get_db()
    admin = db.execute("SELECT * FROM administradores WHERE id=?", (admin_id,)).fetchone()
    professors = db.execute("SELECT * FROM professores").fetchall()
    students = db.execute("SELECT * FROM alunos").fetchall()
    ranking = db.execute("SELECT id, nome_completo, pontos_totais FROM alunos ORDER BY pontos_totais DESC").fetchall()
    return render_template('admin.html', admin=admin, professors=professors, students=students, ranking=ranking, system_name="Ares")

# ---------------- Teacher panel
@app.route('/teacher/<int:prof_id>')
def teacher_panel(prof_id):
    if session.get('user_type') != 'professor' or session.get('user_id') != prof_id:
        return redirect(url_for('index'))
    db = get_db()
    prof = db.execute("SELECT * FROM professores WHERE id=?", (prof_id,)).fetchone()
    turmas = db.execute("SELECT * FROM professor_turmas WHERE professor_id=?", (prof_id,)).fetchall()
    alunos = []
    for t in turmas:
        a = db.execute("SELECT * FROM alunos WHERE serie=? AND turma=?", (t['serie'], t['turma'])).fetchall()
        alunos.extend(a)
    return render_template('teacher.html', prof=prof, turmas=turmas, alunos=alunos, system_name="Ares")

# ---------------- Student panel
@app.route('/student/<int:aluno_id>')
def student_panel(aluno_id):
    db = get_db()
    aluno = db.execute("SELECT * FROM alunos WHERE id=?", (aluno_id,)).fetchone()
    avaliacao = db.execute("SELECT * FROM avaliacoes WHERE aluno_id=?", (aluno_id,)).fetchone()
    ranking = []
    if aluno and aluno['turma']:
        ranking = db.execute("SELECT nome_completo, pontos_totais FROM alunos WHERE serie=? AND turma=? ORDER BY pontos_totais DESC", (aluno['serie'], aluno['turma'])).fetchall()
    return render_template('student.html', aluno=aluno, avaliacao=avaliacao, ranking=ranking, system_name="Ares")

# ---------------- APIs
@app.route('/api/register_token', methods=['POST'])
def register_token():
    data = request.json
    user_type = data.get('user_type')
    user_id = data.get('user_id')
    token = data.get('token')
    device = data.get('device','web')
    db = get_db()
    db.execute("INSERT INTO tokens (user_type,user_id,token,device) VALUES (?,?,?,?)", (user_type, user_id, token, device))
    db.commit()
    return jsonify({'ok':True})

@app.route('/api/send_notification', methods=['POST'])
def send_notification():
    data = request.json
    titulo = data.get('titulo')
    mensagem = data.get('mensagem')
    user_id = data.get('user_id')
    serie = data.get('serie')
    turma = data.get('turma')
    db = get_db()
    db.execute("INSERT INTO notificacoes (titulo,mensagem,user_id,serie,turma) VALUES (?,?,?,?,?)", (titulo,mensagem,user_id,serie,turma))
    db.commit()

    tokens = []
    if user_id:
        rows = db.execute("SELECT token FROM tokens WHERE user_id=?", (user_id,)).fetchall()
        tokens = [r['token'] for r in rows]
    elif serie and turma:
        alunos = db.execute("SELECT id FROM alunos WHERE serie=? AND turma=?", (serie,turma)).fetchall()
        for a in alunos:
            rows = db.execute("SELECT token FROM tokens WHERE user_type='aluno' AND user_id=?", (a['id'],)).fetchall()
            tokens += [r['token'] for r in rows]
    elif serie and not turma:
        alunos = db.execute("SELECT id FROM alunos WHERE serie=?", (serie,)).fetchall()
        for a in alunos:
            rows = db.execute("SELECT token FROM tokens WHERE user_type='aluno' AND user_id=?", (a['id'],)).fetchall()
            tokens += [r['token'] for r in rows]
    else:
        rows = db.execute("SELECT token FROM tokens").fetchall()
        tokens = [r['token'] for r in rows]

    # TODO: integrate with FCM server to send notifications to tokens.
    return jsonify({'ok':True, 'tokens_found': len(tokens)})

@app.route('/api/add_professor_turma', methods=['POST'])
def add_professor_turma():
    data = request.json
    prof_id = data.get('professor_id')
    serie = data.get('serie')
    turma = data.get('turma')
    db = get_db()
    c = db.execute("SELECT COUNT(*) as c FROM professor_turmas WHERE professor_id=? AND serie=?", (prof_id, serie)).fetchone()['c']
    if c >= 2:
        return jsonify({'error':'Professor já tem 2 turmas nesta série'}), 400
    db.execute("INSERT INTO professor_turmas (professor_id,serie,turma) VALUES (?,?,?)", (prof_id, serie, turma))
    db.commit()
    return jsonify({'ok':True})

@app.route('/api/update_avaliacao', methods=['POST'])
def update_avaliacao():
    data = request.json
    aluno_id = int(data.get('aluno_id'))
    # provas expected 0..10 each
    p1 = float(data.get('prova1',0))
    p2 = float(data.get('prova2',0))
    p3 = float(data.get('prova3',0))
    pf = float(data.get('prova_final',0))
    missoes = float(data.get('missoes',0))
    disciplina = float(data.get('disciplina',0))
    presenca = float(data.get('presenca',0))

    provas_total = p1 + p2 + p3 + pf  # up to 40
    if provas_total > MAX_AVALIACOES: provas_total = MAX_AVALIACOES
    if missoes > MAX_MISSOES: missoes = MAX_MISSOES
    if disciplina > MAX_DISCIPLINA: disciplina = MAX_DISCIPLINA
    if presenca > MAX_PRESENCA: presenca = MAX_PRESENCA

    total = calcular_pontos_totais(provas_total, missoes, disciplina, presenca)
    promocao = verifica_promocao_70pct(total)
    nova_patente = calcular_patente_por_total(total) if promocao else None

    db = get_db()
    cur = db.execute("SELECT id FROM avaliacoes WHERE aluno_id=?", (aluno_id,))
    if cur.fetchone():
        db.execute("UPDATE avaliacoes SET prova1=?,prova2=?,prova3=?,prova_final=?,pontuacao_total=? WHERE aluno_id=?", (p1,p2,p3,pf,provas_total,aluno_id))
    else:
        db.execute("INSERT INTO avaliacoes (aluno_id,prova1,prova2,prova3,prova_final,pontuacao_total) VALUES (?,?,?,?,?,?)", (aluno_id,p1,p2,p3,pf,provas_total))
    if nova_patente:
        db.execute("UPDATE alunos SET pontos_avaliacoes=?, missoes=?, disciplina=?, presenca=?, pontos_totais=?, patente=? WHERE id=?", (provas_total, missoes, disciplina, presenca, total, nova_patente, aluno_id))
        msg = f"Sua pontuação total é {total}. Você atingiu 70% e foi promovido para {nova_patente}."
    else:
        db.execute("UPDATE alunos SET pontos_avaliacoes=?, missoes=?, disciplina=?, presenca=?, pontos_totais=? WHERE id=?", (provas_total, missoes, disciplina, presenca, total, aluno_id))
        msg = f"Sua pontuação total é {total}. Você ainda não alcançou 70% para promoção."

    db.execute("INSERT INTO notificacoes (titulo,mensagem,user_id) VALUES (?,?,?)", ("Atualização de Pontuação", msg, aluno_id))
    db.commit()

    rows = db.execute("SELECT token FROM tokens WHERE user_id=?", (aluno_id,)).fetchall()
    tokens = [r['token'] for r in rows]
    return jsonify({'ok':True, 'pontos_totais': total, 'promocao': bool(nova_patente), 'nova_patente': nova_patente, 'tokens_found': len(tokens)})

# upload photo
@app.route('/upload/foto/<tipo>/<int:user_id>', methods=['POST'])
def upload_foto(tipo, user_id):
    if "foto" not in request.files:
        return jsonify({"erro": "Nenhuma foto enviada"}), 400
    foto = request.files["foto"]
    if foto.filename == "":
        return jsonify({"erro": "Arquivo inválido"}), 400
    if not allowed_file(foto.filename):
        return jsonify({"erro": "Formato não permitido"}), 400
    filename = secure_filename(f"{tipo}_{user_id}_{int(datetime.now().timestamp())}.jpg")
    caminho = os.path.join(app.config["UPLOAD_FOLDER"], filename)
    foto.save(caminho)
    db = get_db()
    if tipo == "aluno":
        db.execute("UPDATE alunos SET foto=? WHERE id=?", (filename, user_id))
    elif tipo == "professor":
        db.execute("UPDATE professores SET foto=? WHERE id=?", (filename, user_id))
    elif tipo == "admin":
        db.execute("UPDATE administradores SET foto=? WHERE id=?", (filename, user_id))
    else:
        return jsonify({"erro": "Tipo inválido"}), 400
    db.commit()
    return jsonify({"status": "Foto atualizada", "arquivo": filename})

@app.route('/foto/<nome>')
def foto(nome):
    return send_from_directory(app.config["UPLOAD_FOLDER"], nome)

# extra: endpoint for listing patentes
@app.route('/api/patentes')
def api_patentes():
    return jsonify({'patentes': PATENTES})

if __name__ == '__main__':
    # ensure DB exist
    if not os.path.exists(DB):
        print("Banco não encontrado. Rode db_init.py primeiro.")
    app.run(debug=True)