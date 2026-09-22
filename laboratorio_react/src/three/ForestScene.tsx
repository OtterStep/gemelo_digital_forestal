import { Canvas } from '@react-three/fiber';
import { OrbitControls } from '@react-three/drei';
import { useMemo, useState } from 'react';
import * as THREE from 'three';
import type { Simulation, Terreno } from '../types';

/** Pseudo-random determinista para dispersar retornos LiDAR en el dosel. */
function seededRandom(seed: number) {
  let t = seed + 0x6d2b79f5;
  t = Math.imul(t ^ (t >>> 15), t | 1);
  t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
  return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
}

const COLOR_SANO = new THREE.Color('#39d15c');
const COLOR_MEDIO = new THREE.Color('#e8b93a');
const COLOR_ALTO = new THREE.Color('#e8452f');
const COLOR_TRUNK = new THREE.Color('#8a5a34');
const COLOR_BRANCH = new THREE.Color('#6f4828');

/** Construye una nube de puntos LiDAR densa y detallada con siluetas de árboles reales:
 *  - Tronco vertical cónico y robusto (28 puntos)
 *  - Ramas primarias que emergen del fuste hacia la copa (20 puntos)
 *  - Copa en domo volumétrico característica del bosque amazónico (140 puntos)
 */
function buildPointCloud(data: Simulation['trees'], baseline: boolean, baseElev: number) {
  const positions: number[] = [];
  const colors: number[] = [];

  data.forEach((t, i) => {
    const scale = baseline ? 0.82 : 1;
    const risk = baseline ? 0.28 : t.risk;
    const crownColor = risk > 0.65 ? COLOR_ALTO : risk > 0.4 ? COLOR_MEDIO : COLOR_SANO;

    const cx = t.x;
    const cz = t.y;
    const groundY = t.elevation !== undefined ? t.elevation - baseElev : 0;
    const treeH = t.height * scale;

    // Proporciones biofísicas de árboles tropicales primarios (Tapajós):
    // El fuste/tronco libre de ramas ocupa cerca del 55% de la altura total
    const trunkH = treeH * 0.55;
    const crownH = treeH * 0.45;
    const crownR = Math.max(2.4, t.crown * scale * 1.15);
    const crownCenterY = groundY + trunkH + crownH * 0.55;

    // 1. Tronco vertical con ahusamiento natural (28 retornos láser)
    const trunkPts = 28;
    for (let p = 0; p < trunkPts; p++) {
      const frac = p / (trunkPts - 1);
      const y = groundY + frac * trunkH;
      // El tronco es más ancho en la base (raíces tablares) y se afina hacia la copa
      const radius = (0.42 - frac * 0.16) * (0.85 + 0.3 * seededRandom(i * 47 + p));
      const ang = (p * 1.8 + seededRandom(i * 13 + p) * 0.8) * Math.PI;
      const px = cx + Math.cos(ang) * radius;
      const pz = cz + Math.sin(ang) * radius;
      positions.push(px, y, pz);
      colors.push(COLOR_TRUNK.r, COLOR_TRUNK.g, COLOR_TRUNK.b);
    }

    // 2. Ramas estructurales principales (20 retornos láser bifurcándose hacia la copa)
    const numBranches = 4;
    const ptsPerBranch = 5;
    for (let b = 0; b < numBranches; b++) {
      const baseAng = (b / numBranches) * Math.PI * 2 + seededRandom(i * 89 + b) * 0.5;
      const branchLength = crownR * 0.75;
      for (let bp = 1; bp <= ptsPerBranch; bp++) {
        const bFrac = bp / ptsPerBranch;
        const bx = cx + Math.cos(baseAng) * (branchLength * bFrac);
        const bz = cz + Math.sin(baseAng) * (branchLength * bFrac);
        const by = groundY + trunkH + Math.pow(bFrac, 0.7) * (crownH * 0.45);
        positions.push(bx, by, bz);
        colors.push(COLOR_BRANCH.r, COLOR_BRANCH.g, COLOR_BRANCH.b);
      }
    }

    // 3. Copa del árbol: domo semiesférico/parasol amazónico denso (140 retornos láser)
    const crownPts = 140;
    for (let p = 0; p < crownPts; p++) {
      const u = seededRandom(i * 31 + p * 7);
      const v = seededRandom(i * 59 + p * 11);
      const theta = u * Math.PI * 2;
      // Más puntos en la parte superior y envolvente externa (donde el láser GEDI impacta primero)
      const phi = Math.acos(1 - 1.85 * v);
      const shellJitter = 0.65 + 0.35 * Math.pow(seededRandom(i * 73 + p * 13), 0.5);

      const rx = crownR * shellJitter;
      const rz = crownR * shellJitter;
      const ry = crownH * 0.55 * shellJitter;

      const px = cx + rx * Math.sin(phi) * Math.cos(theta);
      const py = crownCenterY + ry * Math.cos(phi);
      const pz = cz + rz * Math.sin(phi) * Math.sin(theta);

      // Gradiente lumínico sutil: copas superiores más vivas
      const heightFactor = Math.max(0, Math.min(1, (py - (groundY + trunkH)) / crownH));
      const r = THREE.MathUtils.lerp(crownColor.r * 0.85, Math.min(1, crownColor.r * 1.15), heightFactor);
      const g = THREE.MathUtils.lerp(crownColor.g * 0.85, Math.min(1, crownColor.g * 1.15), heightFactor);
      const bCol = THREE.MathUtils.lerp(crownColor.b * 0.85, Math.min(1, crownColor.b * 1.15), heightFactor);

      positions.push(px, py, pz);
      colors.push(r, g, bCol);
    }
  });

  return { positions: new Float32Array(positions), colors: new Float32Array(colors) };
}

