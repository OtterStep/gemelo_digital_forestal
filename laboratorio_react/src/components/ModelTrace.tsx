import type {Insumos} from '../types';
export function ModelTrace({insumos}:{insumos?:Insumos}){
  if(!insumos)return null;
  const g=insumos.gestion||{}, v=insumos.vegetacion_efectiva||{};
  return <div className="traza">
    <h3>¿Qué hace el modelo? · Factores analizados</h3>
    <div className="vege">
      {Object.entries(g).map(([k,x])=><span key={k}>{k.replace(/_/g,' ')}: <b>{x}</b></span>)}
      {Object.entries(v).map(([k,x])=><span key={k}>efectivo {k.replace(/_/g,' ')}: <b>{x}</b></span>)}
    </div>
    <div className="trazaCards">
      {insumos.modelos?.map((m,i)=>(
        <div className="trazaCard" key={i}>
          <div className="trazaHead"><strong>{m.objetivo}</strong><span>{m.modelo} · {m.tipo}</span></div>
          <div className="predictores">
            {m.predictoras.map((p,j)=><span className="pred" key={j}>{p.nombre} <b>{p.valor}</b> {p.unidad}</span>)}
          </div>
          <div className="resultado">{m.resultado!=null?<><span>predicción</span><b>{m.resultado}</b>{m.unidad}</>:<><span>predicción</span><b>no disponible</b></>}</div>
        </div>
      ))}
    </div>
    {insumos.interpretaciones?.length?
      <ul className="interpretaciones">{insumos.interpretaciones.map((t,i)=><li key={i}>{t}</li>)}</ul>:null}
  </div>;
}