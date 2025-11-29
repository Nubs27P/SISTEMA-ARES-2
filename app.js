// app/static/app.js
function toggleTheme(){
  document.body.classList.toggle('dark');
  const theme = document.body.classList.contains('dark') ? 'dark' : 'light';
  localStorage.setItem('ares_theme', theme);
}

function changeLang(lang){
  localStorage.setItem('ares_lang', lang);
  applyI18n();
}

function applyI18n(){
  const lang = localStorage.getItem('ares_lang') || 'pt';
  const map = window.ARES_I18N && window.ARES_I18N[lang] ? window.ARES_I18N[lang] : window.ARES_I18N['pt'];
  document.querySelectorAll('[data-i18n]').forEach(el=>{
    const key = el.getAttribute('data-i18n');
    if(map[key]) el.innerText = map[key];
  });
}

window.addEventListener('DOMContentLoaded', ()=>{
  const savedTheme = localStorage.getItem('ares_theme') || 'light';
  if(savedTheme === 'dark') document.body.classList.add('dark');
  applyI18n();
});

// Helper to add turma (teacher)
async function addTurma(profId){
  const f = document.getElementById('addTurmaForm');
  const serie = f.querySelector('input[name="serie"]').value;
  const turma = f.querySelector('input[name="turma"]').value;
  const res = await fetch('/api/add_professor_turma', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({professor_id:profId, serie, turma})});
  const j = await res.json();
  if(j.error) alert('Erro: '+j.error);
  else location.reload();
}

// Enviar pontos (student)
async function enviarPontos(alunoId){
  const f = document.getElementById('pontosForm');
  const data = {
    aluno_id: alunoId,
    prova1: parseFloat(f.prova1.value||0),
    prova2: parseFloat(f.prova2.value||0),
    prova3: parseFloat(f.prova3.value||0),
    prova_final: parseFloat(f.prova_final.value||0),
    missoes: parseFloat(f.missoes.value||0),
    disciplina: parseFloat(f.disciplina.value||0),
    presenca: parseFloat(f.presenca.value||0)
  };
  const res = await fetch('/api/update_avaliacao', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(data)});
  const j = await res.json();
  alert(JSON.stringify(j));
  if(j.ok) location.reload();
}

// Enviar foto
async function enviarFoto(tipo, userId){
  const file = document.getElementById('input-foto').files[0];
  if(!file) return alert('Selecione uma foto');
  const form = new FormData();
  form.append('foto', file);
  const res = await fetch(`/upload/foto/${tipo}/${userId}`, {method:'POST', body: form});
  const j = await res.json();
  if(j.arquivo){
    document.getElementById('foto-preview').src = `/foto/${j.arquivo}`;
  }
  alert(j.status || j.erro);
}