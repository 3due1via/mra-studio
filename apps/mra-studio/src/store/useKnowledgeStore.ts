import { create } from "zustand";
export type Card = { code:string; title:string; category:string; status:string; version:string };
type State = { cards:Card[]; addDemo:()=>void };
export const useKnowledgeStore = create<State>((set)=>({
  cards:[],
  addDemo:()=>set((s)=>s.cards.length ? s : {cards:[{
    code:"CMP-RES-000001", title:"Resistenza", category:"Componenti passivi", status:"draft", version:"1.0.0"
  }]})
}));
