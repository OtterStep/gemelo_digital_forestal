"""Pantalla principal: monitor de resultados de entrenamiento."""
import json, time
from pathlib import Path
import streamlit as st
import pandas as pd
import plotly.express as px
from modulo_ia.demo import generar_historial_demo
from config import MODELOS, PHASE_NAMES, MODELOS_DIR, SOURCE_VERSION

st.set_page_config(page_title="Monitor de Entrenamiento", page_icon="📊", layout="wide")

HIST=MODELOS_DIR/"historial_entrenamiento.json"
BEST=MODELOS_DIR/"mejor_modelo.json"

@st.cache_data

def cargar_historial(mtime=None):
    if HIST.exists():
        return json.loads(HIST.read_text(encoding='utf-8'))
    return generar_historial_demo(HIST)

def estado_icon(s): return {"completada":"✅","en curso":"🟡","pendiente":"⚪","error":"🔴"}.get(s,"⚪")

st.title("📊 Monitor de Entrenamiento")
st.caption("Resultados simulados por defecto · preparados para sustituirse por artefactos exportados desde Colab")

with st.sidebar:
    st.header("Artefactos")
    st.write("Carga los resultados reales cuando estén disponibles.")
    up_hist=st.file_uploader("historial_entrenamiento.json", type="json")
    up_best=st.file_uploader("mejor_modelo.json", type="json")
    up_model=st.file_uploader("Modelo entrenado (.pkl/.joblib/.h5)", type=["pkl","joblib","h5"])
    if up_hist:
        try:
            data=json.loads(up_hist.getvalue().decode('utf-8'))
            st.session_state['historial']=data
            st.success("Historial cargado en la sesión")
        except Exception as e: st.error(f"JSON inválido: {e}")
    if up_best:
        st.session_state['best']=json.loads(up_best.getvalue().decode('utf-8'))
        st.success("Mejor modelo cargado")
    if up_model: st.info(f"Modelo listo para integración: {up_model.name}")
    if st.button("Regenerar demo", use_container_width=True):
        generar_historial_demo(HIST); st.cache_data.clear(); st.rerun()

hist=st.session_state.get('historial') or cargar_historial(HIST.stat().st_mtime if HIST.exists() else None)

phases=hist.get('phases',[])
completed=sum(p.get('status')=='completada' for p in phases)
progress=completed/max(len(PHASE_NAMES),1)

c1,c2,c3,c4=st.columns(4)
c1.metric("Progreso del pipeline", f"{progress:.0%}")
c2.metric("Fases", f"{completed}/{len(PHASE_NAMES)}")
c3.metric("Modelos", len(hist.get('models',MODELOS)))
c4.metric("Fuente", hist.get('source_version',SOURCE_VERSION))
st.progress(progress)

st.subheader("1. Fases del entrenamiento")
for p in phases:
    status=p.get('status','pendiente'); pct=1.0 if status=='completada' else 0.0
    with st.container(border=True):
        a,b,c=st.columns([4,2,2])
        a.markdown(f"### {estado_icon(status)} {p['phase']}")
        b.write(f"**Estado:** {status}")
        b.write(f"**Duración:** {p.get('duration_s','—')} s")
        c.progress(pct)
        if p.get('metrics'): st.json(p['metrics'], expanded=False)
        with st.expander("Ver log"):
            st.code(p.get('log','Sin mensajes'))

st.subheader("2. Comparativa de modelos")
models=hist.get('models',{})
rows=[]
for name,m in models.items(): rows.append({"Modelo":name,**m})
df=pd.DataFrame(rows)
st.dataframe(df,use_container_width=True,hide_index=True)
if not df.empty:
    fig=px.bar(df,x='Modelo',y='r2',text='r2',title='R² final (demo)')
    fig.update_yaxes(range=[0,1]); st.plotly_chart(fig,use_container_width=True)

st.subheader("3. Resultados por fase")
tab1,tab2,tab3,tab4=st.tabs(["CV k=5","GridSearch","EDA","Evolución"])
with tab1:
    cv=next((p for p in phases if 'Validación' in p['phase']),None)
    if cv:
        foldrows=[]
        for model,v in cv['metrics']['folds'].items():
            for i,(r,rm) in enumerate(zip(v['r2'],v['rmse']),1): foldrows.append({'Modelo':model,'Fold':i,'R²':r,'RMSE':rm})
        cdf=pd.DataFrame(foldrows); st.dataframe(cdf,use_container_width=True,hide_index=True)
        fig=px.line(cdf,x='Fold',y='R²',color='Modelo',markers=True,title='Curva R² por fold')
        st.plotly_chart(fig,use_container_width=True)
with tab2:
    hp=next((p for p in phases if 'hiperparámetros' in p['phase']),None)
    if hp: st.dataframe(pd.DataFrame([hp['metrics']]),use_container_width=True,hide_index=True)
    st.info('Aquí se pueden reemplazar estos datos por results_ de GridSearchCV exportados desde Colab.')
with tab3:
    st.write('Matriz de correlación y curvas EDA: placeholder listo para recibir artefactos de analisis_exploratorio.py.')
    corr=pd.DataFrame([[1,.82,.55,.31],[.82,1,.67,.42],[.55,.67,1,.74],[.31,.42,.74,1]],columns=['AGB','NDVI','LAI','FMC'],index=['AGB','NDVI','LAI','FMC'])
    st.plotly_chart(px.imshow(corr,text_auto=True,title='Matriz de correlación sintética'),use_container_width=True)
with tab4:
    evo=[]
    for i,p in enumerate(phases,1):
        met=p.get('metrics',{}); r=met.get('mejor_r2') or met.get('r2')
        if r is not None: evo.append({'Fase':p['phase'],'R²':r})
    if evo: st.plotly_chart(px.line(pd.DataFrame(evo),x='Fase',y='R²',markers=True,title='Evolución de R²'),use_container_width=True)

st.subheader("4. Acciones de demostración")
model=st.selectbox('Modelo / fase a simular', MODELOS)
phase=st.selectbox('Fase', PHASE_NAMES)
if st.button('▶ Re-ejecutar fase con datos de ejemplo',type='primary'):
    bar=st.progress(0); box=st.empty()
    for i in range(1,11):
        time.sleep(.08); bar.progress(i/10); box.info(f"Ejecutando demo: {phase} · {i*10}% · modelo={model} · synthetic_test")
    st.success('Fase demo finalizada. No se entrenaron modelos reales ni se usaron descargas externas.')

st.subheader("5. Exportar historial")
st.download_button('⬇ Descargar historial JSON',data=json.dumps(hist,ensure_ascii=False,indent=2),file_name='historial_entrenamiento.json',mime='application/json',use_container_width=True)
