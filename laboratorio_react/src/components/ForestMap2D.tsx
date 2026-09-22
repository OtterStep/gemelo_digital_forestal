import { useMemo, useState } from 'react';
import type { Simulation } from '../types';

type LayerKey = 'biomasa' | 'riesgo' | 'loss';

const GRID_COLS = 10;
const GRID_ROWS = 10;

/** Agrupa los árboles reales (result.trees) en una grilla GRID_COLS x GRID_ROWS (500 × 500 m),
 *  promediando riesgo/biomasa/pérdida por celda según su posición x,y real. */
function buildGrid(trees: Simulation['trees']) {
  if (trees.length === 0) return [];

  const xs = trees.map((t) => t.x);
  const ys = trees.map((t) => t.y);
  const xMin = Math.min(...xs), xMax = Math.max(...xs);
  const yMin = Math.min(...ys), yMax = Math.max(...ys);
  const xSpan = xMax - xMin || 1;
  const ySpan = yMax - yMin || 1;

  const buckets = Array.from({ length: GRID_COLS * GRID_ROWS }, () => ({
    risk: 0,
    biomass: 0,
    loss: 0,
    count: 0,
  }));

  trees.forEach((t) => {
    const col = Math.min(GRID_COLS - 1, Math.max(0, Math.floor(((t.x - xMin) / xSpan) * GRID_COLS)));
    const row = Math.min(GRID_ROWS - 1, Math.max(0, Math.floor(((t.y - yMin) / ySpan) * GRID_ROWS)));
    const idx = row * GRID_COLS + col;
    buckets[idx].risk += t.risk;
    buckets[idx].biomass += t.biomass;
    buckets[idx].loss += t.loss;
    buckets[idx].count += 1;
  });

  return buckets.map((b) => ({
    risk: b.count ? b.risk / b.count : 0,
    biomass: b.count ? b.biomass / b.count : 0,
    loss: b.count ? b.loss / b.count : 0,
    count: b.count,
  }));
}

export function ForestMap2D({ data }: { data: Simulation['trees'] }) {
  const [layers, setLayers] = useState<Record<LayerKey, boolean>>({
    biomasa: true,
    riesgo: true,
    loss: true,
  });

  const cells = useMemo(() => buildGrid(data), [data]);

  return (
    <div className="map">
      <div className="layerControls">
        {(Object.keys(layers) as LayerKey[]).map((k) => (
          <label key={k}>
            <input
              type="checkbox"
              checked={layers[k]}
              onChange={() => setLayers((x) => ({ ...x, [k]: !x[k] }))}
            />
            {k === 'biomasa' ? 'Biomasa' : k === 'riesgo' ? 'Riesgo incendio' : 'GFW loss'}
          </label>
        ))}
      </div>

      <div
        className="mapGrid"
        style={{
          display: 'grid',
          gridTemplateColumns: `repeat(${GRID_COLS}, 1fr)`,
          gridTemplateRows: `repeat(${GRID_ROWS}, 1fr)`,
          gap: 2,
          width: '100%',
          aspectRatio: `${GRID_COLS} / ${GRID_ROWS}`,
          position: 'relative',
        }}
      >
        {cells.length === 0 && (
          <div style={{ gridColumn: `1 / span ${GRID_COLS}`, padding: 12, opacity: 0.6 }}>
            Sin árboles en la simulación actual.
          </div>
        )}
        {cells.map((c, i) => {
          const col = i % GRID_COLS;
          const row = Math.floor(i / GRID_COLS);
          // Las 4 celdas centrales (columnas 4 y 5, filas 4 y 5) abarcan la parcela 100 x 100 m
          const isSub = (col === 4 || col === 5) && (row === 4 || row === 5);

          let opacity = 0.15;
          if (layers.riesgo) opacity += c.risk * 0.5;
          if (layers.biomasa) opacity += Math.min(1, c.biomass / 210) * 0.2;
          if (layers.loss) opacity += c.loss * 0.5;
          const color = layers.riesgo
            ? c.risk > 0.65
              ? '#b63b25'
              : c.risk > 0.4
              ? '#d5a52e'
              : '#39784a'
            : '#647269';

          return (
            <div
              key={i}
              title={`Celda ${i + 1} ${isSub ? '[Parcela 3D 100×100m]' : '[Macro 500×500m]'} · ${c.count} árboles · riesgo ${(c.risk * 100).toFixed(0)}%`}
              style={{
                width: '100%',
                height: '100%',
                opacity: Math.min(1, opacity),
                background: color,
                outline: isSub ? '2px dashed rgba(110, 231, 183, 0.85)' : undefined,
                outlineOffset: -2,
              }}
            />
          );
        })}
      </div>

      <div className="mapLabel" style={{ display: 'flex', justifyContent: 'space-between', flexWrap: 'wrap', gap: 6 }}>
        <span>Área macro 500 × 500 m ({data.length} puntos)</span>
        <span style={{ color: '#6ee7b7' }}>□ Recuadro punteado: Parcela 3D (100 × 100 m · 1 ha)</span>
      </div>
    </div>
  );
}