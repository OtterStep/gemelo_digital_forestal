import { useState } from 'react';
import type { Simulation } from '../types';
import { ForestMap2D } from '../components/ForestMap2D';
import { ForestScene } from '../three/ForestScene';

export function MapsView({ result }: { result: Simulation | null }) {
  const [compare, setCompare] = useState(false);

  if (!result) {
    return <div className="panel empty">Ejecuta una simulación para cargar las capas 2D y la escena 3D.</div>;
  }

  const numTrees100 = result.trees.filter((t) => Math.abs(t.x) <= 50 && Math.abs(t.y) <= 50).length;

  return (
    <div className="maps">
      <div className="panel">
        <h2>Mapa 2D Analítico (Área Macro 500 × 500 m)</h2>
        <p className="muted">
          Análisis geoespacial de 25 ha con capas de biomasa, riesgo de incendio y deforestación GFW. Se destaca la
          parcela central de 100 × 100 m (1 ha).
        </p>
        <ForestMap2D data={result.trees} />
      </div>
      <div className="panel">
        <div className="rowTitle">
          <div>
            <h2>Gemelo Digital 3D (Parcela 100 × 100 m · 1 ha)</h2>
            <p className="muted">
              Nube LiDAR detallada (fuste, ramas y domo de copa) sobre relieve Copernicus DEM · {numTrees100} árboles.
            </p>
          </div>
          <label className="switch">
            <input type="checkbox" checked={compare} onChange={(e) => setCompare(e.target.checked)} /> Antes / después
          </label>
        </div>
        <ForestScene data={result.trees} compare={compare} terreno={result.terreno} />
      </div>
    </div>
  );
}
