import type {Scenario,Simulation} from '../types';
import {KpiCard} from '../components/KpiCard';
import {ModelTrace} from '../components/ModelTrace';
import type {IAProps} from './Scenario';

const FILAS:Array<[keyof Simulation['baseline'],string]>=[['biomasa','Mg/ha'],['npp','Mg C/ha/año'],['riesgo','probabilidad'],['nee','flujo neto de C']];

export function ExportView({s,result,ia}:{s:Scenario;result:Simulation|null;ia:IAProps}){
  const sv=result?.source_version||'synthetic_test';
  const fecha=result?new Date().toLocaleString('es-ES'):'';
  const download=(name:string,text:string,type='application/json')=>{const a=document.createElement('a');a.href=URL.createObjectURL(new Blob([text],{type}));a.download=name;a.click();URL.revokeObjectURL(a.href)};
  const exportJson=()=>{if(!result)return;const payload={generated_at:new Date().toISOString(),source_version:result.source_version,escenario:s,resumen:{linea_base:result.baseline,escenario:result.scenario,delta:result.delta},temporal:result.temporal,modelos_usados:result.insumos?result.insumos.modelos.map(m=>({objetivo:m.objetivo,modelo:m.modelo,tipo:m.tipo,predictoras:m.predictoras,resultado:m.resultado,unidad:m.unidad})):undefined,insumos:result.insumos,explicacion_ia:ia.explicacion||undefined};download(`resultado_escenario_${sv}.json`,JSON.stringify(payload,null,2))};
  const exportCsv=()=>{if(!result)return;const rows:string[]=[];rows.push('# RESUMEN DE LA SIMULACION');rows.push('variable,linea_base,escenario,delta,unidad');for(const [k,u] of FILAS)rows.push(`${k},${result.baseline[k]??''},${result.scenario[k]??''},${result.delta[k]??''},${u}`);if(result.insumos?.modelos?.length){rows.push('');rows.push('# MODELOS UTILIZADOS');rows.push('objetivo,modelo,tipo,resultado,unidad');for(const m of result.insumos.modelos)rows.push(`${m.objetivo},${m.modelo},${m.tipo},${m.resultado??''},${m.unidad}`)}if(ia.explicacion){rows.push('');rows.push('# EXPLICACION CON IA (GEMINI)');rows.push(ia.explicacion.replace(/\r?\n/g,' '))}rows.push('');rows.push('# SERIE TEMPORAL');rows.push('period,biomasa_base,biomasa_escenario,riesgo_base,riesgo_escenario');for(const x of result.temporal)rows.push(`${x.period},${x.baseline},${x.scenario},${x.riesgo_base},${x.riesgo_escenario}`);download(`serie_temporal_${sv}.csv`,rows.join('\n'),'text/csv')};
  return <div className="panel">
    <h2>Exportar resultado</h2>
    <p className="muted">Archivos y reporte imprimible con los resultados de la simulación. Trazabilidad <b>source_version={sv}</b>.</p>
    <div className="exportCards">
      <button className="primary" disabled={!result} onClick={exportJson}>↓ Exportar JSON</button>
      <button disabled={!result} onClick={exportCsv}>↓ Exportar CSV</button>
      <button disabled={!result} onClick={()=>window.print()}>▣ Generar vista imprimible / PDF</button>
      {result&&ia.configurado&&!ia.explicacion&&!ia.cargando&&<button onClick={ia.onExplicar}>✨ Explicar con IA</button>}
      {ia.cargando&&<button disabled>Analizando con Gemini…</button>}
    </div>
    {result&&!ia.configurado&&<p className="muted">IA no configurada: define GEMINI_API_KEY en el archivo .env del servidor para incluir la explicación.</p>}
    {result?
      <div className="report">
        <h2>Reporte de simulación — Gemelo Digital Forestal</h2>
        <p className="muted">Origen: <b>{sv}</b> · generado: {fecha}</p>
        <div className="kpis">
          <KpiCard label="Biomasa" value={result.scenario.biomasa} delta={result.delta.biomasa} unit=" Mg/ha"/>
          <KpiCard label="NPP" value={result.scenario.npp} delta={result.delta.npp} unit=" Mg C/ha/año"/>
          <KpiCard label="Riesgo incendio" value={result.scenario.riesgo*100} delta={result.delta.riesgo*100} unit="%"/>
          <KpiCard label="NEE (C neto)" value={result.scenario.nee??0} delta={result.delta.nee??0} unit=""/>
        </div>
        <div className="compare">
          <div><span>Línea base</span><strong>{result.baseline.biomasa.toFixed(1)} Mg/ha</strong></div>
          <div><span>Escenario</span><strong>{result.scenario.biomasa.toFixed(1)} Mg/ha</strong></div>
        </div>
        {result.insumos&&<ModelTrace insumos={result.insumos}/>}
        {ia.explicacion&&<div className="iaPanel">
          <h3>Explicación con IA <small>(Gemini)</small></h3>
          <p className="iaText">{ia.explicacion}</p>
        </div>}
        {ia.error&&<p className="iaError">{ia.error}</p>}
        <h3>Serie temporal mensual</h3>
        <div className="tableWrap">
          <table>
            <thead><tr><th>period</th><th>biomasa_base</th><th>biomasa_escenario</th><th>riesgo_base</th><th>riesgo_escenario</th></tr></thead>
            <tbody>{result.temporal.map(x=><tr key={x.period}><td>{x.period}</td><td>{x.baseline.toFixed(1)}</td><td>{x.scenario.toFixed(1)}</td><td>{(x.riesgo_base*100).toFixed(1)}%</td><td>{(x.riesgo_escenario*100).toFixed(1)}%</td></tr>)}</tbody>
          </table>
        </div>
        <p className="muted">La predicción es ilustrativa y no representa una estimación operativa real para BR-Sa1.</p>
      </div>:
      <div className="empty">Ejecuta una simulación para poder exportarla.</div>}
  </div>;
}