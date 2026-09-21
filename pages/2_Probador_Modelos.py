"""Probador de modelos: inferencia simulada o con artefacto compatible."""
import streamlit as st
import numpy as np
from config import MODELOS
st.set_page_config(page_title='Probador de Modelos',page_icon='🧪',layout='wide')
st.title('🧪 Probador de Modelos')
st.caption('Sin entrenamiento. Espacio preparado para cargar un modelo exportado desde Colab.')
model=st.selectbox('Modelo',MODELOS)
file=st.file_uploader('Cargar modelo',type=['pkl','joblib','h5'])
cols=st.columns(4)
vals=[]
for i,n in enumerate(['AGB (Mg/ha)','LAI','FMC (%)','NDVI']): vals.append(cols[i].number_input(n,value=[210.0,5.2,78.0,.76][i]))
if st.button('Ejecutar inferencia demo',type='primary'):
    pred=float(np.clip(.35*vals[0]+4*vals[1]+.12*vals[2]+80*vals[3],0,400))
    st.metric('Biomasa predicha (demo)',f'{pred:.1f} Mg/ha')
    st.info(f'Modelo: {model} · fuente_version=synthetic_test')
if file: st.success(f'Archivo recibido: {file.name}. La carga queda lista para conectar al predictor real.')