function LidarPointCloud({
  data,
  baseline = false,
  baseElev = 0,
  pointSize = 0.45,
}: {
  data: Simulation['trees'];
  baseline?: boolean;
  baseElev?: number;
  pointSize?: number;
}) {
  const { positions, colors } = useMemo(
    () => buildPointCloud(data, baseline, baseElev),
    [data, baseline, baseElev]
  );
  if (positions.length === 0) return null;
  return (
    <points>
      <bufferGeometry>
        <bufferAttribute attach="attributes-position" count={positions.length / 3} array={positions} itemSize={3} />
        <bufferAttribute attach="attributes-color" count={colors.length / 3} array={colors} itemSize={3} />
      </bufferGeometry>
      {/* fog={false}: el gemelo 3D (los puntos) ya no se oscurece al alejar la
          cámara. Antes, la niebla de la escena mezclaba el color de cada punto
          con el color de fondo casi negro a partir de cierta distancia, y con
          maxDistance=220 > fog far=180 eso pasaba todo el tiempo al hacer zoom out. */}
      <pointsMaterial
        size={pointSize}
        vertexColors
        sizeAttenuation
        transparent
        opacity={0.94}
        depthWrite={false}
        fog={false}
      />
    </points>
  );
}

/** Malla de terreno 3D con relieve topográfico real de Copernicus DEM (100 × 100 m). */
function TerrainMesh({
  terreno,
  baseElev,
  size = 100,
}: {
  terreno?: Terreno;
  baseElev: number;
  size?: number;
}) {
  const geometry = useMemo(() => {
    const segs = 32;
    const geo = new THREE.PlaneGeometry(size, size, segs, segs);
    geo.rotateX(-Math.PI / 2);

    const pos = geo.attributes.position;
    if (terreno && terreno.elevations && terreno.elevations.length > 0) {
      const rows = terreno.elevations.length;
      const cols = terreno.elevations[0].length;

      for (let i = 0; i < pos.count; i++) {
        const x = pos.getX(i);
        const z = pos.getZ(i);

        // Mapear de [-50, 50] al área macro de 500x500 m del terreno
        const u = Math.min(cols - 1, Math.max(0, ((x + 250) / 500) * (cols - 1)));
        const v = Math.min(rows - 1, Math.max(0, ((z + 250) / 500) * (rows - 1)));

        const c0 = Math.floor(u);
        const r0 = Math.floor(v);
        const c1 = Math.min(cols - 1, c0 + 1);
        const r1 = Math.min(rows - 1, r0 + 1);

        const tx = u - c0;
        const ty = v - r0;

        const e00 = terreno.elevations[r0][c0];
        const e10 = terreno.elevations[r0][c1];
        const e01 = terreno.elevations[r1][c0];
        const e11 = terreno.elevations[r1][c1];

        const elev = (1 - tx) * (1 - ty) * e00 + tx * (1 - ty) * e10 + (1 - tx) * ty * e01 + tx * ty * e11;
        pos.setY(i, elev - baseElev);
      }
    }
    geo.computeVertexNormals();
    return geo;
  }, [terreno, baseElev, size]);

  return (
    <mesh geometry={geometry} receiveShadow>
      {/* Terreno un poco más claro: con la niebla más lejana ahora se nota su color real. */}
      <meshStandardMaterial color="#1c2a20" roughness={0.95} wireframe={false} />
    </mesh>
  );
}

