export type Scenario = {
  clareo_pct: number;
  quema_pct: number;
  restauracion_plantas_ha: number;
  manejo_combustibles: number;
  fmc: number;
  lai: number;
  ndvi: number;
  precipitacion_mm: number;
  temperatura_c: number;
  year: number;
  month: number;
};

export type Metricas = {
  biomasa: number;
  npp: number;
  riesgo: number;
  nee?: number;
};

export type Predictora = {
  nombre: string;
  valor: number;
  unidad: string;
};

export type TrazaModelo = {
  objetivo: string;
  modelo: string;
  tipo: string;
  predictoras: Predictora[];
  resultado?: number;
  unidad: string;
};

export type Insumos = {
  gestion: Record<string, number>;
  vegetacion_efectiva: Record<string, number>;
  modelos: TrazaModelo[];
  interpretaciones: string[];
};

export type Tree = {
  x: number;
  y: number;
  height: number;
  crown: number;
  biomass: number;
  risk: number;
  loss: number;
  elevation?: number;
  en_subparcela_3d?: boolean;
};

export type Terreno = {
  grid_size: number;
  resolution_m: number;
  elevation_min: number;
  elevation_max: number;
  elevations: number[][];
};

export type ParcelaMetadata = {
  sitio: string;
  latitud: number;
  longitud: number;
  area_macro_m: number;
  subparcela_3d_m: number;
  fuente: string;
  total_arboles_macro: number;
  total_arboles_subparcela_3d: number;
};

export type Simulation = {
  source_version: string;
  baseline: Metricas;
  scenario: Metricas;
  delta: Metricas;
  temporal: Array<{
    period: string;
    baseline: number;
    scenario: number;
    riesgo_base: number;
    riesgo_escenario: number;
  }>;
  trees: Tree[];
  insumos?: Insumos;
  terreno?: Terreno;
  metadata_parcela?: ParcelaMetadata;
};

export type Model = {
  nombre: string;
  metricas: Record<string, number>;
  hiperparametros?: Record<string, unknown>;
  source_version: string;
  fecha?: string;
};
