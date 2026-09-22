import type {Scenario,Simulation} from '../types';
import {ScenarioControls} from '../components/ScenarioControls';
import {KpiCard} from '../components/KpiCard';
import {ModelTrace} from '../components/ModelTrace';
import { WithInfo } from '../components/Glossary';
export type IAProps={configurado:boolean;explicacion:string;cargando:boolean;error:string;onExplicar:()=>void};
export function ScenarioView({s,setS,result,run,loading,ia}:{s:Scenario;setS:(x:Scenario)=>void;result:Simulation|null;run:()=>void;loading:boolean;ia:IAProps}){
  const modelos=result?.insumos?.modelos?.map(m=>m.modelo).filter(Boolean).join(' · ');
  return <div className="layout">
    <aside className="panel">
      <h2>Escenario what-if</h2>
      <p className="muted">Modifica las condiciones y ejecuta una simulación. Origen de la inferencia: {result?.source_version?<b>{result.source_version}</b>:'sin simular aún'}.</p>
      <ScenarioControls s={s} setS={setS} onRun={run} loading={loading}/>
    </aside>
    <section>
      <div className="kpis">
        {result&&<>
          <WithInfo term="biomasa"><KpiCard label="Biomasa" value={result.scenario.biomasa} delta={result.delta.biomasa} unit=" Mg/ha"/></WithInfo>
          <WithInfo term="npp"><KpiCard label="NPP" value={result.scenario.npp} delta={result.delta.npp} unit=" Mg C/ha/año"/></WithInfo>
          <WithInfo term="riesgo"><KpiCard label="Riesgo incendio" value={result.scenario.riesgo*100} delta={result.delta.riesgo*100} unit="%"/></WithInfo>
          <WithInfo term="nee"><KpiCard label="NEE (C neto)" value={result.scenario.nee??0} delta={result.delta.nee??0} unit=""/></WithInfo>
        </>}
      </div>
      <div className="panel hero">
        <h2>Resultado de simulación</h2>
        {result?
          <>
            <p className="muted">Comparación respecto a la línea base sin manejo. Modelos analizados: <b>{modelos||'—'}</b>.</p>
            <div className="compare">
              <div><span>Línea base</span><strong>{result.baseline.biomasa.toFixed(1)} Mg/ha</strong></div>
              <div><span>Escenario</span><strong>{result.scenario.biomasa.toFixed(1)} Mg/ha</strong></div>
            </div>
            <ModelTrace insumos={result.insumos}/>
            <div className="iaPanel">
              <h3>Explicación con IA <small>(Gemini)</small></h3>
              {ia.cargando?
                <p className="muted">Analizando la inferencia con Gemini…</p>:
               ia.error?
                <p className="iaError">{ia.error}</p>:
               ia.explicacion?
                <p className="iaText">{ia.explicacion}</p>:
               ia.configurado?
                <><p className="muted">Pide a Gemini que explique en lenguaje sencillo qué significa esta inferencia.</p><button className="primary" onClick={ia.onExplicar}>Explicar con IA</button></>:
                <p className="muted">IA no configurada: define GEMINI_API_KEY en el archivo .env del servidor.</p>}
            </div>
          </>:
          <div className="empty">Ejecuta una simulación para visualizar resultados.</div>}
      </div>
    </section>
  </div>;
}