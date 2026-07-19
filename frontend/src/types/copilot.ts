export interface CopilotQueryRequest {
  question: string;
}

export interface CopilotQueryResponse {
  answer: string;
  citations: string[];
  confidence: number;
  insufficient_evidence: boolean;
}
