// Session types
export type SessionKind = 'chat' | 'pdf' | 'audio';
export type SessionStatus = 'pending' | 'processing' | 'completed' | 'failed';

export interface Session {
  session_id: string;
  kind: SessionKind;
  title: string;
  created_at: string;
  status: SessionStatus;
  source_ref?: string;
  metadata?: Record<string, any>;
}

// Chat types
export interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
  citations?: Citation[];
}

export interface Citation {
  chunk_id: string;
  object_id: string;
  title: string;
  section_type: string;
  distance: number;
}

export interface ChatRequest {
  session_id?: string;
  message: string;
  history?: ChatMessage[];
  top_k?: number;
}

export interface ChatResponse {
  message: string;
  citations: Citation[];
  matched_objects: string[];
  graph_data?: GraphData;
  trace?: any[];
  session_id?: string;
}

export interface ChunkInfo {
  chunk_id: string;
  object_id: string;
  title: string;
  section_type: string;
  distance: number;
  content: string;
}

// Fit-Gap types
export type Verdict = 'fit' | 'partial' | 'gap' | 'question';
export type DecisionStatus = 'open' | 'answered' | 'resolved';

export interface Requirement {
  req_id: string;
  session_id: string;
  ref_in_doc?: string;
  text: string;
  category?: string;
  page?: number;
  speaker?: string;
  created_at: string;
}

export interface Match {
  req_id: string;
  session_id: string;
  object_id: string;
  distance: number;
  verdict: Verdict;
  rationale: string;
  model: string;
  matched_objects: string[];
  created_at: string;
}

export interface Decision {
  decision_id: string;
  session_id: string;
  req_id?: string;
  question: string;
  options: string[];
  status: DecisionStatus;
  answer?: string;
  source: string;
  created_at: string;
}

export interface FitGapResult {
  session_id: string;
  requirements: Requirement[];
  matches: Match[];
  decisions: Decision[];
  summary: string;
  stats: Record<string, any>;
}

// Graph types
export interface GraphNode {
  id: string;
  title: string;
}

export interface GraphEdge {
  source: string;
  target: string;
  type: string;
}

export interface GraphData {
  nodes: GraphNode[];
  edges: GraphEdge[];
}

// Object types
export interface ObjectInfo {
  object_id: string;
  title: string;
  sections: Record<string, string>;
  element_refs: string[];
}

// API response types
export interface ApiResponse<T> {
  data?: T;
  error?: string;
  message?: string;
}
