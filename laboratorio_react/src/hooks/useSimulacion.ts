import {useState} from 'react'; import type {Scenario,Simulation} from '../types'; import {simulate} from '../services/api';
export function useSimulacion(){const [loading,setLoading]=useState(false);const [result,setResult]=useState<Simulation|null>(null);const run=async(s:Scenario)=>{setLoading(true);try{setResult(await simulate(s))}finally{setLoading(false)}};return{loading,result,run}}
