// components/Glossary.tsx
//
// Componente puramente presentacional: NO llama a la API, NO toca `result`,
// NO recalcula nada. Solo agrega explicaciones de texto sobre elementos
// que ya existen en pantalla. Seguro de insertar sin afectar la inferencia.
import type { ReactNode } from 'react';
import { useState } from 'react';

export const GLOSSARY_TERMS = {
  biomasa: 'Biomasa: cantidad de materia vegetal (troncos, ramas, hojas) por hectárea. Más biomasa = más carbono almacenado en el bosque.',
  npp: 'NPP (Producción Primaria Neta): cuánto carbono "fabrica" el bosque al año mediante fotosíntesis, descontando lo que respira.',
  riesgo: 'Riesgo de incendio: probabilidad estimada de que ocurra un incendio en la zona, según humedad del combustible, vegetación y clima.',
  nee: 'NEE (Intercambio Neto de Ecosistema): si es negativo, el bosque absorbe más CO2 del que libera (actúa como sumidero de carbono). Si es positivo, libera más de lo que absorbe.',
  linea_base: 'Línea base: cómo estaría el bosque si NO se aplicara ninguna acción de manejo (clareo, quema, restauración). Es el punto de comparación.',
  escenario: 'Escenario: cómo cambiaría el bosque con las acciones de manejo que definiste en los controles de la izquierda.',
  fmc: 'FMC (Contenido de Humedad del Combustible): cuánta agua tiene la vegetación seca y la hojarasca. Menos humedad = más riesgo de incendio.',
  lai: 'LAI (Índice de Área Foliar): cuántas "capas" de hojas cubren cada metro cuadrado de suelo. Más LAI = follaje más denso.',
  ndvi: 'NDVI: índice satelital que mide qué tan verde y saludable está la vegetación (0 = sin vegetación, 1 = vegetación muy densa).',
  modelo_entrenado: 'Modelo entrenado: algoritmo de machine learning ajustado con datos reales del sitio FLUXNET Tapajós (2002-2011) para hacer esta predicción.',
} as const;

export type GlossaryKey = keyof typeof GLOSSARY_TERMS;

function splitTerm(def: string) {
  const idx = def.indexOf(':');
  return { title: def.slice(0, idx), body: def.slice(idx + 1).trim() };
}

/** Ícono "ⓘ" chico e inline. Usa `title` nativo (funciona en cualquier navegador,
 *  sin CSS extra) más aria-label para lectores de pantalla. No desplaza layout. */
export function InfoTip({ term, className = '' }: { term: GlossaryKey; className?: string }) {
  return (
    <span
      className={`glossary-infotip ${className}`.trim()}
      tabIndex={0}
      role="note"
      aria-label={GLOSSARY_TERMS[term]}
      title={GLOSSARY_TERMS[term]}
    >
      ⓘ
    </span>
  );
}

/** Envuelve un elemento existente (ej. un <KpiCard/>) y le agrega el ícono
 *  de ayuda en la esquina, sin tocar el contenido ni los props internos. */
export function WithInfo({ term, children }: { term: GlossaryKey; children: ReactNode }) {
  return (
    <div className="glossary-with-info">
      {children}
      <InfoTip term={term} className="glossary-corner" />
    </div>
  );
}

/** Botón discreto para el header. No reemplaza nada existente, se agrega al lado. */
export function GlossaryToggle({ onOpen }: { onOpen: () => void }) {
  return (
    <button type="button" className="glossary-toggle" onClick={onOpen} title="Ver glosario de términos">
      ❓ Glosario
    </button>
  );
}

/** Panel lateral colapsable con todos los términos. Oculto por defecto (open=false),
 *  no ocupa espacio ni interfiere con el layout hasta que el usuario lo abre. */
export function GlossaryDrawer({ open, onClose }: { open: boolean; onClose: () => void }) {
  if (!open) return null;
  return (
    <div className="glossary-drawer-backdrop" onClick={onClose}>
      <aside className="glossary-drawer" onClick={(e) => e.stopPropagation()}>
        <div className="glossary-drawer-header">
          <h3>Glosario</h3>
          <button type="button" onClick={onClose} aria-label="Cerrar glosario">✕</button>
        </div>
        <dl>
          {Object.entries(GLOSSARY_TERMS).map(([key, def]) => {
            const { title, body } = splitTerm(def);
            return (
              <div key={key} className="glossary-entry">
                <dt>{title}</dt>
                <dd>{body}</dd>
              </div>
            );
          })}
        </dl>
      </aside>
    </div>
  );
}

/** Hook chico opcional para manejar el estado de apertura sin tocar el resto de App.tsx. */
export function useGlossary() {
  const [open, setOpen] = useState(false);
  return { open, openGlossary: () => setOpen(true), closeGlossary: () => setOpen(false) };
}