export function ForestScene({
  data,
  compare = false,
  terreno,
}: {
  data: Simulation['trees'];
  compare?: boolean;
  terreno?: Terreno;
}) {
  const [pointSize, setPointSize] = useState<number>(0.42);

  // Parcela 100 × 100 m (1 hectárea central: x en [-50, 50], y en [-50, 50])
  const subTrees = useMemo(() => {
    return data.filter((t) => Math.abs(t.x) <= 50 && Math.abs(t.y) <= 50);
  }, [data]);

  // Elevación base de referencia
  const baseElev = useMemo(() => {
    if (terreno && terreno.elevation_min) return terreno.elevation_min;
    const elevs = subTrees.map((t) => t.elevation).filter((e): e is number => e !== undefined);
    return elevs.length > 0 ? Math.min(...elevs) : 90.0;
  }, [subTrees, terreno]);

  return (
    <div className="scene" style={{ position: 'relative', width: '100%', height: 560 }}>
      {/* Control flotante para ajustar tamaño de puntos */}
      <div
        className="lidar-controls-overlay"
        style={{
          position: 'absolute',
          top: 12,
          right: 12,
          background: 'rgba(12, 20, 16, 0.88)',
          backdropFilter: 'blur(8px)',
          border: '1px solid rgba(255, 255, 255, 0.12)',
          borderRadius: 8,
          padding: '7px 12px',
          display: 'flex',
          alignItems: 'center',
          gap: 10,
          color: '#e5e7eb',
          fontSize: '0.82rem',
          zIndex: 10,
          boxShadow: '0 4px 14px rgba(0, 0, 0, 0.35)',
        }}
      >
        <label
          htmlFor="lidar-size-slider"
          style={{ display: 'flex', alignItems: 'center', gap: 6, cursor: 'pointer', whiteSpace: 'nowrap' }}
        >
          <span>Puntos LiDAR:</span>
          <strong style={{ color: '#6ee7b7', minWidth: 28, fontFamily: 'monospace' }}>{pointSize.toFixed(2)}</strong>
        </label>
        <input
          id="lidar-size-slider"
          type="range"
          min="0.10"
          max="1.50"
          step="0.05"
          value={pointSize}
          onChange={(e) => setPointSize(parseFloat(e.target.value))}
          style={{
            cursor: 'pointer',
            accentColor: '#10b981',
            width: 100,
            height: 5,
          }}
          title="Ajustar tamaño de los puntos LiDAR"
        />
      </div>

      <Canvas
        style={{ width: '100%', height: '100%', display: 'block' }}
        camera={{ position: [0, 32, 68], fov: 46 }}
      >
        <color attach="background" args={['#090f0c']} />
        {/* Niebla movida mucho más lejos: antes empezaba a 70 y terminaba a 180,
            pero se puede hacer zoom out hasta 220 (maxDistance abajo), así que
            todo se fundía con el fondo negro apenas te alejabas un poco. */}
        <fog attach="fog" args={['#090f0c', 160, 340]} />
        <ambientLight intensity={1.1} />
        <hemisphereLight args={['#9fd8b0', '#0c1210', 0.55]} />
        <directionalLight position={[40, 80, 30]} intensity={1.9} />

        {/* Grilla de la parcela de 100 × 100 m */}
        <gridHelper args={[100, 20, '#365842', '#1a2820']} position={[0, -0.05, 0]} />

        {compare ? (
          <>
            <group position={[-60, 0, 0]}>
              <TerrainMesh terreno={terreno} baseElev={baseElev} size={100} />
              <LidarPointCloud data={subTrees} baseline baseElev={baseElev} pointSize={pointSize} />
            </group>
            <group position={[60, 0, 0]}>
              <TerrainMesh terreno={terreno} baseElev={baseElev} size={100} />
              <LidarPointCloud data={subTrees} baseElev={baseElev} pointSize={pointSize} />
            </group>
          </>
        ) : (
          <>
            <TerrainMesh terreno={terreno} baseElev={baseElev} size={100} />
            <LidarPointCloud data={subTrees} baseElev={baseElev} pointSize={pointSize} />
          </>
        )}

        <OrbitControls
          makeDefault
          enableDamping
          maxPolarAngle={Math.PI / 2 - 0.05}
          minDistance={8}
          maxDistance={220}
        />
      </Canvas>

      <div className="sceneLegend">
        <span style={{ fontWeight: 600, color: '#9ca3af', marginRight: 8 }}>Parcela 100 × 100 m (1 ha - Tapajós):</span>
        <span style={{ color: '#39d15c', fontWeight: 600 }}>● sano</span>
        <span style={{ color: '#e8b93a', fontWeight: 600 }}>● riesgo medio</span>
        <span style={{ color: '#e8452f', fontWeight: 600 }}>● riesgo alto</span>
        <span style={{ marginLeft: 8, opacity: 0.7, color: '#9ca3af' }}>
          · {subTrees.length} árboles ({subTrees.length * 188} retornos LiDAR)
        </span>
      </div>
    </div>
  );
}