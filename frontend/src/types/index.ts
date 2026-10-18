// Chat types
export interface ChatMessage {
  role: 'user' | 'assistant';
  content: string;
  citations?: Citation[];
  trace?: any[];
}

export interface Citation {
  chunk_id: string;
  object_id: string;
  title: string;
  section_type: string;
  distance: number;
  corpus?: "standard" | "nova";
  graph_expanded?: boolean;
  source_no?: number;
}

export interface ChatRequest {
  session_id?: string;
  message: string;
  history?: ChatMessage[];
  top_k?: number;
  scope?: "standard" | "nova" | "both";
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
